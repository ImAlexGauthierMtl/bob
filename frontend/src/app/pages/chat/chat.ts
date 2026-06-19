import { Component, signal, computed, ViewChild, ElementRef, AfterViewChecked } from '@angular/core';
import { ChatService, ChatMessage } from '../../shared/services/chat.service';

@Component({
    selector: 'croo-chat',
    standalone: true,
    imports: [],
    templateUrl: './chat.html',
    styleUrl: './chat.css',
})
export class ChatComponent implements AfterViewChecked {
    @ViewChild('messagesEnd') private messagesEndRef!: ElementRef<HTMLDivElement>;

    messages = signal<ChatMessage[]>([]);
    inputText = signal('');
    isLoading = signal(false);
    error = signal<string | null>(null);
    private sessionId?: string;

    hasMessages = computed(() => this.messages().length > 0);

    constructor(private chat: ChatService) {}

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
        if (!text || this.isLoading()) return;

        const newMsg: ChatMessage = { role: 'user', content: text };
        this.messages.update((m) => [...m, newMsg]);
        this.inputText.set('');
        this.error.set(null);
        this.isLoading.set(true);

        this.chat.send(text, this.sessionId).subscribe({
            next: (res) => {
                this.sessionId = res.sessionId;
                this.messages.update((m) => [...m, { role: 'assistant', content: res.reply }]);
                this.isLoading.set(false);
            },
            error: (err) => {
                this.isLoading.set(false);
                const msg = err?.error?.detail || err?.message || 'Chat unavailable.';
                this.error.set(typeof msg === 'string' ? msg : JSON.stringify(msg));
            },
        });
    }

    onKeydown(event: KeyboardEvent): void {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            this.send();
        }
    }
}
