import { AsyncPipe } from '@angular/common';
import { Component, signal, ViewChild, ElementRef, AfterViewChecked, OnDestroy, OnInit, inject } from '@angular/core';
import { Store } from '@ngrx/store';
import { map } from 'rxjs/operators';
import { Subscription } from 'rxjs';
import { BobRuntimeAgent } from '../../shared/services/bob-assistant-settings.service';
import { loadBobAssistantSettings } from '../../store/bob-assistant-settings/bob-assistant-settings.actions';
import { selectBobAssistantRuntimeSettings } from '../../store/bob-assistant-settings/bob-assistant-settings.selectors';
import { sendBobChatMessage, startNewBobChatConversation } from '../../store/bob-chat/bob-chat.actions';
import { selectBobChatError, selectBobChatLoading, selectBobChatMessages } from '../../store/bob-chat/bob-chat.selectors';

@Component({
    selector: 'croo-chat',
    standalone: true,
    imports: [AsyncPipe],
    templateUrl: './chat.html',
    styleUrl: './chat.css',
})
export class ChatComponent implements AfterViewChecked, OnDestroy, OnInit {
    @ViewChild('messagesEnd') private messagesEndRef!: ElementRef<HTMLDivElement>;

    private store = inject(Store);
    inputText = signal('');
    agents = signal<BobRuntimeAgent[]>([]);
    selectedAgentId = signal('agent-bob-orchestrator');
    messages$ = this.store.select(selectBobChatMessages).pipe(
        map((messages) => messages.filter((message) => !message.isLoading && message.id !== 'bob-welcome')),
    );
    isLoading$ = this.store.select(selectBobChatLoading);
    error$ = this.store.select(selectBobChatError);
    private subscriptions = new Subscription();
    private isSending = false;

    ngOnInit(): void {
        this.subscriptions.add(
            this.store.select(selectBobAssistantRuntimeSettings).subscribe((runtime) => {
                const agents = runtime?.agents || [];
                this.agents.set(agents);
                if (agents.length && !agents.some((agent) => agent.id === this.selectedAgentId())) {
                    this.selectedAgentId.set(agents[0].id);
                }
            }),
        );
        this.subscriptions.add(
            this.store.select(selectBobChatLoading).subscribe((loading) => {
                this.isSending = loading;
            }),
        );
        this.store.dispatch(loadBobAssistantSettings());
        this.store.dispatch(startNewBobChatConversation());
    }

    ngOnDestroy(): void {
        this.subscriptions.unsubscribe();
    }

    ngAfterViewChecked(): void {
        this.scrollToBottom();
    }

    private scrollToBottom(): void {
        try {
            this.messagesEndRef?.nativeElement?.scrollIntoView({ behavior: 'smooth' });
        } catch {}
    }

    send(): void {
        const text = this.inputText().trim();
        if (!text || this.isSending) return;

        this.inputText.set('');
        this.store.dispatch(sendBobChatMessage({
            messageId: this.createMessageId('user'),
            loadingMessageId: this.createMessageId('loading'),
            text,
            channel: 'workspace',
            agentId: this.selectedAgentId() || undefined,
        }));
    }

    onKeydown(event: KeyboardEvent): void {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            this.send();
        }
    }

    onAgentChange(agentId: string): void {
        this.selectedAgentId.set(agentId);
        this.store.dispatch(startNewBobChatConversation());
    }

    private createMessageId(prefix: string): string {
        if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
            return `${prefix}-${crypto.randomUUID()}`;
        }
        return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    }
}
