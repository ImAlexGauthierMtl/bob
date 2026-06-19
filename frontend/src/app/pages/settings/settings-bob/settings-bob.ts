import { Component, OnDestroy, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { Store } from '@ngrx/store';
import { Subscription } from 'rxjs';
import {
    BobConversationPersonality,
    BobLanguageOption,
    BobVoiceOption,
    BobVoiceSettings,
} from '../../../shared/services/bob-assistant-settings.service';
import {
    loadBobAssistantSettings,
    saveBobAssistantSettings,
} from '../../../store/bob-assistant-settings/bob-assistant-settings.actions';
import {
    selectBobAssistantSettingsError,
    selectBobAssistantSettingsNotice,
    selectBobAssistantSettingsOptions,
    selectBobAssistantSettingsPersonality,
    selectBobAssistantSettingsSaving,
    selectBobAssistantSettingsVoice,
} from '../../../store/bob-assistant-settings/bob-assistant-settings.selectors';

@Component({
    selector: 'croo-settings-bob',
    standalone: true,
    imports: [RouterLink, FormsModule],
    templateUrl: './settings-bob.html',
    styleUrls: ['../settings-shared.css', './settings-bob.css'],
})
export class SettingsBobComponent implements OnInit, OnDestroy {
    private store = inject(Store);
    private subscriptions = new Subscription();
    private savingSignal = this.store.selectSignal(selectBobAssistantSettingsSaving);

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

    // UI state
    saveMessage = '';

    get isSaving(): boolean {
        return this.savingSignal();
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
            this.store.select(selectBobAssistantSettingsNotice).subscribe((notice) => {
                if (notice) this.flashMessage(notice);
            }),
        );
        this.subscriptions.add(
            this.store.select(selectBobAssistantSettingsError).subscribe((error) => {
                if (error) this.flashMessage(error);
            }),
        );
        this.store.dispatch(loadBobAssistantSettings());
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

    private flashMessage(message: string): void {
        this.saveMessage = message;
        setTimeout(() => this.saveMessage = '', 3000);
    }
}
