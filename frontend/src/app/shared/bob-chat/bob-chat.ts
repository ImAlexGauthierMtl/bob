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
            icon: 'fa-solid fa-building',
            label: 'Ajouter un compte',
            description: 'Créer une organisation et enrichir automatiquement',
        },
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

        // ── Intent: Add account/organization ──
        const addAccountMatch = msg.match(/(?:ajouter|créer|creer|nouveau|nouvelle)\s+(?:un\s+)?(?:compte|organisation|organization|client|entreprise)\s*[:\-–]?\s*(.*)/i);
        if (addAccountMatch) {
            const name = addAccountMatch[1]?.trim();
            if (name) {
                return `🏢 J'ai détecté que tu veux ajouter "${name}" comme nouvelle organisation. Je lance le workflow **Ajouter un compte** :\n\n✓ Création de l'organisation "${name}"\n✓ Enrichissement automatique des données\n✓ Recherche de contacts associés\n\nVeux-tu que je procède ?`;
            }
            return '🏢 Je peux t\'aider à ajouter une nouvelle organisation. Donne-moi le nom du compte et je lancerai le workflow de création.';
        }

        // ── Intent: Add contact ──
        if (/(?:ajouter|créer|creer|nouveau|nouvelle)\s+(?:un\s+)?(?:contact|personne)/i.test(lower)) {
            const nameMatch = msg.match(/(?:contact|personne)\s*[:\-–]?\s*(.*)/i);
            const contactName = nameMatch?.[1]?.trim();
            if (contactName) {
                return `👤 Je crée le contact "${contactName}" et je lance l'enrichissement automatique. Je te notifie quand c'est prêt.`;
            }
            return '👤 Je peux ajouter un nouveau contact. Donne-moi le nom et je m\'occupe du reste.';
        }

        // ── Intent: Create task ──
        if (/(?:ajouter|créer|creer|nouvelle?)\s+(?:une?\s+)?(?:tâche|tache|task|todo)/i.test(lower)) {
            return '✅ Je peux créer une tâche pour toi. Précise le titre et je l\'assigne automatiquement.';
        }

        // ── Intent: Follow-up / relance ──
        if (/(?:relancer|follow.?up|rappel|suivi)/i.test(lower)) {
            return '🔔 Je peux configurer une relance automatique. Sur quel contact ou opportunité ?';
        }

        // ── Intent: Workflow / automation ──
        if (lower.includes('workflow') || lower.includes('automation') || lower.includes('automatiser')) {
            return 'Je peux t\'aider à créer ou exécuter des workflows. Utilise les actions rapides ou dis-moi ce que tu veux automatiser.';
        }

        // ── Intent: Contacts / organizations ──
        if (lower.includes('contact') || lower.includes('organization') || lower.includes('organisation')) {
            return 'Je peux enrichir les contacts et organisations avec des données IA. Veux-tu lancer un enrichissement ?';
        }

        // ── Intent: Opportunities / deals ──
        if (lower.includes('opportunit') || lower.includes('deal') || lower.includes('prospect')) {
            return 'Je peux scorer tes leads et signaler les opportunités dormantes. Veux-tu lancer une analyse ?';
        }

        return 'Je suis là pour t\'aider ! Tu peux me demander d\'ajouter un compte, créer un contact, automatiser une tâche, ou utiliser les actions rapides ci-dessous.';
    }
}
