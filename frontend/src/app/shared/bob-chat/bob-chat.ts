import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';

interface ChatMessage {
    role: 'user' | 'bob';
    text: string;
    time: Date;
}

interface QuickWorkflow {
    icon: string;
    label: string;
    description: string;
}

@Component({
    selector: 'croo-bob-chat',
    standalone: true,
    imports: [FormsModule],
    templateUrl: './bob-chat.html',
    styleUrl: './bob-chat.css',
})
export class BobChatComponent {
    isOpen = false;
    message = '';
    hasUnread = true;

    messages: ChatMessage[] = [
        {
            role: 'bob',
            text: 'Hello! I\'m Bob, your AI assistant. How can I help you today?',
            time: new Date(),
        },
    ];

    quickWorkflows: QuickWorkflow[] = [
        {
            icon: 'fa-solid fa-user-plus',
            label: 'Enrich Contacts',
            description: 'Auto-enrich new contacts with AI',
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

    toggle(): void {
        this.isOpen = !this.isOpen;
        if (this.isOpen) {
            this.hasUnread = false;
        }
    }

    close(): void {
        this.isOpen = false;
    }

    sendMessage(): void {
        if (!this.message.trim()) return;
        this.messages.push({
            role: 'user',
            text: this.message,
            time: new Date(),
        });
        const userMsg = this.message;
        this.message = '';

        // Simulate Bob response
        setTimeout(() => {
            this.messages.push({
                role: 'bob',
                text: this.getBobResponse(userMsg),
                time: new Date(),
            });
        }, 800);
    }

    launchWorkflow(wf: QuickWorkflow): void {
        this.messages.push({
            role: 'user',
            text: `Launch: ${wf.label}`,
            time: new Date(),
        });
        setTimeout(() => {
            this.messages.push({
                role: 'bob',
                text: `I'm starting the "${wf.label}" workflow. I'll ${wf.description.toLowerCase()} and notify you when it's done.`,
                time: new Date(),
            });
        }, 600);
    }

    formatTime(date: Date): string {
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }

    private getBobResponse(msg: string): string {
        const lower = msg.toLowerCase();
        if (lower.includes('workflow') || lower.includes('automation')) {
            return 'I can help you create or run workflows. Use the quick actions below or tell me what you\'d like to automate.';
        }
        if (lower.includes('contact') || lower.includes('organization')) {
            return 'I can enrich contacts and organizations with AI-powered data. Would you like me to start an enrichment workflow?';
        }
        if (lower.includes('opportunity') || lower.includes('deal')) {
            return 'I can score your leads and flag stale opportunities. Want me to run a lead scoring analysis?';
        }
        return 'I\'m here to help! You can ask me about workflows, contacts, opportunities, or use the quick actions below.';
    }
}
