import { Component, inject, ViewChild, ElementRef, AfterViewChecked, OnDestroy, OnInit, NgZone } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Subscription } from 'rxjs';
import { Store } from '@ngrx/store';
import { AuthService } from '../services/auth.service';
import { BobActionService, BobAction, BobMission } from '../services/bob-action.service';
import { BobRuntimeAgent } from '../services/bob-assistant-settings.service';
import { PipecatClient, RTVIEvent } from '@pipecat-ai/client-js';
import { WebSocketTransport } from '@pipecat-ai/websocket-transport';
import {
    addBobChatMessage,
    addBobChatToolStep,
    appendBobChatTranscript,
    cancelBobChatAction,
    confirmBobChatAction,
    deleteBobChatSession,
    loadBobChatSessions,
    selectBobChatSession,
    sendBobChatMessage,
    setBobChatMission,
    startNewBobChatConversation,
} from '../../store/bob-chat/bob-chat.actions';
import { loadBobAssistantSettings } from '../../store/bob-assistant-settings/bob-assistant-settings.actions';
import { selectBobAssistantRuntimeSettings } from '../../store/bob-assistant-settings/bob-assistant-settings.selectors';
import {
    BobChatActionConfirmationView,
    BobChatMessageView,
    BobChatSessionSummary,
} from '../../store/bob-chat/bob-chat.models';
import {
    selectBobChatActiveTitle,
    selectBobChatLoading,
    selectBobChatMessages,
    selectBobChatSessionGroups,
    selectBobChatSessionId,
} from '../../store/bob-chat/bob-chat.selectors';

interface QuickWorkflow {
    icon: string;
    label: string;
    description: string;
}

type VoiceState = 'idle' | 'connecting' | 'listening' | 'processing' | 'speaking';
import { environment } from '../../../environments/environment';

const WS_URL = environment.wsUrl;
const VOICE_CONSENT_KEY = 'croo_voice_consent';
const MAX_RECONNECT_ATTEMPTS = 3;

import { MarkdownPipe } from '../pipes/markdown.pipe';

@Component({
    selector: 'croo-bob-chat',
    standalone: true,
    imports: [FormsModule, MarkdownPipe],
    templateUrl: './bob-chat.html',
    styleUrl: './bob-chat.css',
})
export class BobChatComponent implements OnInit, AfterViewChecked, OnDestroy {
    @ViewChild('messagesContainer') private messagesContainer!: ElementRef;

    private store = inject(Store);
    private authService = inject(AuthService);
    private bobActionService = inject(BobActionService);
    private missionSub!: Subscription;
    private missionUpdateSub?: Subscription;
    private messagesSub?: Subscription;
    private subscriptions = new Subscription();
    private readonly messagesSignal = this.store.selectSignal(selectBobChatMessages);
    private readonly sessionGroupsSignal = this.store.selectSignal(selectBobChatSessionGroups);
    private readonly sessionIdSignal = this.store.selectSignal(selectBobChatSessionId);
    private readonly activeTitleSignal = this.store.selectSignal(selectBobChatActiveTitle);
    private readonly loadingSignal = this.store.selectSignal(selectBobChatLoading);

    isOpen = false;
    isExpanded = false;
    message = '';
    hasUnread = true;
    availableAgents: BobRuntimeAgent[] = [];
    selectedAgentId = 'agent-bob-orchestrator';
    private shouldScrollToBottom = false;

    // ── Expanded sidebar state ──────────────────────────
    userName = '';
    userRole = '';

    // ── Voice state ─────────────────────────────────────
    voiceState: VoiceState = 'idle';
    showConsentDialog = false;
    private pipecatClient: PipecatClient | null = null;
    private reconnectAttempts = 0;
    private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    private intentionalDisconnect = false;
    private ngZone = inject(NgZone);
    private currentBotTranscriptMessageId: string | null = null;
    private autoListenEnabled = true;

    get messages(): BobChatMessageView[] {
        return this.messagesSignal();
    }

    get sessionGroups() {
        return this.sessionGroupsSignal();
    }

    get sessionId(): string | undefined {
        return this.sessionIdSignal();
    }

    get activeTitle(): string {
        return this.activeTitleSignal();
    }

    get isLoading(): boolean {
        return this.loadingSignal();
    }

    quickWorkflows: QuickWorkflow[] = [
        {
            icon: 'fa-solid fa-building',
            label: 'Ajouter un compte',
            description: 'Créer une organisation et enrichir automatiquement',
        },
        {
            icon: 'fa-solid fa-briefcase',
            label: 'Business Advisor',
            description: 'Conseils d\'affaires et analyses stratégiques',
        },
        {
            icon: 'fa-solid fa-chart-line',
            label: 'Score Leads',
            description: 'Predictive scoring on opportunities',
        },
        {
            icon: 'fa-solid fa-bell',
            label: 'Follow-up Alerts',
            description: 'Alert on stale opportunities',
        },
    ];

    ngOnInit(): void {
        let previousMessageCount = this.messages.length;
        this.messagesSub = this.store.select(selectBobChatMessages).subscribe((messages) => {
            if (messages.length !== previousMessageCount) {
                this.shouldScrollToBottom = true;
                previousMessageCount = messages.length;
            }
        });
        this.subscriptions.add(
            this.store.select(selectBobAssistantRuntimeSettings).subscribe((runtime) => {
                this.availableAgents = runtime?.agents || [];
                if (
                    this.availableAgents.length > 0 &&
                    !this.availableAgents.some((agent) => agent.id === this.selectedAgentId)
                ) {
                    this.selectedAgentId = this.availableAgents.find((agent) => agent.status === 'active')?.id
                        || this.availableAgents[0].id;
                }
            }),
        );

        this.missionSub = this.bobActionService.mission$.subscribe((mission: BobMission) => {
            this.startMission(mission);
        });
        this.missionUpdateSub = this.bobActionService.missionUpdate$.subscribe((mission: BobMission) => {
            this.updateMission(mission);
        });

        // User info for expanded sidebar
        this.authService.user$.subscribe((user) => {
            if (user) {
                this.userName = [user.first_name, user.last_name].filter(Boolean).join(' ') || user.email || 'User';
                this.userRole = 'Member';
            }
        });
    }

    ngAfterViewChecked(): void {
        if (this.shouldScrollToBottom) {
            this.scrollToBottom();
            this.shouldScrollToBottom = false;
        }
    }

    ngOnDestroy(): void {
        this.disconnectVoice();
        if (this.missionSub) this.missionSub.unsubscribe();
        if (this.missionUpdateSub) this.missionUpdateSub.unsubscribe();
        if (this.messagesSub) this.messagesSub.unsubscribe();
        this.subscriptions.unsubscribe();
    }

    toggle(): void {
        this.isOpen = !this.isOpen;
        if (this.isOpen) {
            this.hasUnread = false;
            this.shouldScrollToBottom = true;
        } else {
            this.isExpanded = false;
            this.disconnectVoice();
        }
    }

    close(): void {
        this.isOpen = false;
        this.isExpanded = false;
        this.disconnectVoice();
    }

    toggleExpand(): void {
        this.isExpanded = !this.isExpanded;
        this.shouldScrollToBottom = true;
        if (this.isExpanded) {
            this.loadSessions();
            this.store.dispatch(loadBobAssistantSettings());
        }
    }

    // ── Session management (expanded sidebar) ───────────

    loadSessions(): void {
        this.store.dispatch(loadBobChatSessions());
    }

    selectSession(session: BobChatSessionSummary): void {
        this.store.dispatch(selectBobChatSession({
            sessionId: session.id,
            title: session.title || `Session #${session.id.slice(0, 8)}`,
        }));
        this.shouldScrollToBottom = true;
    }

    confirmAction(message: BobChatMessageView, confirmation: BobChatActionConfirmationView): void {
        if (confirmation.status !== 'pending' && confirmation.status !== 'failed') {
            return;
        }
        this.store.dispatch(confirmBobChatAction({
            messageId: message.id,
            runId: confirmation.runId,
            confirmationId: confirmation.confirmationId,
        }));
    }

    cancelAction(message: BobChatMessageView, confirmation: BobChatActionConfirmationView): void {
        if (confirmation.status !== 'pending' && confirmation.status !== 'failed') {
            return;
        }
        this.store.dispatch(cancelBobChatAction({
            messageId: message.id,
            runId: confirmation.runId,
            confirmationId: confirmation.confirmationId,
        }));
    }

    deleteSession(session: BobChatSessionSummary, event: Event): void {
        event.stopPropagation();
        this.store.dispatch(deleteBobChatSession({ sessionId: session.id }));
    }

    newConversation(): void {
        this.store.dispatch(startNewBobChatConversation());
        this.shouldScrollToBottom = true;
    }

    onTextareaKeydown(event: KeyboardEvent): void {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            this.sendMessage();
        }
    }

    autoGrowTextarea(event: Event): void {
        const el = event.target as HTMLTextAreaElement;
        el.style.height = 'auto';
        el.style.height = Math.min(el.scrollHeight, 200) + 'px';
    }

    // ── Text chat ───────────────────────────────────────

    sendMessage(): void {
        if (!this.message.trim() || this.isLoading) return;

        const userMsg = this.message.trim();
        this.message = '';
        this.shouldScrollToBottom = true;

        this.store.dispatch(sendBobChatMessage({
            messageId: this.createMessageId('user'),
            loadingMessageId: this.createMessageId('loading'),
            text: userMsg,
            channel: this.isExpanded ? 'workspace' : 'compact',
            agentId: this.selectedAgentId,
        }));
    }

    // ── Voice ───────────────────────────────────────────

    get isVoiceActive(): boolean {
        return this.voiceState !== 'idle';
    }

    get voiceButtonIcon(): string {
        switch (this.voiceState) {
            case 'connecting': return 'fa-solid fa-spinner fa-spin';
            case 'listening': return 'fa-solid fa-microphone';
            case 'processing': return 'fa-solid fa-spinner fa-spin';
            case 'speaking': return 'fa-solid fa-volume-high';
            default: return 'fa-solid fa-microphone';
        }
    }

    get voiceStatusText(): string {
        switch (this.voiceState) {
            case 'connecting': return 'Connecting...';
            case 'listening': return 'Listening...';
            case 'processing': return 'Thinking...';
            case 'speaking': return 'Bob is speaking...';
            default: return '';
        }
    }

    async toggleVoice(): Promise<void> {
        if (this.isVoiceActive) {
            this.intentionalDisconnect = true;
            this.disconnectVoice();
        } else {
            // Check consent first
            if (!localStorage.getItem(VOICE_CONSENT_KEY)) {
                this.showConsentDialog = true;
                return;
            }
            this.intentionalDisconnect = false;
            this.reconnectAttempts = 0;
            await this.connectVoice();
        }
    }

    acceptVoiceConsent(): void {
        localStorage.setItem(VOICE_CONSENT_KEY, 'true');
        this.showConsentDialog = false;
        this.intentionalDisconnect = false;
        this.reconnectAttempts = 0;
        this.connectVoice();
    }

    declineVoiceConsent(): void {
        this.showConsentDialog = false;
    }

    private async connectVoice(): Promise<void> {
        if (!this.authService.hasActiveSession()) {
            console.error('No active Bob Cloud session for voice');
            return;
        }

        this.voiceState = 'connecting';

        try {
            this.pipecatClient = new PipecatClient({
                transport: new WebSocketTransport(),
                enableMic: true,
                enableCam: false,
            });

            // ── RTVI Events ─────────────────────────────
            this.pipecatClient.on(RTVIEvent.Connected, () => {
                this.ngZone.run(() => {
                    this.voiceState = 'listening';
                    this.addStoreMessage('bob', '🎤 Voice mode activated — speak naturally, I\'m listening.');
                    this.shouldScrollToBottom = true;
                });
            });

            this.pipecatClient.on(RTVIEvent.BotStartedSpeaking, () => {
                this.ngZone.run(() => {
                    this.voiceState = 'speaking';
                    this.currentBotTranscriptMessageId = this.createMessageId('voice-bob');
                    this.addStoreMessage('bob', '', this.currentBotTranscriptMessageId);
                    this.shouldScrollToBottom = true;
                });
            });

            this.pipecatClient.on(RTVIEvent.BotStoppedSpeaking, () => {
                this.ngZone.run(() => {
                    this.voiceState = 'listening';
                    this.currentBotTranscriptMessageId = null;
                    if (this.autoListenEnabled && this.pipecatClient) {
                        this.pipecatClient.enableMic(true);
                    }
                });
            });

            this.pipecatClient.on(RTVIEvent.UserStartedSpeaking, () => {
                this.ngZone.run(() => {
                    this.voiceState = 'processing';
                });
            });

            this.pipecatClient.on(RTVIEvent.BotTranscript, (data: any) => {
                if (data?.text) {
                    this.ngZone.run(() => {
                        let clean = this.stripVoiceTags(data.text);
                        if (!clean) return;
                        if (this.currentBotTranscriptMessageId) {
                            this.store.dispatch(appendBobChatTranscript({
                                messageId: this.currentBotTranscriptMessageId,
                                text: `${clean} `,
                            }));
                        } else {
                            this.currentBotTranscriptMessageId = this.createMessageId('voice-bob');
                            this.addStoreMessage('bob', `${clean} `, this.currentBotTranscriptMessageId);
                        }
                        this.shouldScrollToBottom = true;
                    });
                }
            });

            this.pipecatClient.on(RTVIEvent.UserTranscript, (data: any) => {
                // Only show final user transcriptions (not interim) as light confirmations
                if (data?.text && data?.final) {
                    this.ngZone.run(() => {
                        this.addStoreMessage('user', data.text);
                        this.shouldScrollToBottom = true;
                    });
                }
            });

            this.pipecatClient.on(RTVIEvent.Disconnected, () => {
                this.ngZone.run(() => {
                    if (!this.intentionalDisconnect && this.reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
                        this.reconnectAttempts++;
                        const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts - 1), 8000);
                        this.voiceState = 'connecting';
                        this.addStoreMessage('bob', `Connection lost. Reconnecting (${this.reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})...`);
                        this.shouldScrollToBottom = true;
                        this.reconnectTimer = setTimeout(() => this.connectVoice(), delay);
                    } else {
                        this.voiceState = 'idle';
                    }
                });
            });

            this.pipecatClient.on(RTVIEvent.Error, (error: any) => {
                console.error('RTVI error:', error);
            });

            // ── Function call actions (voice navigation) ──
            this.pipecatClient.on(RTVIEvent.LLMFunctionCallInProgress, (data: any) => {
                console.log('[Bob] LLMFunctionCallInProgress:', JSON.stringify(data));
                this.ngZone.run(() => {
                    const fnName = data?.function_name;
                    const args = data?.arguments || {};
                    console.log(`[Bob] Function call: ${fnName}`, args);

                    this.addVoiceToolBadge(fnName);
                    this.dispatchVoiceAction(fnName, args);
                });
            });

            // Also listen for LLMFunctionCall (deprecated) for compatibility
            this.pipecatClient.on(RTVIEvent.LLMFunctionCall, (data: any) => {
                console.log('[Bob] LLMFunctionCall (deprecated):', JSON.stringify(data));
                this.ngZone.run(() => {
                    const fnName = data?.function_name;
                    const args = data?.args || data?.arguments || {};
                    console.log(`[Bob] Function call (deprecated): ${fnName}`, args);

                    this.addVoiceToolBadge(fnName);
                    this.dispatchVoiceAction(fnName, args);
                });
            });

            // ── Server messages (reliable action dispatch from voice) ──
            this.pipecatClient.on(RTVIEvent.ServerMessage, (data: any) => {
                console.log('[Bob] ServerMessage:', JSON.stringify(data));
                this.ngZone.run(() => {
                    if (data?.type === 'bob_action' && data?.action) {
                        const action = data.action;
                        console.log('[Bob] Voice action via ServerMessage:', action);
                        this.bobActionService.dispatch({
                            type: action.type,
                            page: action.page,
                            entity: action.entity,
                            name: action.name,
                            direction: action.direction,
                            slide_number: action.slide_number,
                            text: action.text,
                            submit: action.submit,
                            index: action.index,
                        });
                    }
                });
            });

            // ── Connect ─────────────────────────────────
            await this.pipecatClient.connect({
                wsUrl: `${WS_URL}/ws/bob/voice`,
            });

        } catch (err) {
            console.error('Failed to connect voice:', err);
            this.voiceState = 'idle';
            this.pipecatClient = null;

            this.addStoreMessage('bob', 'Could not access microphone. Please check permissions.');
            this.shouldScrollToBottom = true;
        }
    }

    private stripVoiceTags(text: string): string {
        return text
            .replace(/\[[\w\s]+\]/g, '')
            .replace(/<\/?(?:laugh|chuckle|sigh|gasp|whisper)>/gi, '')
            .replace(/<think>[\s\S]*?<\/think>/gi, '')
            .replace(/\/?(?:no_)?think\b/gi, '')
            .trim();
    }

    private addVoiceToolBadge(fnName: string): void {
        if (!fnName) return;
        this.store.dispatch(addBobChatToolStep({
            messageId: this.currentBotTranscriptMessageId || undefined,
            step: { tool: fnName, status: 'ok' },
        }));
        this.shouldScrollToBottom = true;
    }

    private dispatchVoiceAction(fnName: string, args: Record<string, any>): void {
        if (fnName === 'navigate_to') {
            this.bobActionService.dispatch({ type: 'navigate', page: args['page'] });
        } else if (fnName === 'open_create_dialog') {
            this.bobActionService.dispatch({
                type: 'open_create_dialog', entity: args['entity'], name: args['name'],
            });
        } else if (fnName === 'start_crm_training') {
            this.bobActionService.dispatch({ type: 'navigate', page: 'template/crm-mastery' });
        }
    }

    disconnectVoice(): void {
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
            this.reconnectTimer = null;
        }
        if (this.pipecatClient) {
            this.pipecatClient.disconnect();
            this.pipecatClient = null;
        }
        this.voiceState = 'idle';
        this.reconnectAttempts = 0;
    }

    // ── Shared ──────────────────────────────────────────

    launchWorkflow(wf: QuickWorkflow): void {
        this.message = wf.label;
        this.sendMessage();
    }

    /**
     * Start a mission-driven conversation with Bob.
     * Opens the chat panel, resets the session, and sends the initial message.
     */
    startMission(mission: BobMission): void {
        // Open chat if not open
        this.isOpen = true;
        this.hasUnread = false;

        // Reset session for fresh mission
        this.store.dispatch(startNewBobChatConversation());
        this.store.dispatch(setBobChatMission({
            prompt: mission.missionPrompt,
            context: mission.missionContext,
            active: true,
        }));

        // Add system-like message to indicate mission start
        this.addStoreMessage(
            'bob',
            '🎯 **Mission activée** — Interview CEO en cours. Bob est maintenant en mode intervieweur psychodynamique.',
        );
        this.shouldScrollToBottom = true;

        // Send the initial message
        this.message = mission.initialMessage;
        this.sendMessage();
    }

    /**
     * Update an ongoing mission with new context (e.g. slide changed).
     * Does NOT reset the session.
     */
    updateMission(mission: BobMission): void {
        this.store.dispatch(setBobChatMission({
            prompt: mission.missionPrompt,
            context: mission.missionContext,
            active: true,
        }));

        if (this.isVoiceActive && this.pipecatClient) {
            // Inject new context directly into the running Pipecat Voice pipeline
            // using the 'user' role with a system-like formatting to instruct Bob
            console.log('[Bob Chat] Injecting mission update to Pipecat context');
            this.pipecatClient.appendToContext({
                role: 'user',
                content: `[SYSTEM CONTEXT UPDATE] ${mission.initialMessage}`,
                run_immediately: true,
            });
        } else if (this.isOpen) {
            // Text chat is open, just post the message
            this.message = `[SYSTEM CONTEXT UPDATE] ${mission.initialMessage}`;
            this.sendMessage();
        }
    }

    formatTime(date: Date): string {
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }

    private scrollToBottom(): void {
        try {
            if (this.messagesContainer) {
                this.messagesContainer.nativeElement.scrollTop =
                    this.messagesContainer.nativeElement.scrollHeight;
            }
        } catch (e) {
            // Ignore scroll errors
        }
    }

    private addStoreMessage(role: 'user' | 'bob', text: string, id = this.createMessageId(role)): void {
        this.store.dispatch(addBobChatMessage({
            message: {
                id,
                role,
                text,
                time: new Date(),
            },
        }));
    }

    private createMessageId(prefix: string): string {
        if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
            return `${prefix}-${crypto.randomUUID()}`;
        }

        return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    }
}
