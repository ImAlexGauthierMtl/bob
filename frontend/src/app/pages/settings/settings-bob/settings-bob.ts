import { Component, OnDestroy, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { Store } from '@ngrx/store';
import { Subscription } from 'rxjs';
import {
    BobConversationPersonality,
    BobLanguageOption,
    BobMemorySettingsResponse,
    BobRuntimeConversionInventory,
    BobRuntimeConversionModule,
    BobRuntimeConversionSurface,
    BobRuntimeAgent,
    BobRuntimeMcpCapability,
    BobRuntimeMcpFamily,
    BobRuntimeProvider,
    BobRuntimeSettingsResponse,
    BobRuntimeSkill,
    BobRuntimeTool,
    BobVoiceOption,
    BobVoiceSettings,
} from '../../../shared/services/bob-assistant-settings.service';
import {
    createBobRuntimeAgent,
    createBobRuntimeSkill,
    createBobRuntimeTool,
    loadBobAssistantSettings,
    saveBobAssistantSettings,
} from '../../../store/bob-assistant-settings/bob-assistant-settings.actions';
import {
    selectBobAssistantSettingsError,
    selectBobAssistantSettingsNotice,
    selectBobAssistantSettingsOptions,
    selectBobAssistantSettingsPersonality,
    selectBobAssistantMemorySettings,
    selectBobAssistantRuntimeSettings,
    selectBobAssistantRuntimeSaving,
    selectBobAssistantSettingsSaving,
    selectBobAssistantSettingsVoice,
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
    private savingSignal = this.store.selectSignal(selectBobAssistantSettingsSaving);
    private runtimeSavingSignal = this.store.selectSignal(selectBobAssistantRuntimeSaving);

    // Personality
    tone = 'professional';
    formality = 0.5;
    responseLength = 'balanced';
    language = 'auto';
    creativity = 0.3;
    emojiUsage = false;

    // Voice
    selectedVoice = 'autumn';
    voiceSpeed = 1.0;
    autoListen = true;

    // Options
    availableVoices: BobVoiceOption[] = [];
    availableTones: string[] = [];
    availableLanguages: BobLanguageOption[] = [];
    private isLoadingVoices = false;

    // Runtime
    runtimeProviders: BobRuntimeProvider[] = [];
    runtimeAgents: BobRuntimeAgent[] = [];
    runtimeSkills: BobRuntimeSkill[] = [];
    runtimeTools: BobRuntimeTool[] = [];
    runtimeMcpFamilies: BobRuntimeMcpFamily[] = [];
    runtimeMcpCapabilities: BobRuntimeMcpCapability[] = [];
    runtimeMemory: Record<string, string> = {};
    runtimeConversionInventory: BobRuntimeConversionInventory | null = null;
    memorySettings: BobMemorySettingsResponse | null = null;
    runtimeLoading = false;
    runtimeMessage = '';
    newAgentName = '';
    selectedAgentSkillIds: string[] = [];
    selectedAgentToolIds: string[] = [];
    newSkillName = '';
    newToolName = '';
    newToolFamily = 'custom';

    // UI state
    saveMessage = '';

    get isSaving(): boolean {
        return this.savingSignal();
    }

    get isRuntimeSaving(): boolean {
        return this.runtimeSavingSignal();
    }

    get runtimeMcpFamiliesWithCapabilities(): BobRuntimeMcpFamily[] {
        return this.runtimeMcpFamilies.map((family) => ({
            ...family,
            capability_items: this.runtimeMcpCapabilities.filter((capability) => capability.family === family.family),
        }));
    }

    get conversionModules(): BobRuntimeConversionModule[] {
        return this.runtimeConversionInventory?.settings_modules || [];
    }

    get conversionSurfaces(): BobRuntimeConversionSurface[] {
        return this.runtimeConversionInventory?.surfaces || [];
    }

    ngOnInit(): void {
        this.subscriptions.add(
            this.store.select(selectBobAssistantSettingsPersonality).subscribe((personality) => {
                if (personality) this.applyPersonality(personality);
            }),
        );
        this.subscriptions.add(
            this.store.select(selectBobAssistantSettingsVoice).subscribe((voice) => {
                if (voice) this.applyVoice(voice);
            }),
        );
        this.subscriptions.add(
            this.store.select(selectBobAssistantSettingsOptions).subscribe((options) => {
                this.availableTones = options.availableTones;
                this.availableLanguages = options.availableLanguages;
                this.availableVoices = options.availableVoices;
            }),
        );
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

    saveSettings(): void {
        this.saveMessage = '';

        this.store.dispatch(saveBobAssistantSettings({
            personality: this.currentPersonality(),
            voice: this.currentVoice(),
        }));
    }

    onLanguageChange(): void {
        this.refreshVoicesForLanguage();
    }

    selectVoice(voiceId: string): void {
        this.selectedVoice = voiceId;
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

    getSelectedVoiceName(): string {
        const v = this.availableVoices.find(v => v.id === this.selectedVoice);
        return v ? v.name : this.selectedVoice;
    }

    getGenderIcon(gender: string): string {
        switch (gender) {
            case 'male': return 'fa-solid fa-mars';
            case 'female': return 'fa-solid fa-venus';
            default: return 'fa-solid fa-genderless';
        }
    }

    get formalityLabel(): string {
        if (this.formality < 0.25) return 'Very Casual';
        if (this.formality < 0.5) return 'Casual';
        if (this.formality < 0.75) return 'Professional';
        return 'Formal';
    }

    get creativityLabel(): string {
        if (this.creativity < 0.25) return 'Precise';
        if (this.creativity < 0.5) return 'Balanced';
        if (this.creativity < 0.75) return 'Creative';
        return 'Very Creative';
    }

    get speedLabel(): string {
        if (this.voiceSpeed < 0.75) return 'Slow';
        if (this.voiceSpeed < 1.25) return 'Normal';
        if (this.voiceSpeed < 2.0) return 'Fast';
        return 'Very Fast';
    }

    toneName(tone: string): string {
        return tone.charAt(0).toUpperCase() + tone.slice(1);
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

    statusTone(value: string | undefined | null): string {
        if (!value) return 'pending';
        const normalized = value.toLowerCase();
        if (['ready', 'ok', 'configured', 'runtime_backend_managed', 'ported_active', 'platform_contract_active', 'removed_from_cde_runtime'].includes(normalized)) return 'ok';
        if (['disabled', 'not_configured', 'missing', 'legacy_settings_surface_active', 'in_progress'].includes(normalized)) return 'warn';
        return normalized.includes('error') || normalized.includes('failed') ? 'error' : 'warn';
    }

    private refreshVoicesForLanguage(): void {
        if (this.isLoadingVoices) return;
        this.isLoadingVoices = true;

        this.store.dispatch(saveBobAssistantSettings({
            personality: this.currentPersonality(),
            voice: this.currentVoice(),
        }));
        setTimeout(() => this.isLoadingVoices = false, 500);
    }

    private applyPersonality(personality: BobConversationPersonality): void {
        this.tone = personality.tone;
        this.formality = personality.formality;
        this.responseLength = personality.response_length;
        this.language = personality.language;
        this.creativity = personality.creativity;
        this.emojiUsage = personality.emoji_usage;
    }

    private applyVoice(voice: BobVoiceSettings): void {
        this.selectedVoice = voice.voice;
        this.voiceSpeed = voice.speed;
        this.autoListen = voice.auto_listen;
    }

    private currentPersonality(): BobConversationPersonality {
        return {
            tone: this.tone,
            formality: this.formality,
            response_length: this.responseLength,
            language: this.language,
            creativity: this.creativity,
            emoji_usage: this.emojiUsage,
        };
    }

    private currentVoice(): BobVoiceSettings {
        return {
            voice: this.selectedVoice,
            speed: this.voiceSpeed,
            auto_listen: this.autoListen,
        };
    }

    private applyRuntimeSettings(settings: BobRuntimeSettingsResponse): void {
        this.runtimeProviders = settings.providers;
        this.runtimeAgents = settings.agents;
        this.runtimeSkills = settings.skills;
        this.runtimeTools = settings.tools;
        this.runtimeMcpFamilies = settings.mcp?.families || [];
        this.runtimeMcpCapabilities = settings.mcp?.capabilities || [];
        this.runtimeMemory = settings.memory || {};
        this.runtimeConversionInventory = settings.conversion_inventory || null;
    }

    private flashMessage(message: string): void {
        this.saveMessage = message;
        setTimeout(() => this.saveMessage = '', 3000);
    }
}
