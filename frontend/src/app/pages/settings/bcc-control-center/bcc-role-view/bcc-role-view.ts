import { Component, OnInit, inject } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { KeyValuePipe, UpperCasePipe } from '@angular/common';
import {
    BccService, BccRoleDetail, BccSkill, BccTask, BccMilestone,
} from '../../../../shared/services/bcc.service';

@Component({
    selector: 'croo-bcc-role-view',
    standalone: true,
    imports: [RouterLink, KeyValuePipe, UpperCasePipe],
    templateUrl: './bcc-role-view.html',
    styleUrls: [
        '../../settings-shared.css',
        '../../../organization-detail/organization-detail.css',
        '../bcc-role-detail/bcc-role-detail.css',
    ],
})
export class BccRoleViewComponent implements OnInit {
    role: BccRoleDetail | null = null;
    isLoading = true;
    activeTab = 'skills';
    orgId = '';
    expandedSkills = new Set<string>();
    expandedTasks = new Set<string>();

    readonly stages = ['onboarding', 'foundation', 'practice', 'mastery'];
    readonly stageLabels: Record<string, string> = {
        onboarding: '🔰 Onboarding',
        foundation: '📘 Foundation',
        practice: '🎯 Practice',
        mastery: '🏆 Mastery',
    };
    readonly stageDescs: Record<string, string> = {
        onboarding: 'Jour 1-5 — Découverte et orientation',
        foundation: 'Semaines 1-4 — Bases et fondamentaux',
        practice: 'Mois 1-3 — Pratique guidée et autonomie',
        mastery: 'Mois 3+ — Expertise et leadership',
    };

    private bccService = inject(BccService);
    private route = inject(ActivatedRoute);

    ngOnInit(): void {
        this.orgId = this.route.snapshot.paramMap.get('orgId') || '';
        const roleId = this.route.snapshot.paramMap.get('roleId');
        if (roleId) {
            this.loadRole(roleId);
        }
    }

    loadRole(id: string): void {
        this.isLoading = true;
        this.bccService.getRole(id).subscribe({
            next: (role) => {
                this.role = role;
                this.isLoading = false;
            },
            error: () => { this.isLoading = false; },
        });
    }

    setActiveTab(tab: string): void {
        this.activeTab = tab;
    }

    // ── Skill helpers ────────────────────────────────
    getSkillsByStage(stage: string): BccSkill[] {
        if (!this.role) return [];
        return this.role.skills
            .filter((s) => s.stage === stage)
            .sort((a, b) => b.priority - a.priority);
    }

    getSkillTypeIcon(type: string): string {
        switch (type) {
            case 'soft': return 'fa-solid fa-heart';
            case 'tool': return 'fa-solid fa-screwdriver-wrench';
            default: return 'fa-solid fa-cog';
        }
    }

    getSkillTypeLabel(type: string): string {
        switch (type) {
            case 'soft': return 'Soft Skill';
            case 'tool': return 'Tool';
            default: return 'Hard Skill';
        }
    }

    toggleSkill(skillId: string): void {
        if (this.expandedSkills.has(skillId)) {
            this.expandedSkills.delete(skillId);
        } else {
            this.expandedSkills.add(skillId);
        }
    }

    isSkillExpanded(skillId: string): boolean {
        return this.expandedSkills.has(skillId);
    }

    getPriorityDots(priority: number): number[] {
        return Array(priority).fill(0);
    }

    // ── Task helpers ─────────────────────────────────
    getTasksByStage(stage: string): BccTask[] {
        if (!this.role) return [];
        return this.role.tasks.filter((t) => t.stage === stage);
    }

    getFrequencyLabel(freq: string): string {
        switch (freq) {
            case 'daily': return 'Quotidien';
            case 'weekly': return 'Hebdo';
            case 'monthly': return 'Mensuel';
            case 'ad_hoc': return 'Ponctuel';
            default: return freq;
        }
    }

    getFrequencyColor(freq: string): string {
        switch (freq) {
            case 'daily': return '#10B981';
            case 'weekly': return '#3B82F6';
            case 'monthly': return '#8B5CF6';
            default: return '#6B7280';
        }
    }

    toggleTask(taskId: string): void {
        if (this.expandedTasks.has(taskId)) {
            this.expandedTasks.delete(taskId);
        } else {
            this.expandedTasks.add(taskId);
        }
    }

    isTaskExpanded(taskId: string): boolean {
        return this.expandedTasks.has(taskId);
    }

    // ── Milestone helpers ────────────────────────────
    getMilestonesByStage(stage: string): BccMilestone[] {
        if (!this.role) return [];
        return this.role.milestones
            .filter((m) => m.stage === stage)
            .sort((a, b) => a.sort_order - b.sort_order);
    }

    // ── KPI helpers ──────────────────────────────────
    getKpiEntries(): [string, unknown][] {
        if (!this.role?.kpis) return [];
        return Object.entries(this.role.kpis);
    }

    formatKpiKey(key: string): string {
        return key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    }
}
