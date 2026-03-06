import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';

interface WorkflowStep {
    label: string;
    type: 'trigger' | 'ai' | 'condition' | 'action';
}

interface Automation {
    id: string;
    name: string;
    description: string;
    level: 'user' | 'company' | 'system';
    status: 'active' | 'paused';
    icon: string;
    iconGradient: string;
    createdDaysAgo: number;
    triggeredCount: number;
    successRate: number;
    steps: WorkflowStep[];
}

interface AutomationTemplate {
    name: string;
    description: string;
    level: 'User' | 'Company' | 'System';
    icon: string;
    gradient: string;
    borderColor: string;
    textColor: string;
    bgColor: string;
}

@Component({
    selector: 'croo-settings-automation',
    standalone: true,
    imports: [FormsModule],
    templateUrl: './settings-automation.html',
    styleUrls: ['../settings-shared.css'],
})
export class SettingsAutomationComponent {
    showBanner = true;
    searchQuery = '';
    selectedLevel: 'all' | 'user' | 'company' | 'system' = 'all';

    automations: Automation[] = [
        {
            id: '1',
            name: 'Smart Email Prioritization',
            description: 'Automatically categorizes incoming emails and flags urgent messages requiring immediate attention',
            level: 'user',
            status: 'active',
            icon: 'fa-solid fa-envelope',
            iconGradient: 'auto-card__icon--blue',
            createdDaysAgo: 14,
            triggeredCount: 247,
            successRate: 98.4,
            steps: [
                { label: 'Trigger: New Email Received', type: 'trigger' },
                { label: 'Bob Analysis: Content & Sender Priority', type: 'ai' },
                { label: 'Action: Apply Label & Send Notification', type: 'action' },
            ],
        },
        {
            id: '2',
            name: 'Lead Assignment & Distribution',
            description: 'Intelligently assigns new leads to sales reps based on territory, expertise, and current workload',
            level: 'company',
            status: 'active',
            icon: 'fa-solid fa-user-plus',
            iconGradient: 'auto-card__icon--orange',
            createdDaysAgo: 28,
            triggeredCount: 1834,
            successRate: 99.2,
            steps: [
                { label: 'Trigger: New Lead Created', type: 'trigger' },
                { label: 'Bob Routing: Analyze Territory & Skills Match', type: 'ai' },
                { label: 'Condition: Check Team Capacity', type: 'condition' },
                { label: 'Action: Assign to Rep & Notify', type: 'action' },
            ],
        },
        {
            id: '3',
            name: 'Cross-Platform Data Synchronization',
            description: 'Maintains data consistency across CRM, ERP, and external platforms in real-time',
            level: 'system',
            status: 'active',
            icon: 'fa-solid fa-sync',
            iconGradient: 'auto-card__icon--purple',
            createdDaysAgo: 45,
            triggeredCount: 8921,
            successRate: 99.8,
            steps: [
                { label: 'Trigger: Data Change Detected', type: 'trigger' },
                { label: 'Validation: Check Data Integrity', type: 'condition' },
                { label: 'Bob Mapping: Transform Data Format', type: 'ai' },
                { label: 'Action: Sync Across All Platforms', type: 'action' },
            ],
        },
        {
            id: '4',
            name: 'Smart Task Completion Reminder',
            description: 'Sends contextual reminders for pending tasks based on priority and deadline proximity',
            level: 'user',
            status: 'paused',
            icon: 'fa-solid fa-check-double',
            iconGradient: 'auto-card__icon--green',
            createdDaysAgo: 7,
            triggeredCount: 89,
            successRate: 97.8,
            steps: [
                { label: 'Trigger: Task Due Within 24 Hours', type: 'trigger' },
                { label: 'Bob Analysis: Assess Task Context & Priority', type: 'ai' },
                { label: 'Action: Send Smart Reminder', type: 'action' },
            ],
        },
    ];

    templates: AutomationTemplate[] = [
        {
            name: 'Welcome New Customers',
            description: 'Automatically send onboarding emails, create tasks, and schedule follow-ups for new clients',
            level: 'Company',
            icon: 'fa-solid fa-handshake',
            gradient: 'auto-tpl--blue',
            borderColor: 'border-blue',
            textColor: 'text-blue',
            bgColor: 'bg-blue',
        },
        {
            name: 'Pipeline Stage Updates',
            description: 'Notify team members and update records when opportunities move through sales stages',
            level: 'Company',
            icon: 'fa-solid fa-chart-simple',
            gradient: 'auto-tpl--purple',
            borderColor: 'border-purple',
            textColor: 'text-purple',
            bgColor: 'bg-purple',
        },
        {
            name: 'Invoice Generation',
            description: 'Automatically create and send invoices when deals are marked as closed-won',
            level: 'System',
            icon: 'fa-solid fa-file-invoice',
            gradient: 'auto-tpl--green',
            borderColor: 'border-green',
            textColor: 'text-green',
            bgColor: 'bg-green',
        },
        {
            name: 'Deal Risk Alerts',
            description: 'Bob detects stagnant opportunities and alerts managers to take action',
            level: 'Company',
            icon: 'fa-solid fa-triangle-exclamation',
            gradient: 'auto-tpl--orange',
            borderColor: 'border-orange',
            textColor: 'text-orange',
            bgColor: 'bg-orange',
        },
        {
            name: 'Meeting Follow-ups',
            description: 'Create tasks and send summary emails after meetings are completed',
            level: 'User',
            icon: 'fa-solid fa-calendar-check',
            gradient: 'auto-tpl--indigo',
            borderColor: 'border-indigo',
            textColor: 'text-indigo',
            bgColor: 'bg-indigo',
        },
        {
            name: 'Customer Anniversaries',
            description: 'Celebrate customer milestones with personalized messages and offers',
            level: 'Company',
            icon: 'fa-solid fa-cake-candles',
            gradient: 'auto-tpl--yellow',
            borderColor: 'border-yellow',
            textColor: 'text-yellow',
            bgColor: 'bg-yellow',
        },
    ];

    // ── Helpers ──────────────────────────

    dismissBanner(): void {
        this.showBanner = false;
    }

    selectLevel(level: 'all' | 'user' | 'company' | 'system'): void {
        this.selectedLevel = level;
    }

    toggleAutomation(auto: Automation): void {
        auto.status = auto.status === 'active' ? 'paused' : 'active';
    }

    get filteredAutomations(): Automation[] {
        let result = this.automations;
        if (this.selectedLevel !== 'all') {
            result = result.filter(a => a.level === this.selectedLevel);
        }
        if (this.searchQuery.trim()) {
            const q = this.searchQuery.toLowerCase();
            result = result.filter(a =>
                a.name.toLowerCase().includes(q) || a.description.toLowerCase().includes(q)
            );
        }
        return result;
    }

    getLevelLabel(level: string): string {
        switch (level) {
            case 'user': return 'User Level';
            case 'company': return 'Company Level';
            case 'system': return 'System Level';
            default: return level;
        }
    }

    getLevelBadgeClass(level: string): string {
        switch (level) {
            case 'user': return 'auto-badge--blue';
            case 'company': return 'auto-badge--orange';
            case 'system': return 'auto-badge--purple';
            default: return 'auto-badge--gray';
        }
    }

    getStepColor(type: string): string {
        switch (type) {
            case 'trigger': return 'auto-step__num--blue';
            case 'ai': return 'auto-step__num--purple';
            case 'condition': return 'auto-step__num--indigo';
            case 'action': return 'auto-step__num--green';
            default: return 'auto-step__num--gray';
        }
    }

    formatCount(n: number): string {
        return n >= 1000 ? (n / 1000).toFixed(1).replace(/\.0$/, '') + 'k' : n.toString();
    }
}
