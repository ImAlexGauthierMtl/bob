import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { AuthService } from '../../../shared/services/auth.service';
import { environment } from '../../../../environments/environment';

interface VoiceOption {
    id: string;
    name: string;
    gender: string;
    accent: string;
    style: string;
}

interface LanguageOption {
    code: string;
    name: string;
}

interface BobSettings {
    personality: {
        tone: string;
        formality: number;
        response_length: string;
        language: string;
        creativity: number;
        emoji_usage: boolean;
    };
    voice: {
        voice: string;
        speed: number;
        auto_listen: boolean;
    };
    available_voices: VoiceOption[];
    available_tones: string[];
    available_languages: LanguageOption[];
}

@Component({
    selector: 'croo-settings-bob',
    standalone: true,
    imports: [RouterLink, FormsModule],
    templateUrl: './settings-bob.html',
    styleUrls: ['../settings-shared.css', './settings-bob.css'],
})
export class SettingsBobComponent implements OnInit {
    private http = inject(HttpClient);
    private auth = inject(AuthService);

    // Personality
    tone = 'professional';
    formality = 0.5;
    responseLength = 'balanced';
    language = 'auto';
    creativity = 0.3;
    emojiUsage = false;

    // Voice
    selectedVoice = 'Fritz-PlayAI';
    voiceSpeed = 1.0;
    autoListen = true;

    // Options
    availableVoices: VoiceOption[] = [];
    availableTones: string[] = [];
    availableLanguages: LanguageOption[] = [];

    // UI state
    isSaving = false;
    saveMessage = '';

    private apiUrl = `${environment.apiUrl}/bob/settings`;

    ngOnInit(): void {
        this.loadSettings();
    }

    loadSettings(): void {
        this.http.get<BobSettings>(this.apiUrl, {
            headers: { Authorization: `Bearer ${this.auth.getToken()}` },
        }).subscribe({
            next: (data) => {
                this.tone = data.personality.tone;
                this.formality = data.personality.formality;
                this.responseLength = data.personality.response_length;
                this.language = data.personality.language;
                this.creativity = data.personality.creativity;
                this.emojiUsage = data.personality.emoji_usage;

                this.selectedVoice = data.voice.voice;
                this.voiceSpeed = data.voice.speed;
                this.autoListen = data.voice.auto_listen;

                this.availableVoices = data.available_voices;
                this.availableTones = data.available_tones;
                this.availableLanguages = data.available_languages;
            },
            error: () => {
                // Use defaults on error
            },
        });
    }

    saveSettings(): void {
        this.isSaving = true;
        this.saveMessage = '';

        const payload = {
            personality: {
                tone: this.tone,
                formality: this.formality,
                response_length: this.responseLength,
                language: this.language,
                creativity: this.creativity,
                emoji_usage: this.emojiUsage,
            },
            voice: {
                voice: this.selectedVoice,
                speed: this.voiceSpeed,
                auto_listen: this.autoListen,
            },
        };

        this.http.put<BobSettings>(this.apiUrl, payload, {
            headers: { Authorization: `Bearer ${this.auth.getToken()}` },
        }).subscribe({
            next: () => {
                this.isSaving = false;
                this.saveMessage = 'Settings saved';
                setTimeout(() => this.saveMessage = '', 3000);
            },
            error: () => {
                this.isSaving = false;
                this.saveMessage = 'Error saving settings';
                setTimeout(() => this.saveMessage = '', 3000);
            },
        });
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
}
