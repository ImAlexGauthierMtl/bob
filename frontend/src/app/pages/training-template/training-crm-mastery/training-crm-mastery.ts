import { Component, inject, OnInit, OnDestroy } from '@angular/core';
import { UpperCasePipe, NgFor, NgIf } from '@angular/common';
import { Subscription, interval } from 'rxjs';
import { BobActionService, BobAction } from '../../../shared/services/bob-action.service';
import { TrainingService } from '../../../shared/services/training.service';
import { TrainingNote, TrainingMissing } from '../../../shared/models/training.model';

export interface SlideCard {
    icon: string;
    iconColor: string;
    iconBg: string;
    title: string;
    desc: string;
}

export interface SlideStep {
    number: number;
    text: string;
}

export interface SlideKpi {
    label: string;
    value: string;
    color: string;
}

export interface Slide {
    id: number;
    module: number;
    moduleTitle: string;
    type: 'title' | 'grid' | 'feature' | 'checklist' | 'kpi' | 'timeline' | 'alert' | 'list' | 'assessment';
    title: string;
    subtitle?: string;
    badge?: string;
    content?: string;
    cards?: SlideCard[];
    steps?: SlideStep[];
    kpis?: SlideKpi[];
    items?: string[];
    alertType?: 'warning' | 'info' | 'success';
    timelineSteps?: string[];
    footerText?: string;
}

@Component({
    selector: 'app-training-crm-mastery',
    standalone: true,
    imports: [UpperCasePipe, NgFor, NgIf],
    templateUrl: './training-crm-mastery.html',
    styleUrl: './training-crm-mastery.css',
})
export class TrainingCrmMasteryComponent implements OnInit, OnDestroy {
    private bobActionService = inject(BobActionService);
    private trainingService = inject(TrainingService);
    private subs: Subscription[] = [];

    currentSlide = 0;
    sessionId = '';
    trainingStarted = false;
    notes: TrainingNote[] = [];
    missingElements: TrainingMissing[] = [];

    slides: Slide[] = [
        // ═══════════════════════════════════════
        // MODULE 1: Welcome & Context (1-5)
        // ═══════════════════════════════════════
        {
            id: 1, module: 1, moduleTitle: 'Welcome & Context',
            type: 'title',
            badge: 'Onboarding — The Croo Group',
            title: 'CRM Mastery',
            subtitle: 'Croo Digital Experience',
            content: 'Your complete training to master the CRM platform inside and out. You sell what you breathe.',
            footerText: 'Sales Rep • Digital Experience Team • Sales Department',
        },
        {
            id: 2, module: 1, moduleTitle: 'Welcome & Context',
            type: 'feature',
            badge: 'Your Organization',
            title: 'The Croo Group',
            subtitle: 'Montréal, Québec, Canada',
            content: 'Parent organization specialized in Digital Transformation. You are part of the Digital Experience team, within the Sales department. Your mission: sell Croo Digital Experience, an AI-native CRM platform.',
            cards: [
                { icon: 'fa-solid fa-building', iconColor: '#FF4500', iconBg: '#fff3ed', title: 'The Croo Group', desc: 'Parent Organization' },
                { icon: 'fa-solid fa-users', iconColor: '#3b82f6', iconBg: '#dbeafe', title: 'Sales', desc: 'Department' },
                { icon: 'fa-solid fa-laptop', iconColor: '#8b5cf6', iconBg: '#f3e8ff', title: 'Digital Experience', desc: 'Team' },
                { icon: 'fa-solid fa-user-tie', iconColor: '#10b981', iconBg: '#dcfce7', title: 'Sales Rep', desc: 'Your Role' },
            ],
            footerText: 'Industry: Digital Transformation • Cloud-first SaaS • Data-driven',
        },
        {
            id: 3, module: 1, moduleTitle: 'Welcome & Context',
            type: 'grid',
            badge: 'Objectives',
            title: 'What You Will Learn',
            cards: [
                { icon: 'fa-solid fa-compass', iconColor: '#3b82f6', iconBg: '#dbeafe', title: 'Navigation', desc: 'Navigate all CRM modules independently' },
                { icon: 'fa-solid fa-address-book', iconColor: '#10b981', iconBg: '#dcfce7', title: 'Management', desc: 'Create and manage contacts, organizations and opportunities' },
                { icon: 'fa-solid fa-filter', iconColor: '#8b5cf6', iconBg: '#f3e8ff', title: 'Pipeline', desc: 'Configure and use pipeline stages effectively' },
                { icon: 'fa-solid fa-robot', iconColor: '#f59e0b', iconBg: '#fef3c7', title: 'Bob AI', desc: 'Leverage Bob AI for your daily tasks' },
                { icon: 'fa-solid fa-gears', iconColor: '#ef4444', iconBg: '#fee2e2', title: 'Automation', desc: 'Set up automations for your workflows' },
                { icon: 'fa-solid fa-chart-bar', iconColor: '#06b6d4', iconBg: '#cffafe', title: 'Analytics', desc: 'Read and interpret performance dashboards' },
            ],
            footerText: 'CRM Mastery — Croo Digital Experience',
        },
        {
            id: 4, module: 1, moduleTitle: 'Welcome & Context',
            type: 'timeline',
            badge: 'Your Journey',
            title: 'Progression Roadmap',
            timelineSteps: [
                'Onboarding — CRM Mastery: Master the platform',
                'Foundation — Prospection & Email: Build your pipeline',
                'Practice — Demo & Closing: Convert your prospects',
                'Mastery — Account Management: Become a self-sufficient expert',
            ],
            footerText: '4 stages • 6 skills • 5 daily tasks • 4 milestones',
        },
        {
            id: 5, module: 1, moduleTitle: 'Welcome & Context',
            type: 'assessment',
            badge: 'Milestone #1',
            title: 'CRM Certified — Croo Expert',
            subtitle: 'Validation Criteria',
            kpis: [
                { label: 'Product Knowledge', value: 'Demo all modules independently', color: '#3b82f6' },
                { label: 'CRM Hygiene', value: 'Pipeline up to date 5 consecutive days', color: '#10b981' },
                { label: 'Bob Usage', value: '3+ tasks completed with Bob AI', color: '#f59e0b' },
            ],
            footerText: 'Stage: Onboarding',
        },

        // ═══════════════════════════════════════
        // MODULE 2: Platform Overview (6-12)
        // ═══════════════════════════════════════
        {
            id: 6, module: 2, moduleTitle: 'Platform Overview',
            type: 'title',
            badge: 'Module 2',
            title: 'Croo Digital\nExperience',
            subtitle: 'Platform Overview',
            content: 'An AI-native CRM platform designed for modern sales teams. Every module is interconnected and powered by Bob, your AI assistant.',
            footerText: 'AI-native • Voice-first • Privacy-compliant by design',
        },
        {
            id: 7, module: 2, moduleTitle: 'Platform Overview',
            type: 'grid',
            badge: 'The 6 Modules',
            title: 'Platform Architecture',
            cards: [
                { icon: 'fa-solid fa-address-book', iconColor: '#3b82f6', iconBg: '#dbeafe', title: 'Contacts', desc: 'Create, search, segment your contacts. CSV import.' },
                { icon: 'fa-solid fa-building', iconColor: '#8b5cf6', iconBg: '#f3e8ff', title: 'Organizations', desc: 'Link contacts to companies. Track hierarchy.' },
                { icon: 'fa-solid fa-chart-line', iconColor: '#10b981', iconBg: '#dcfce7', title: 'Opportunities', desc: 'Full pipeline lifecycle, lead → close.' },
                { icon: 'fa-solid fa-list-check', iconColor: '#f59e0b', iconBg: '#fef3c7', title: 'Tasks & Activities', desc: 'Follow-ups, call logs, activity management.' },
                { icon: 'fa-solid fa-chart-pie', iconColor: '#06b6d4', iconBg: '#cffafe', title: 'Analytics', desc: 'Real-time performance dashboards and KPIs.' },
                { icon: 'fa-solid fa-robot', iconColor: '#FF4500', iconBg: '#fff3ed', title: 'Bob AI', desc: 'AI assistant: voice, suggestions, pipeline analysis.' },
            ],
            footerText: 'Croo Digital Experience — Platform Architecture',
        },
        {
            id: 8, module: 2, moduleTitle: 'Platform Overview',
            type: 'feature',
            badge: 'CRM Module',
            title: 'Contacts',
            subtitle: 'Your Smart Address Book',
            content: 'The Contacts module is your people database. Each contact can be linked to an organization, have activities, notes, and be qualified by Bob.',
            items: [
                'Create contacts manually or via CSV import',
                'Search and filter by ICP criteria',
                'Segment by industry, size, engagement',
                'View complete interaction history',
                'Bob automatically enriches data',
            ],
            footerText: 'Module: Contacts',
        },
        {
            id: 9, module: 2, moduleTitle: 'Platform Overview',
            type: 'feature',
            badge: 'CRM Module',
            title: 'Organizations',
            subtitle: 'The Companies You Target',
            content: 'Organizations group your contacts by company. Always link a contact to their organization for a complete view.',
            items: [
                'Link multiple contacts to the same organization',
                'Track hierarchy (parent/subsidiary)',
                'View all linked opportunities',
                'Track industry, size and stage',
                'Contact vs Organization: always link both',
            ],
            footerText: 'Module: Organizations',
        },
        {
            id: 10, module: 2, moduleTitle: 'Platform Overview',
            type: 'feature',
            badge: 'CRM Module',
            title: 'Opportunities',
            subtitle: 'Your Sales Pipeline',
            content: 'The core of your daily work. Each opportunity moves through defined stages, from qualification to close.',
            items: [
                'Visual pipeline with drag & drop between stages',
                'Lead → Qualified → Demo → Proposal → Negotiation → Closed',
                'Automatic forecasting based on history',
                'Bob detects stale deals (> 7 days)',
                'Conversion reports by stage',
            ],
            footerText: 'Module: Opportunities',
        },
        {
            id: 11, module: 2, moduleTitle: 'Platform Overview',
            type: 'feature',
            badge: 'CRM Module',
            title: 'Activities & Tasks',
            subtitle: 'Never Miss a Beat',
            content: 'Every interaction with a prospect must be logged. Tasks help you stay organized and never miss a follow-up.',
            items: [
                'Log calls, emails, meetings automatically',
                'Schedule follow-ups with reminders',
                'Bob generates call notes automatically',
                'Calendar view of all your activities',
                'Activity metrics: calls/day, emails/week',
            ],
            footerText: 'Module: Tasks & Activities',
        },
        {
            id: 12, module: 2, moduleTitle: 'Platform Overview',
            type: 'feature',
            badge: 'CRM Module',
            title: 'Dashboard & Analytics',
            subtitle: 'Measure to Improve',
            content: 'Real-time dashboards giving you a view of your performance. Track your KPIs and identify improvement opportunities.',
            items: [
                'Pipeline health: coverage, velocity, conversion',
                'Activity: calls, emails, meetings by period',
                'Forecasts vs. targets',
                'Top deals and next best actions',
                'Bob analyzes and suggests improvements',
            ],
            footerText: 'Module: Analytics',
        },

        // ═══════════════════════════════════════
        // MODULE 3: Bob AI Assistant (13-18)
        // ═══════════════════════════════════════
        {
            id: 13, module: 3, moduleTitle: 'Bob AI Assistant',
            type: 'title',
            badge: 'Module 3',
            title: 'Bob',
            subtitle: 'Your Personal AI Assistant',
            content: 'Bob is an AI-native assistant integrated into every module of Croo. He analyzes your pipeline, drafts your emails, and guides you through your daily tasks by voice.',
            footerText: 'Voice-first • Smart Suggestions • Pipeline Intelligence',
        },
        {
            id: 14, module: 3, moduleTitle: 'Bob AI Assistant',
            type: 'grid',
            badge: 'Capabilities',
            title: 'What Bob Can Do for You',
            cards: [
                { icon: 'fa-solid fa-microphone', iconColor: '#FF4500', iconBg: '#fff3ed', title: 'Voice Mode', desc: 'Talk to Bob like a colleague. He understands context.' },
                { icon: 'fa-solid fa-wand-magic-sparkles', iconColor: '#8b5cf6', iconBg: '#f3e8ff', title: 'Smart Suggestions', desc: 'Proactive recommendations based on your pipeline.' },
                { icon: 'fa-solid fa-pen-to-square', iconColor: '#3b82f6', iconBg: '#dbeafe', title: 'Email Drafting', desc: 'Writes personalized CASL-compliant emails.' },
                { icon: 'fa-solid fa-chart-line', iconColor: '#10b981', iconBg: '#dcfce7', title: 'Pipeline Analysis', desc: 'Detects at-risk deals and opportunities.' },
            ],
            footerText: 'Bob AI — Croo Digital Experience',
        },
        {
            id: 15, module: 3, moduleTitle: 'Bob AI Assistant',
            type: 'list',
            badge: 'Conversation Starters',
            title: 'How to Talk to Bob',
            subtitle: 'Example commands for your daily CRM tasks',
            items: [
                '"Bob, show me how to create a contact from a received email"',
                '"Bob, how do I set up a custom pipeline?"',
                '"Bob, which of my opportunities have been stale for more than 7 days?"',
                '"Bob, generate a report of my activities for the week"',
                '"Bob, help me understand the analytics dashboard"',
            ],
            footerText: 'CRM Mastery — Bob Conversation Starters',
        },
        {
            id: 16, module: 3, moduleTitle: 'Bob AI Assistant',
            type: 'grid',
            badge: 'Intelligence',
            title: 'Smart Suggestions & Pipeline Intelligence',
            cards: [
                { icon: 'fa-solid fa-bell', iconColor: '#f59e0b', iconBg: '#fef3c7', title: 'Alerts', desc: 'Bob notifies you when a deal is stale or action is required.' },
                { icon: 'fa-solid fa-bullseye', iconColor: '#ef4444', iconBg: '#fee2e2', title: 'Prioritization', desc: 'The most important deals surface first.' },
                { icon: 'fa-solid fa-clock-rotate-left', iconColor: '#06b6d4', iconBg: '#cffafe', title: 'History', desc: 'Bob remembers your conversations and preferences.' },
                { icon: 'fa-solid fa-shield-halved', iconColor: '#10b981', iconBg: '#dcfce7', title: 'Compliance', desc: 'Automatically verifies CASL and Bill 25 compliance.' },
            ],
            footerText: 'Bob AI — Intelligence Layer',
        },
        {
            id: 17, module: 3, moduleTitle: 'Bob AI Assistant',
            type: 'feature',
            badge: 'Automation',
            title: 'Automated Workflows',
            subtitle: 'Let Bob Work for You',
            content: 'Set up automations that trigger at every pipeline stage. Bob handles the repetitive tasks while you focus on selling.',
            items: [
                'Auto-send a follow-up email after a demo',
                'Create a reminder task when a deal moves',
                'Notify the team when a deal is closed',
                'Update fields automatically',
                'Trigger a workflow based on activity',
            ],
            footerText: 'Module: Automations',
        },
        {
            id: 18, module: 3, moduleTitle: 'Bob AI Assistant',
            type: 'assessment',
            badge: 'Validation',
            title: 'Assessment — Bob AI Usage',
            subtitle: 'Criteria for Mastering Bob',
            kpis: [
                { label: 'Navigation', value: 'Access any module in < 3 sec', color: '#3b82f6' },
                { label: 'Data Entry', value: 'Create contact + opportunity in < 2 min', color: '#10b981' },
                { label: 'Pipeline', value: '100% accuracy 5 consecutive days', color: '#8b5cf6' },
                { label: 'Bob Usage', value: '3+ tasks with Bob AI', color: '#FF4500' },
                { label: 'Automation', value: '1+ workflow configured', color: '#f59e0b' },
            ],
            footerText: 'CRM Mastery — Assessment Criteria',
        },

        // ═══════════════════════════════════════
        // MODULE 4: Pipeline Mastery (19-26)
        // ═══════════════════════════════════════
        {
            id: 19, module: 4, moduleTitle: 'Pipeline Mastery',
            type: 'title',
            badge: 'Module 4',
            title: 'Pipeline\nMastery',
            subtitle: 'The Core of Your Daily Work',
            content: 'Your pipeline is alive. Every morning, it must reflect the exact reality of your deals. It\'s the foundation of all your performance.',
            footerText: 'Pipeline Review & CRM Hygiene — Daily Task',
        },
        {
            id: 20, module: 4, moduleTitle: 'Pipeline Mastery',
            type: 'timeline',
            badge: 'Pipeline Stages',
            title: 'The Opportunity Lifecycle',
            timelineSteps: [
                'Lead — New contact identified, initial interest',
                'Qualified — BANT criteria validated, potential confirmed',
                'Demo — Product presentation delivered, strong interest',
                'Proposal — Proposal sent with pricing',
                'Negotiation — Negotiation in progress, objections handled',
                'Closed Won / Lost — Deal signed or lost, post-mortem analysis',
            ],
            footerText: 'Pipeline: Lead → Qualified → Demo → Proposal → Negotiation → Closed',
        },
        {
            id: 21, module: 4, moduleTitle: 'Pipeline Mastery',
            type: 'grid',
            badge: 'Key Concepts',
            title: 'The 4 Pipeline Pillars',
            cards: [
                { icon: 'fa-solid fa-user', iconColor: '#3b82f6', iconBg: '#dbeafe', title: 'Contact vs Org', desc: 'Contacts are people, orgs are companies. Always link both.' },
                { icon: 'fa-solid fa-pen', iconColor: '#10b981', iconBg: '#dcfce7', title: 'Activity Logging', desc: 'Every call, email and meeting must be logged for AI analysis.' },
                { icon: 'fa-solid fa-robot', iconColor: '#FF4500', iconBg: '#fff3ed', title: 'Bob AI', desc: 'Voice-first assistant that analyzes your pipeline and suggests actions.' },
                { icon: 'fa-solid fa-filter', iconColor: '#8b5cf6', iconBg: '#f3e8ff', title: 'Pipeline Stages', desc: 'Lead → Qualified → Demo → Proposal → Negotiation → Closed.' },
            ],
            footerText: 'Key Concepts — Pipeline Management',
        },
        {
            id: 22, module: 4, moduleTitle: 'Pipeline Mastery',
            type: 'alert',
            badge: 'Golden Rule',
            title: 'Activity Logging — Non-Negotiable',
            subtitle: 'Every interaction must be documented',
            alertType: 'warning',
            content: 'Without activity logging, Bob cannot analyze your pipeline or give you smart suggestions. It\'s the fuel of all AI intelligence.',
            items: [
                'Log every call with summary and next steps',
                'Track every email sent and received',
                'Document every meeting with action items',
                'Bob generates notes automatically after calls',
                'Notes must not contain any sensitive personal data',
            ],
            footerText: 'Compliance: Respect information confidentiality',
        },
        {
            id: 23, module: 4, moduleTitle: 'Pipeline Mastery',
            type: 'checklist',
            badge: 'Daily Task',
            title: 'Pipeline Review — SOP',
            subtitle: 'Every morning — < 15 minutes',
            steps: [
                { number: 1, text: 'Open Croo Digital Experience → Opportunities tab' },
                { number: 2, text: 'Review Bob\'s Smart Suggestions for follow-ups' },
                { number: 3, text: 'Update stages for opportunities that have moved' },
                { number: 4, text: 'Add notes from yesterday\'s calls/meetings' },
                { number: 5, text: 'Flag deals with no activity > 7 days' },
                { number: 6, text: 'Check today\'s planned activities and prepare' },
            ],
            footerText: 'Pipeline Review & CRM Hygiene — Frequency: Daily',
        },
        {
            id: 24, module: 4, moduleTitle: 'Pipeline Mastery',
            type: 'kpi',
            badge: 'Metrics',
            title: 'Pipeline KPIs',
            subtitle: 'Your Daily Targets',
            kpis: [
                { label: 'Pipeline Accuracy', value: '100% deals up to date every morning', color: '#10b981' },
                { label: 'Stale Deals', value: '0 deals > 7 days without activity', color: '#ef4444' },
                { label: 'Notes Coverage', value: '100% of calls have notes within 24h', color: '#3b82f6' },
                { label: 'Time to Complete', value: '< 15 minutes per session', color: '#f59e0b' },
            ],
            footerText: 'Pipeline Review — Success Metrics',
        },
        {
            id: 25, module: 4, moduleTitle: 'Pipeline Mastery',
            type: 'list',
            badge: 'Bob Intelligence',
            title: 'How Bob Helps with Your Pipeline',
            subtitle: 'AI-powered performance assistance',
            items: [
                'Automatically identifies deals with no activity > 7 days',
                'Suggests priority follow-ups based on AI analysis',
                'Detects pipeline changes and alerts on risks',
                'Generates a daily pipeline status summary',
                'Prepares pre-call briefs with all prospect info',
            ],
            footerText: 'Bob AI — Pipeline Intelligence',
        },
        {
            id: 26, module: 4, moduleTitle: 'Pipeline Mastery',
            type: 'assessment',
            badge: 'Checkpoint',
            title: 'Validation — Pipeline Mastery',
            subtitle: 'Are you ready for the next step?',
            kpis: [
                { label: 'Daily Review', value: 'Pipeline review done 5 days in a row', color: '#10b981' },
                { label: 'Data Quality', value: '100% of deals with up-to-date notes', color: '#3b82f6' },
                { label: 'Bob Usage', value: 'Used Bob for 3+ pipeline tasks', color: '#FF4500' },
                { label: 'Stale Detection', value: 'No unflagged deal > 7 days', color: '#ef4444' },
            ],
            footerText: 'Milestone: CRM Certified — Croo Expert',
        },

        // ═══════════════════════════════════════
        // MODULE 5: Prospection (27-33)
        // ═══════════════════════════════════════
        {
            id: 27, module: 5, moduleTitle: 'Prospection & Qualification',
            type: 'title',
            badge: 'Module 5',
            title: 'Prospection',
            subtitle: 'Finding Your Future Clients',
            content: 'Identify and qualify B2B clients who need CRM automation. Build a solid pipeline of 50+ qualified leads in 4 weeks.',
            footerText: 'Skill: Prospection & Lead Qualification • Stage: Foundation',
        },
        {
            id: 28, module: 5, moduleTitle: 'Prospection & Qualification',
            type: 'grid',
            badge: 'Qualification Framework',
            title: 'BANT',
            cards: [
                { icon: 'fa-solid fa-dollar-sign', iconColor: '#3b82f6', iconBg: '#dbeafe', title: 'Budget', desc: '$500-$5,000/month. Confirm allocated CRM budget.' },
                { icon: 'fa-solid fa-user-tie', iconColor: '#8b5cf6', iconBg: '#f3e8ff', title: 'Authority', desc: 'VP Sales or CEO. Identify decision-makers.' },
                { icon: 'fa-solid fa-bullseye', iconColor: '#10b981', iconBg: '#dcfce7', title: 'Need', desc: 'Manual processes slowing growth.' },
                { icon: 'fa-solid fa-clock', iconColor: '#f59e0b', iconBg: '#fef3c7', title: 'Timeline', desc: 'Evaluating this quarter. Urgency confirmed.' },
            ],
            footerText: 'BANT Qualification Framework',
        },
        {
            id: 29, module: 5, moduleTitle: 'Prospection & Qualification',
            type: 'feature',
            badge: 'ICP — Ideal Customer Profile',
            title: 'Your Ideal Customer',
            subtitle: 'The target profile you\'re looking for',
            content: 'Your ICP is a B2B company in digital transformation still using manual tools or spreadsheets to manage sales.',
            items: [
                '> 10 employees with an active sales team',
                'B2B — selling services or products to businesses',
                'Sales team using a manual CRM or spreadsheets',
                'In a digital transformation phase',
                'CRM budget between $500 and $5,000/month',
            ],
            footerText: 'ICP: > 10 employees, B2B, active sales team, manual CRM',
        },
        {
            id: 30, module: 5, moduleTitle: 'Prospection & Qualification',
            type: 'grid',
            badge: 'Signal Detection',
            title: 'Signals to Watch For',
            cards: [
                { icon: 'fa-solid fa-briefcase', iconColor: '#3b82f6', iconBg: '#dbeafe', title: 'Job Postings', desc: 'Company is hiring sales reps → needs tools.' },
                { icon: 'fa-solid fa-money-bill-trend-up', iconColor: '#10b981', iconBg: '#dcfce7', title: 'New Funding', desc: 'Recent funding round → money to invest.' },
                { icon: 'fa-solid fa-code', iconColor: '#8b5cf6', iconBg: '#f3e8ff', title: 'Tech Changes', desc: 'Changes in their technology stack.' },
                { icon: 'fa-solid fa-comment-dots', iconColor: '#ef4444', iconBg: '#fee2e2', title: 'CRM Complaints', desc: 'CRM complaints on social media.' },
            ],
            footerText: 'Signal Detection — Identify Opportunities',
        },
        {
            id: 31, module: 5, moduleTitle: 'Prospection & Qualification',
            type: 'checklist',
            badge: 'Daily Task',
            title: 'Outbound Prospecting Block — SOP',
            subtitle: 'Dedicated 2h block — Target: 20 touchpoints/day',
            steps: [
                { number: 1, text: 'Pull today\'s target list from Croo (filtered by ICP criteria)' },
                { number: 2, text: 'Research 5-10 companies: news, tech stack, growth signals' },
                { number: 3, text: 'Draft personalized cold emails with Bob AI' },
                { number: 4, text: 'Verify CASL compliance (consent, unsubscribe, identification)' },
                { number: 5, text: 'Send emails and LinkedIn InMail messages' },
                { number: 6, text: 'Log all activities in Croo with follow-up dates' },
                { number: 7, text: 'Check Bob\'s hot response detection' },
            ],
            footerText: 'Outbound Prospecting Block — Frequency: Daily',
        },
        {
            id: 32, module: 5, moduleTitle: 'Prospection & Qualification',
            type: 'kpi',
            badge: 'Metrics',
            title: 'Prospection KPIs',
            subtitle: 'Your Weekly Targets',
            kpis: [
                { label: 'Touchpoints/Day', value: '20+ contacts per day', color: '#3b82f6' },
                { label: 'Email Open Rate', value: '> 20%', color: '#10b981' },
                { label: 'Reply Rate', value: '> 3%', color: '#8b5cf6' },
                { label: 'Qualified Leads/Week', value: '5+', color: '#f59e0b' },
                { label: 'CASL Compliance', value: '100%', color: '#ef4444' },
            ],
            footerText: 'Prospection — Success Metrics',
        },
        {
            id: 33, module: 5, moduleTitle: 'Prospection & Qualification',
            type: 'list',
            badge: 'Bob for Prospection',
            title: 'How Bob Helps You Prospect',
            subtitle: 'Conversation starters for your prospecting block',
            items: [
                '"Bob, analyze my CRM and identify contacts that match our ICP"',
                '"Bob, which companies in my pipeline are in digital transformation?"',
                '"Bob, score this lead against BANT criteria"',
                '"Bob, draft a first-contact message for this prospect"',
                '"Bob, show me inactive leads that deserve a follow-up"',
            ],
            footerText: 'Bob AI — Prospection Intelligence',
        },

        // ═══════════════════════════════════════
        // MODULE 6: Email & Compliance (34-40)
        // ═══════════════════════════════════════
        {
            id: 34, module: 6, moduleTitle: 'Email Writing & Compliance',
            type: 'title',
            badge: 'Module 6',
            title: 'Email Writing',
            subtitle: 'The Art of Outreach',
            content: 'Write impactful cold emails, nurture sequences and targeted campaigns. All while staying 100% CASL and Bill 25 compliant.',
            footerText: 'Skill: Email Writing & Outreach • Stage: Foundation',
        },
        {
            id: 35, module: 6, moduleTitle: 'Email Writing & Compliance',
            type: 'grid',
            badge: 'Templates',
            title: '5 Proven Email Templates',
            cards: [
                { icon: 'fa-solid fa-paper-plane', iconColor: '#3b82f6', iconBg: '#dbeafe', title: 'Initial Outreach', desc: 'Personalized first contact based on research.' },
                { icon: 'fa-solid fa-bolt', iconColor: '#f59e0b', iconBg: '#fef3c7', title: 'Trigger-based', desc: 'Triggered by an event (funding, job post).' },
                { icon: 'fa-solid fa-trophy', iconColor: '#10b981', iconBg: '#dcfce7', title: 'Case Study', desc: 'Share concrete results from a similar client.' },
                { icon: 'fa-solid fa-calculator', iconColor: '#8b5cf6', iconBg: '#f3e8ff', title: 'ROI Calculator', desc: 'Help the prospect calculate their potential ROI.' },
                { icon: 'fa-solid fa-hand-wave', iconColor: '#ef4444', iconBg: '#fee2e2', title: 'Break-up', desc: 'Last email — creates urgency without pressure.' },
            ],
            footerText: 'Email Templates — SaaS CRM Sales',
        },
        {
            id: 36, module: 6, moduleTitle: 'Email Writing & Compliance',
            type: 'timeline',
            badge: 'Sequence',
            title: 'Optimal Follow-up Cadence',
            timelineSteps: [
                'Day 1 — Initial Outreach: personalized first contact',
                'Day 3 — Light follow-up: added value, no pressure',
                'Day 7 — Case study: social proof, concrete results',
                'Day 14 — ROI Calculator: personalized numbers',
                'Day 21 — Break-up email: last contact, create urgency',
            ],
            footerText: 'Email Sequence Cadence — 5 steps over 21 days',
        },
        {
            id: 37, module: 6, moduleTitle: 'Email Writing & Compliance',
            type: 'alert',
            badge: 'Regulation',
            title: 'CASL — Canada\'s Anti-Spam Legislation',
            subtitle: 'Express consent required',
            alertType: 'warning',
            content: 'Every commercial email in Canada requires express consent. Violations can cost up to $10M per infraction.',
            items: [
                'Express consent required before any commercial email',
                'Sender identification mandatory (name + address)',
                'Functional unsubscribe mechanism in every email',
                'No misleading subject lines or sender names',
                'Penalties: up to $10M per violation',
            ],
            footerText: 'CASL — Canada\'s Anti-Spam Legislation',
        },
        {
            id: 38, module: 6, moduleTitle: 'Email Writing & Compliance',
            type: 'alert',
            badge: 'Regulation',
            title: 'Bill 25 — Québec Data Protection',
            subtitle: 'Privacy and consent',
            alertType: 'info',
            content: 'Québec\'s modernized privacy protection framework. Requires consent for collection and use of personal information.',
            items: [
                'Explicit consent for personal data collection',
                'Mandatory privacy impact assessments',
                'Data portability rights',
                'Breach notification within 72 hours',
                'Also: PIPEDA at the federal level',
            ],
            footerText: 'Bill 25 — Québec Privacy Law',
        },
        {
            id: 39, module: 6, moduleTitle: 'Email Writing & Compliance',
            type: 'checklist',
            badge: 'Weekly Task',
            title: 'Email Campaign SOP',
            subtitle: 'Weekly nurture campaign',
            steps: [
                { number: 1, text: 'Analyze previous campaign performance (open rate, CTR, replies)' },
                { number: 2, text: 'Segment audience: new leads vs warm leads vs re-engagement' },
                { number: 3, text: 'Write content: subject + body + CTA' },
                { number: 4, text: 'Have Bob review copy for tone and compliance' },
                { number: 5, text: 'Schedule send (Tue-Thu, 9-11am ET)' },
                { number: 6, text: 'Set up A/B test on subject line' },
                { number: 7, text: 'Document results in the tracker' },
            ],
            footerText: 'Email Campaign — Nurture Sequence • Frequency: Weekly',
        },
        {
            id: 40, module: 6, moduleTitle: 'Email Writing & Compliance',
            type: 'kpi',
            badge: 'Metrics',
            title: 'Email KPIs',
            subtitle: 'Your Benchmarks to Hit',
            kpis: [
                { label: 'Open Rate', value: '> 20%', color: '#10b981' },
                { label: 'Click Rate', value: '> 3%', color: '#3b82f6' },
                { label: 'Reply Rate', value: '> 1%', color: '#8b5cf6' },
                { label: 'Unsubscribe Rate', value: '< 0.5%', color: '#ef4444' },
                { label: 'Bounce Rate', value: '< 2%', color: '#f59e0b' },
            ],
            footerText: 'Email Campaign — Success Metrics',
        },

        // ═══════════════════════════════════════
        // MODULE 7: Demo & Closing (41-47)
        // ═══════════════════════════════════════
        {
            id: 41, module: 7, moduleTitle: 'Demo & Closing',
            type: 'title',
            badge: 'Module 7',
            title: 'Demo &\nClosing',
            subtitle: 'Convert Your Prospects into Clients',
            content: 'Deliver impactful demos of Croo Digital Experience. Focus on ROI: time saved, AI insights, automated follow-ups.',
            footerText: 'Skills: Solution Demo & Value Selling + Negotiation & Closing',
        },
        {
            id: 42, module: 7, moduleTitle: 'Demo & Closing',
            type: 'timeline',
            badge: 'Demo Flow',
            title: '30-Minute Demo Structure',
            timelineSteps: [
                'Discovery (10 min) — Understand processes, team size, pain points',
                'Tailored Demo (15 min) — Show features mapped to their specific needs',
                'Next Steps (5 min) — Timeline, decision-makers, trial or proposal',
            ],
            footerText: 'Demo Flow: 10 min discovery → 15 min demo → 5 min next steps',
        },
        {
            id: 43, module: 7, moduleTitle: 'Demo & Closing',
            type: 'feature',
            badge: 'Methodology',
            title: 'Challenger Sale',
            subtitle: 'Teach — Tailor — Take Control',
            content: 'Don\'t be a simple presenter. Reframe the prospect\'s thinking. Teach them something new about their own business before presenting your solution.',
            items: [
                'Teach — Share an insight the prospect doesn\'t know',
                'Tailor — Adapt your message to their specific reality',
                'Take Control — Guide the conversation toward a decision',
                'Reframe their problem before presenting your solution',
                'Use data and concrete cases',
            ],
            footerText: 'Challenger Sale Methodology',
        },
        {
            id: 44, module: 7, moduleTitle: 'Demo & Closing',
            type: 'feature',
            badge: 'ROI',
            title: 'ROI Calculator',
            subtitle: 'Hours Saved × Number of Reps × Hourly Cost',
            content: 'ROI is the most powerful argument. Concretely calculate how much time and money Croo saves each representative.',
            kpis: [
                { label: 'Time Saved / Rep / Week', value: '5-10 hours', color: '#10b981' },
                { label: 'Cost per Hour', value: '$35-75', color: '#3b82f6' },
                { label: 'Annual Savings (10 reps)', value: '$91K-$390K', color: '#8b5cf6' },
                { label: 'Croo Investment', value: '$4,680-$5,880/year', color: '#FF4500' },
            ],
            footerText: 'ROI Calculator — Live vs Recorded: always prefer live',
        },
        {
            id: 45, module: 7, moduleTitle: 'Demo & Closing',
            type: 'grid',
            badge: 'Objection Handling',
            title: 'Top 4 CRM Objections',
            cards: [
                { icon: 'fa-solid fa-database', iconColor: '#3b82f6', iconBg: '#dbeafe', title: '"We already have a CRM"', desc: 'Yes, but does it have an integrated AI assistant that analyzes your pipeline?' },
                { icon: 'fa-solid fa-dollar-sign', iconColor: '#ef4444', iconBg: '#fee2e2', title: '"It\'s too expensive"', desc: 'Let\'s calculate the cost of NOT changing. Cost of inaction.' },
                { icon: 'fa-solid fa-users', iconColor: '#f59e0b', iconBg: '#fef3c7', title: '"The team won\'t adopt it"', desc: 'Bob makes adoption natural: voice-first, AI that does the work.' },
                { icon: 'fa-solid fa-plug', iconColor: '#8b5cf6', iconBg: '#f3e8ff', title: '"We need X integration"', desc: 'Open API + integration marketplace. What tools do you use?' },
            ],
            footerText: 'Objection Handling — CRM Objections Playbook',
        },
        {
            id: 46, module: 7, moduleTitle: 'Demo & Closing',
            type: 'grid',
            badge: 'Pricing',
            title: 'Pricing Options',
            cards: [
                { icon: 'fa-solid fa-calendar-days', iconColor: '#3b82f6', iconBg: '#dbeafe', title: 'Monthly', desc: '$49/user/month. Maximum flexibility, no commitment.' },
                { icon: 'fa-solid fa-calendar-check', iconColor: '#10b981', iconBg: '#dcfce7', title: 'Annual', desc: '$39/user/month. 20% discount for annual commitment.' },
                { icon: 'fa-solid fa-rocket', iconColor: '#8b5cf6', iconBg: '#f3e8ff', title: 'Onboarding', desc: 'Onboarding package included for contracts > 10 seats.' },
                { icon: 'fa-solid fa-handshake', iconColor: '#FF4500', iconBg: '#fff3ed', title: 'Mutual Action Plan', desc: 'Shared timeline: trial → eval → decision → onboarding.' },
            ],
            footerText: 'Pricing: Monthly $49/user vs Annual $39/user (20% discount)',
        },
        {
            id: 47, module: 7, moduleTitle: 'Demo & Closing',
            type: 'checklist',
            badge: 'Weekly Task',
            title: 'Deal Negotiation SOP',
            subtitle: 'Managing deals in negotiation phase',
            steps: [
                { number: 1, text: 'Review deals in \'Negotiation\' stage in the Croo pipeline' },
                { number: 2, text: 'Prepare proposal with pricing options' },
                { number: 3, text: 'Build ROI business case (savings vs investment)' },
                { number: 4, text: 'Address final objections with proof and references' },
                { number: 5, text: 'Send proposal and schedule decision call' },
                { number: 6, text: 'Follow up within 48h if no response' },
                { number: 7, text: 'Update deal stage and log result in Croo' },
            ],
            footerText: 'Deal Negotiation & Close — Frequency: Weekly',
        },

        // ═══════════════════════════════════════
        // MODULE 8: Graduation (48-50)
        // ═══════════════════════════════════════
        {
            id: 48, module: 8, moduleTitle: 'Graduation',
            type: 'grid',
            badge: 'Milestones',
            title: 'Your Progression Path',
            cards: [
                { icon: 'fa-solid fa-certificate', iconColor: '#3b82f6', iconBg: '#dbeafe', title: 'CRM Certified', desc: 'Demo all modules, pipeline up to date 5 days, Bob 3+ tasks.' },
                { icon: 'fa-solid fa-chart-line', iconColor: '#10b981', iconBg: '#dcfce7', title: 'First Pipeline Built', desc: '50+ qualified leads, 200+ touchpoints, 100% CASL compliant.' },
                { icon: 'fa-solid fa-trophy', iconColor: '#f59e0b', iconBg: '#fef3c7', title: 'First Deal Closed', desc: '10+ demos, first contract signed, ARR > $5,000.' },
                { icon: 'fa-solid fa-crown', iconColor: '#FF4500', iconBg: '#fff3ed', title: 'Quota Crusher', desc: '> 100% quota, 3x pipeline, 1+ upsell, mentoring a new rep.' },
            ],
            footerText: '4 Milestones: Onboarding → Foundation → Practice → Mastery',
        },
        {
            id: 49, module: 8, moduleTitle: 'Graduation',
            type: 'feature',
            badge: 'Next Level',
            title: 'Account Management & Expansion',
            subtitle: 'The Next Step in Your Career',
            content: 'Once certified, you can develop your account management skills. Retain your clients, identify upsell opportunities and become a trusted advisor.',
            items: [
                'Identify upsell and cross-sell opportunities',
                'Conduct Quarterly Business Reviews (QBR)',
                'Build champion relationships within client organizations',
                'Maintain Net Revenue Retention > 110%',
                'Generate referrals from satisfied clients',
            ],
            footerText: 'Skill: Account Management & Expansion • Stage: Mastery',
        },
        {
            id: 50, module: 8, moduleTitle: 'Graduation',
            type: 'title',
            badge: 'Congratulations 🚀',
            title: 'You\'re Ready',
            subtitle: 'Go crush it!',
            content: 'You now have all the knowledge to master Croo Digital Experience. Your pipeline awaits. Bob is by your side. Let\'s go!',
            footerText: 'CRM Mastery — Croo Digital Experience • The Croo Group',
        },
    ];

    // ── Lifecycle ──────────────────────────────

    ngOnInit(): void {
        // Create training session + auto-start mission
        this.trainingService.createSession('crm-mastery').subscribe({
            next: (session) => {
                this.sessionId = session.id;
                console.log('[Training] session created:', session.id);
                // Auto-start the training mission with Bob
                this.startTrainingWithBob();
            },
            error: (err) => console.error('[Training] session creation failed:', err),
        });

        // Subscribe to Bob slide-change actions
        this.subs.push(
            this.bobActionService.action$.subscribe((action: BobAction) => {
                if (action.type === 'change_slide') {
                    if (action.direction === 'next') {
                        this.nextSlide();
                    } else if (action.direction === 'previous') {
                        this.prevSlide();
                    } else if (action.direction === 'goto' && action.slide_number) {
                        this.goToSlide(action.slide_number - 1); // 1-indexed from LLM
                    }
                }
            })
        );
    }

    ngOnDestroy(): void {
        this.subs.forEach((s) => s.unsubscribe());
    }

    // ── Slide navigation ──────────────────────

    get currentSlideData(): Slide {
        return this.slides[this.currentSlide];
    }

    get totalSlides(): number {
        return this.slides.length;
    }

    get progressPercent(): number {
        return Math.round(((this.currentSlide + 1) / this.totalSlides) * 100);
    }

    goToSlide(index: number): void {
        if (index >= 0 && index < this.totalSlides) {
            this.currentSlide = index;
            this.onSlideChange();
        }
    }

    nextSlide(): void {
        if (this.currentSlide < this.totalSlides - 1) {
            this.currentSlide++;
            this.onSlideChange();
        }
    }

    prevSlide(): void {
        if (this.currentSlide > 0) {
            this.currentSlide--;
            this.onSlideChange();
        }
    }

    // ── Bob Training ──────────────────────────

    startTrainingWithBob(): void {
        this.trainingStarted = true;
        this.startPolling();

        const slide = this.currentSlideData;
        this.bobActionService.startMission({
            missionPrompt: this.buildMissionPrompt(slide),
            initialMessage: `Let's start the CRM Mastery training! I'm ready to learn about "${slide.title}".`,
            missionContext: {
                training_session_id: this.sessionId,
                training_slug: 'crm-mastery',
            },
        });
    }

    private buildMissionPrompt(slide: Slide): string {
        return `You are Bob, a CRM training instructor for Croo Digital Experience.
You are conducting the "CRM Mastery" onboarding training for a new sales rep.

TRAINING SESSION ID: ${this.sessionId}
CURRENT SLIDE: #${slide.id} — "${slide.title}"
MODULE: ${slide.module} - ${slide.moduleTitle}
SLIDE CONTENT: ${slide.content || ''}
${slide.cards ? 'CARDS: ' + slide.cards.map(c => `${c.title}: ${c.desc}`).join(' | ') : ''}
${slide.items ? 'KEY POINTS: ' + slide.items.join(', ') : ''}
${slide.timelineSteps ? 'STEPS: ' + slide.timelineSteps.join(' → ') : ''}

YOUR ROLE:
- Explain the current slide content clearly and engagingly
- Answer any questions about the training material
- When the user asks to "take a note" or "write that down", call save_training_note with session_id="${this.sessionId}" and slide_id=${this.currentSlide}
- When the user mentions a missing feature/integration (e.g. "we need Zoho", "I wish we had X"), call save_missing_element with session_id="${this.sessionId}"
- When the user says "next slide", "previous slide", or "go to slide X", call change_training_slide

VOICE STYLE: Warm, clear, concise. Short sentences for voice clarity. No markdown.
LANGUAGE: Match the user's language — English or French.`;
    }

    private onSlideChange(): void {
        if (!this.sessionId) return;
        // Update slide in DB
        this.trainingService.updateSlide(this.sessionId, this.currentSlide).subscribe();

        // Update Bob's mission context if training has started so he can explain the new slide
        if (this.trainingStarted) {
            const slide = this.currentSlideData;
            this.bobActionService.updateMission({
                missionPrompt: this.buildMissionPrompt(slide),
                initialMessage: `The user has moved to SLIDE #${slide.id} — "${slide.title}". Please briefly explain the concept on this new slide.`,
                missionContext: {
                    training_session_id: this.sessionId,
                    training_slug: 'crm-mastery',
                    current_slide: slide.id,
                },
            });
        }
    }

    private startPolling(): void {
        this.subs.push(
            interval(3000).subscribe(() => {
                if (!this.sessionId) return;
                this.trainingService.getNotes(this.sessionId).subscribe({
                    next: (notes) => (this.notes = notes),
                });
                this.trainingService.getMissing(this.sessionId).subscribe({
                    next: (items) => (this.missingElements = items),
                });
            })
        );
    }

    // ── Helpers ────────────────────────────────

    noteIcon(type: string): string {
        switch (type) {
            case 'action': return 'fa-solid fa-bolt';
            case 'important': return 'fa-solid fa-star';
            default: return 'fa-solid fa-lightbulb';
        }
    }

    noteColor(type: string): string {
        switch (type) {
            case 'action': return 'blue';
            case 'important': return 'red';
            default: return 'yellow';
        }
    }

    categoryIcon(cat: string): string {
        switch (cat) {
            case 'feature': return 'fa-solid fa-puzzle-piece';
            case 'process': return 'fa-solid fa-sitemap';
            default: return 'fa-solid fa-plug';
        }
    }
}
