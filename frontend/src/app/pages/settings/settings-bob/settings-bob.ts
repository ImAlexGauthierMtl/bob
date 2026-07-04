import { Component, OnDestroy, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { Store } from '@ngrx/store';
import { Subscription } from 'rxjs';
import {
    BobMemorySettingsResponse,
    BobRuntimeAgent,
    BobRuntimeMcpCapability,
    BobRuntimeMcpFamily,
    BobRuntimeProvider,
    BobRuntimeSettingsResponse,
    BobRuntimeSkill,
    BobRuntimeTool,
} from '../../../shared/services/bob-assistant-settings.service';
import {
    createBobRuntimeAgent,
    createBobRuntimeSkill,
    createBobRuntimeTool,
    loadBobAssistantSettings,
} from '../../../store/bob-assistant-settings/bob-assistant-settings.actions';
import {
    selectBobAssistantSettingsError,
    selectBobAssistantSettingsNotice,
    selectBobAssistantMemorySettings,
    selectBobAssistantRuntimeSettings,
    selectBobAssistantRuntimeSaving,
} from '../../../store/bob-assistant-settings/bob-assistant-settings.selectors';

@Component({
    selector: 'croo-settings-bob',
    standalone: true,
    imports: [CommonModule, RouterLink, FormsModule],
    templateUrl: './settings-bob.html',
    styleUrls: ['../settings-shared.css', './settings-bob.css'],
})
export class SettingsBobComponent implements OnInit, OnDestroy {
    private store = inject(Store);
    private subscriptions = new Subscription();
    private runtimeSavingSignal = this.store.selectSignal(selectBobAssistantRuntimeSaving);

    // Runtime
    runtimeProviders: BobRuntimeProvider[] = [];
    runtimeAgents: BobRuntimeAgent[] = [];
    runtimeSkills: BobRuntimeSkill[] = [];
    runtimeTools: BobRuntimeTool[] = [];
    runtimeMcpFamilies: BobRuntimeMcpFamily[] = [];
    runtimeMcpCapabilities: BobRuntimeMcpCapability[] = [];
    runtimeMemory: Record<string, string> = {};
    memorySettings: BobMemorySettingsResponse | null = null;
    runtimeLoading = false;
    newAgentName = '';
    selectedAgentSkillIds: string[] = [];
    selectedAgentToolIds: string[] = [];
    newSkillName = '';
    newToolName = '';
    newToolFamily = 'custom';

    // UI state
    runtimeNotice = '';

    get isRuntimeSaving(): boolean {
        return this.runtimeSavingSignal();
    }

    get runtimeMcpFamiliesWithCapabilities(): BobRuntimeMcpFamily[] {
        return this.runtimeMcpFamilies.map((family) => ({
            ...family,
            capability_items: this.runtimeMcpCapabilities.filter((capability) => capability.family === family.family),
        }));
    }

    ngOnInit(): void {
        this.subscriptions.add(
            this.store.select(selectBobAssistantRuntimeSettings).subscribe((runtime) => {
                if (runtime) {
                    this.applyRuntimeSettings(runtime);
                    this.runtimeLoading = false;
                }
            }),
        );
        this.subscriptions.add(
            this.store.select(selectBobAssistantMemorySettings).subscribe((memorySettings) => {
                this.memorySettings = memorySettings;
            }),
        );
        this.subscriptions.add(
            this.store.select(selectBobAssistantSettingsNotice).subscribe((notice) => {
                if (notice) this.flashMessage(notice);
            }),
        );
        this.subscriptions.add(
            this.store.select(selectBobAssistantSettingsError).subscribe((error) => {
                if (error) this.flashMessage(error);
            }),
        );
        this.loadRuntimeSettings();
    }

    ngOnDestroy(): void {
        this.subscriptions.unsubscribe();
    }

    loadRuntimeSettings(): void {
        this.runtimeLoading = true;
        this.store.dispatch(loadBobAssistantSettings());
    }

    createAgent(): void {
        const name = this.newAgentName.trim();
        if (!name) return;
        this.store.dispatch(createBobRuntimeAgent({ agent: {
            name,
            description: 'Agent ajoute depuis CDE Settings',
            skills: [...this.selectedAgentSkillIds],
            tools: [...this.selectedAgentToolIds],
        } }));
        this.newAgentName = '';
        this.selectedAgentSkillIds = [];
        this.selectedAgentToolIds = [];
    }

    createSkill(): void {
        const name = this.newSkillName.trim();
        if (!name) return;
        this.store.dispatch(createBobRuntimeSkill({ skill: {
            name,
            description: 'Skill ajoute depuis CDE Settings',
            scope: 'shared_clean',
        } }));
        this.newSkillName = '';
    }

    createTool(): void {
        const name = this.newToolName.trim();
        if (!name) return;
        this.store.dispatch(createBobRuntimeTool({ tool: {
            name,
            family: this.newToolFamily || 'custom',
            risk: 'read',
            description: 'Tool ajoute depuis CDE Settings',
        } }));
        this.newToolName = '';
    }

    isAgentSkillSelected(skillId: string): boolean {
        return this.selectedAgentSkillIds.includes(skillId);
    }

    toggleAgentSkill(skillId: string, checked: boolean): void {
        this.selectedAgentSkillIds = checked
            ? Array.from(new Set([...this.selectedAgentSkillIds, skillId]))
            : this.selectedAgentSkillIds.filter((id) => id !== skillId);
    }

    isAgentToolSelected(toolId: string): boolean {
        return this.selectedAgentToolIds.includes(toolId);
    }

    toggleAgentTool(toolId: string, checked: boolean): void {
        this.selectedAgentToolIds = checked
            ? Array.from(new Set([...this.selectedAgentToolIds, toolId]))
            : this.selectedAgentToolIds.filter((id) => id !== toolId);
    }

    memoryDegradedLabel(detail: { code?: string; message?: string } | string | null): string {
        if (!detail) return 'unavailable';
        if (typeof detail === 'string') return detail;
        return detail.code || detail.message || 'unavailable';
    }

    runtimeStatusLabel(value: string | undefined | null): string {
        if (!value) return 'pending';
        return value.replace(/_/g, ' ');
    }

    statusVariant(value: string | undefined | null): string {
        if (!value) return 'pending';
        const normalized = value.toLowerCase();
        if ([
            'ready',
            'ok',
            'configured',
            'runtime_backend_managed',
            'ported_active',
            'platform_contract_active',
            'removed_from_cde_runtime',
            'local_active',
            'local_runtime_active',
            'local_adapter_active',
            'remote_adapter_configured',
        ].includes(normalized)) return 'ok';
        if ([
            'disabled',
            'not_configured',
            'missing',
            'missing_secret',
            'needs_configuration',
            'contract_pending',
            'contract_pending_adapter',
            'partially_active',
            'confirmation_gated_contract',
            'local_adapter_disabled',
            'remote_adapter_missing_secret',
            'legacy_settings_surface_active',
            'in_progress',
        ].includes(normalized)) return 'warn';
        return normalized.includes('error') || normalized.includes('failed') ? 'error' : 'warn';
    }

    private applyRuntimeSettings(settings: BobRuntimeSettingsResponse): void {
        this.runtimeProviders = settings.providers;
        this.runtimeAgents = settings.agents;
        this.runtimeSkills = settings.skills;
        this.runtimeTools = settings.tools;
        this.runtimeMcpFamilies = settings.mcp?.families || [];
        this.runtimeMcpCapabilities = settings.mcp?.capabilities || [];
        this.runtimeMemory = settings.memory || {};
    }

    private flashMessage(message: string): void {
        this.runtimeNotice = message;
        setTimeout(() => this.runtimeNotice = '', 3000);
    }
}
