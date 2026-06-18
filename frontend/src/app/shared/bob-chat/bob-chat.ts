import { Component, inject, ViewChild, ElementRef, AfterViewChecked, OnDestroy, OnInit, NgZone } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { Subscription } from 'rxjs';
import { BobService } from '../services/bob.service';
import { BobArtifact, BobSessionInfo } from '../models/bob.model';
import { AuthService } from '../services/auth.service';
import { BobActionService, BobAction, BobMission } from '../services/bob-action.service';
import { PipecatClient, RTVIEvent } from '@pipecat-ai/client-js';
import { WebSocketTransport } from '@pipecat-ai/websocket-transport';

interface ChatMessage {
    role: 'user' | 'bob';
    text: string;
    time: Date;
    isLoading?: boolean;
    toolSteps?: { tool: string; status: string }[];
    artifact?: BobArtifact;
}

interface QuickWorkflow {
    icon: string;
    label: string;
    description: string;
}

interface SessionGroup {
    label: string;
    sessions: BobSessionInfo[];
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

    private http = inject(HttpClient);
    private bobService = inject(BobService);
    private authService = inject(AuthService);
    private bobActionService = inject(BobActionService);
    private missionSub!: Subscription;
    private missionUpdateSub?: Subscription;

    isOpen = false;
    isExpanded = false;
    message = '';
    hasUnread = true;
    isLoading = false;
    sessionId: string | undefined;
    private shouldScrollToBottom = false;

    // ── Expanded sidebar state ──────────────────────────
    sessionGroups: SessionGroup[] = [];
    activeTitle = 'New Conversation';
    userName = '';
    userRole = '';

    // ── Mission state ───────────────────────────────────
    activeMissionPrompt: string | undefined;
    activeMissionContext: Record<string, unknown> | undefined;
    isMissionActive = false;

    // ── Voice state ─────────────────────────────────────
    voiceState: VoiceState = 'idle';
    showConsentDialog = false;
    private pipecatClient: PipecatClient | null = null;
    private reconnectAttempts = 0;
    private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    private intentionalDisconnect = false;
    private ngZone = inject(NgZone);
    private currentBotTranscriptMsg: ChatMessage | null = null;
    private autoListenEnabled = true;

    messages: ChatMessage[] = [
        {
            role: 'bob',
            text: 'Hello! I\'m Bob, your AI assistant. How can I help you today?',
            time: new Date(),
        },
    ];

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
        }
    }

    // ── Session management (expanded sidebar) ───────────

    loadSessions(): void {
        this.bobService.listSessions().subscribe({
            next: (sessions) => {
                this.sessionGroups = this.groupSessions(sessions);
            },
            error: () => {
                this.sessionGroups = [];
            },
        });
    }

    private groupSessions(sessions: BobSessionInfo[]): SessionGroup[] {
        const now = new Date();
        const today = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
        const yesterday = today - 86400000;
        const weekAgo = today - 7 * 86400000;

        const groups: Record<string, BobSessionInfo[]> = {
            'Today': [],
            'Yesterday': [],
            'Last 7 Days': [],
            'Older': [],
        };

        for (const s of sessions) {
            const ts = s.last_activity * 1000;
            if (ts >= today) {
                groups['Today'].push(s);
            } else if (ts >= yesterday) {
                groups['Yesterday'].push(s);
            } else if (ts >= weekAgo) {
                groups['Last 7 Days'].push(s);
            } else {
                groups['Older'].push(s);
            }
        }

        return Object.entries(groups)
            .filter(([, list]) => list.length > 0)
            .map(([label, list]) => ({ label, sessions: list }));
    }

    selectSession(session: BobSessionInfo): void {
        this.sessionId = session.session_id;
        this.activeTitle = session.title || `Session #${session.session_id.slice(0, 8)}`;
        this.messages = [
            { role: 'bob', text: 'Resuming conversation…', time: new Date() },
        ];
        this.shouldScrollToBottom = true;
    }

    deleteSession(session: BobSessionInfo, event: Event): void {
        event.stopPropagation();
        this.bobService.deleteSession(session.session_id).subscribe(() => {
            this.loadSessions();
            if (this.sessionId === session.session_id) {
                this.newConversation();
            }
        });
    }

    newConversation(): void {
        this.sessionId = undefined;
        this.activeTitle = 'New Conversation';
        this.messages = [
            { role: 'bob', text: 'Hello! I\'m Bob, your AI assistant. How can I help you today?', time: new Date() },
        ];
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
        this.messages.push({
            role: 'user',
            text: userMsg,
            time: new Date(),
        });
        this.message = '';
        this.isLoading = true;
        this.shouldScrollToBottom = true;

        // Add typing indicator
        const loadingMsg: ChatMessage = {
            role: 'bob',
            text: '',
            time: new Date(),
            isLoading: true,
        };
        this.messages.push(loadingMsg);

        this.bobService.chat(userMsg, this.sessionId, this.activeMissionPrompt, this.activeMissionContext, this.isExpanded ? 'workspace' : 'compact').subscribe({
            next: (response) => {
                const idx = this.messages.indexOf(loadingMsg);
                if (idx > -1) this.messages.splice(idx, 1);

                this.messages.push({
                    role: 'bob',
                    text: response.response,
                    time: new Date(),
                    toolSteps: response.tool_steps?.length ? response.tool_steps : undefined,
                    artifact: response.artifact || undefined,
                });

                this.sessionId = response.session_id;
                this.isLoading = false;
                this.shouldScrollToBottom = true;

                // Update active title from session_title
                if (response.session_title) {
                    this.activeTitle = response.session_title;
                    // Refresh sidebar sessions if expanded
                    if (this.isExpanded) this.loadSessions();
                }

                // After first mission message is sent, clear the prompt
                // (backend session already has it, no need to resend)
                if (this.activeMissionPrompt) {
                    this.activeMissionPrompt = undefined;
                }

                // Dispatch any actions from tool calls
                if (response.actions && response.actions.length > 0) {
                    console.log('[Bob] Text chat actions:', response.actions);
                    for (const action of response.actions) {
                        this.bobActionService.dispatch(action as BobAction);
                    }
                }
            },
            error: (err) => {
                const idx = this.messages.indexOf(loadingMsg);
                if (idx > -1) this.messages.splice(idx, 1);

                this.messages.push({
                    role: 'bob',
                    text: 'Sorry, I encountered an error. Please try again.',
                    time: new Date(),
                });

                this.isLoading = false;
                this.shouldScrollToBottom = true;
                console.error('Bob chat error:', err);
            },
        });
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

    private loadVoiceSettings(): void {
        const token = this.authService.getToken();
        if (!token) return;
        this.http.get<any>(`${environment.aiAgentApiUrl}/bob/settings`, {
            headers: { Authorization: `Bearer ${token}` },
        }).subscribe({
            next: (data) => {
                this.autoListenEnabled = data?.voice?.auto_listen ?? true;
            },
            error: () => { /* keep default */ },
        });
    }

    private async connectVoice(): Promise<void> {
        const token = this.authService.getToken();
        if (!token) {
            console.error('No auth token for voice');
            return;
        }

        this.voiceState = 'connecting';
        this.loadVoiceSettings();

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
                    this.messages.push({
                        role: 'bob',
                        text: '🎤 Voice mode activated — speak naturally, I\'m listening.',
                        time: new Date(),
                    });
                    this.shouldScrollToBottom = true;
                });
            });

            this.pipecatClient.on(RTVIEvent.BotStartedSpeaking, () => {
                this.ngZone.run(() => {
                    this.voiceState = 'speaking';
                    // Prepare a new transcript bubble
                    this.currentBotTranscriptMsg = {
                        role: 'bob',
                        text: '',
                        time: new Date(),
                    };
                    this.messages.push(this.currentBotTranscriptMsg);
                    this.shouldScrollToBottom = true;
                });
            });

            this.pipecatClient.on(RTVIEvent.BotStoppedSpeaking, () => {
                this.ngZone.run(() => {
                    this.voiceState = 'listening';
                    this.currentBotTranscriptMsg = null;
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
                        if (this.currentBotTranscriptMsg) {
                            this.currentBotTranscriptMsg.text += clean + ' ';
                        } else {
                            this.currentBotTranscriptMsg = {
                                role: 'bob',
                                text: clean + ' ',
                                time: new Date(),
                            };
                            this.messages.push(this.currentBotTranscriptMsg);
                        }
                        this.shouldScrollToBottom = true;
                    });
                }
            });

            this.pipecatClient.on(RTVIEvent.UserTranscript, (data: any) => {
                // Only show final user transcriptions (not interim) as light confirmations
                if (data?.text && data?.final) {
                    this.ngZone.run(() => {
                        this.messages.push({
                            role: 'user',
                            text: data.text,
                            time: new Date(),
                        });
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
                        this.messages.push({
                            role: 'bob',
                            text: `Connection lost. Reconnecting (${this.reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})...`,
                            time: new Date(),
                        });
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
                wsUrl: `${WS_URL}/ws/bob/voice?token=${token}`,
            });

        } catch (err) {
            console.error('Failed to connect voice:', err);
            this.voiceState = 'idle';
            this.pipecatClient = null;

            this.messages.push({
                role: 'bob',
                text: 'Could not access microphone. Please check permissions.',
                time: new Date(),
            });
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
        const target = this.currentBotTranscriptMsg || this.messages[this.messages.length - 1];
        if (target && target.role === 'bob') {
            if (!target.toolSteps) target.toolSteps = [];
            target.toolSteps.push({ tool: fnName, status: 'ok' });
            this.shouldScrollToBottom = true;
        }
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
        this.sessionId = undefined;
        this.activeMissionPrompt = mission.missionPrompt;
        this.activeMissionContext = mission.missionContext;
        this.isMissionActive = true;

        // Add system-like message to indicate mission start
        this.messages.push({
            role: 'bob',
            text: '🎯 **Mission activée** — Interview CEO en cours. Bob est maintenant en mode intervieweur psychodynamique.',
            time: new Date(),
        });
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
        this.activeMissionPrompt = mission.missionPrompt;
        this.activeMissionContext = mission.missionContext;

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
}
