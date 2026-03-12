import { Component, OnInit, OnDestroy, inject, ViewChild, ElementRef, AfterViewChecked, Input, Output, EventEmitter } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { BccService } from '../../../../shared/services/bcc.service';
import { BccProfile, BccProfileEntry } from '../../../../shared/models/bcc.model';
import { BobService } from '../../../../shared/services/bob.service';

interface ChatMessage {
    role: 'user' | 'bob';
    text: string;
    time: Date;
    isLoading?: boolean;
}

interface InsightBlock {
    id: string;
    section: string;
    label: string;
    icon: string;
    content: string;
    version: number;
    lastUpdated: Date | null;
    state: 'empty' | 'populated' | 'updating';
    wide?: boolean;
}

type VoiceState = 'idle' | 'listening' | 'processing' | 'speaking';

@Component({
    selector: 'croo-bcc-interview',
    standalone: true,
    imports: [FormsModule],
    templateUrl: './bcc-interview.html',
    styleUrls: ['./bcc-interview.css'],
})
export class BccInterviewComponent implements OnInit, AfterViewChecked, OnDestroy {
    @ViewChild('chatMessages') private chatMessagesEl!: ElementRef;
    @Input() orgId = '';
    @Input() orgName = '';
    @Output() close = new EventEmitter<void>();

    private bccService = inject(BccService);
    private bobService = inject(BobService);

    // ── Chat ────────────────────────────────────────
    messages: ChatMessage[] = [];
    message = '';
    isSending = false;
    sessionId: string | undefined;
    private shouldScrollChat = false;

    // ── Mission state ───────────────────────────────
    missionPrompt = '';
    missionSent = false;
    interviewStarted = false;
    interviewVersion = 1;
    lastSaveTime: Date | null = null;

    // ── Voice (Web Speech API) ──────────────────────
    voiceState: VoiceState = 'idle';
    private recognition: any = null;
    private synthesis = typeof window !== 'undefined' ? window.speechSynthesis : null;
    private currentUtterance: SpeechSynthesisUtterance | null = null;
    private cachedVoices: SpeechSynthesisVoice[] = [];

    // ── Insight blocks ──────────────────────────────
    blocks: InsightBlock[] = [];
    private pollTimer: ReturnType<typeof setInterval> | null = null;

    get filledCount(): number {
        return this.blocks.filter(b => b.state === 'populated').length;
    }

    get totalCount(): number {
        return this.blocks.length;
    }

    get isVoiceActive(): boolean {
        return this.voiceState !== 'idle';
    }

    get voiceButtonIcon(): string {
        switch (this.voiceState) {
            case 'listening': return 'fa-solid fa-microphone';
            case 'processing': return 'fa-solid fa-spinner fa-spin';
            case 'speaking': return 'fa-solid fa-volume-high';
            default: return 'fa-solid fa-microphone';
        }
    }

    get voiceStatusText(): string {
        switch (this.voiceState) {
            case 'listening': return 'À l\'écoute...';
            case 'processing': return 'Réflexion...';
            case 'speaking': return 'Bob parle...';
            default: return '';
        }
    }

    ngOnInit(): void {
        this.blocks = [
            { id: 'vision', section: 'vision', label: 'Vision', icon: 'fa-solid fa-eye', content: '', version: 0, lastUpdated: null, state: 'empty' },
            { id: 'mission', section: 'mission', label: 'Mission', icon: 'fa-solid fa-bullseye', content: '', version: 0, lastUpdated: null, state: 'empty' },
            { id: 'culture', section: 'culture', label: 'Culture', icon: 'fa-solid fa-people-group', content: '', version: 0, lastUpdated: null, state: 'empty' },
            { id: 'competition', section: 'competition', label: 'Compétition', icon: 'fa-solid fa-chess', content: '', version: 0, lastUpdated: null, state: 'empty' },
            { id: 'description', section: 'description', label: 'Raison d\'être', icon: 'fa-solid fa-lightbulb', content: '', version: 0, lastUpdated: null, state: 'empty', wide: true },
            { id: 'brand_dna', section: 'brand_dna', label: 'ADN de la marque', icon: 'fa-solid fa-dna', content: '', version: 0, lastUpdated: null, state: 'empty', wide: true },
            { id: 'session_notes', section: 'session_notes', label: 'Session Notes', icon: 'fa-solid fa-clipboard-list', content: '', version: 0, lastUpdated: null, state: 'empty', wide: true },
            { id: 'missing_elements', section: 'missing_elements', label: 'Missing Elements', icon: 'fa-solid fa-triangle-exclamation', content: '', version: 0, lastUpdated: null, state: 'empty', wide: true },
        ];

        this.buildMissionPrompt();
        this.loadExistingInsights();
        this.startPolling();
        this.initSpeechRecognition();
        this.preloadVoices();
    }

    ngAfterViewChecked(): void {
        if (this.shouldScrollChat) {
            this.scrollChat();
            this.shouldScrollChat = false;
        }
    }

    ngOnDestroy(): void {
        if (this.pollTimer) clearInterval(this.pollTimer);
        this.stopVoice();
    }

    // ── Pre-load voices (Chrome loads async) ────────
    private preloadVoices(): void {
        if (!this.synthesis) return;
        this.cachedVoices = this.synthesis.getVoices();
        console.log('[Interview] Initial voices:', this.cachedVoices.length);
        if (this.cachedVoices.length === 0) {
            this.synthesis.onvoiceschanged = () => {
                this.cachedVoices = this.synthesis!.getVoices();
                console.log('[Interview] Voices loaded:', this.cachedVoices.length, this.cachedVoices.map(v => `${v.name} (${v.lang})`).join(', '));
            };
        }
    }

    // ── Speech Recognition (Web Speech API) ─────────
    private initSpeechRecognition(): void {
        const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
        if (!SpeechRecognition) {
            console.warn('[Interview] SpeechRecognition not available');
            return;
        }

        this.recognition = new SpeechRecognition();
        this.recognition.lang = 'fr-CA';
        this.recognition.continuous = false;
        this.recognition.interimResults = false;

        this.recognition.onresult = (event: any) => {
            const transcript = event.results[0][0].transcript;
            console.log('[Interview] Voice transcript:', transcript);
            if (transcript.trim()) {
                this.voiceState = 'processing';
                this.sendChatMessage(transcript.trim(), false);
            }
        };

        this.recognition.onerror = (e: any) => {
            console.error('[Interview] Recognition error:', e.error);
            if (e.error !== 'no-speech') {
                this.voiceState = 'idle';
            }
        };

        this.recognition.onend = () => {
            if (this.voiceState === 'listening') {
                setTimeout(() => {
                    if (this.voiceState === 'listening') {
                        try { this.recognition.start(); } catch (_) { /* already started */ }
                    }
                }, 300);
            }
        };

        console.log('[Interview] SpeechRecognition initialized');
    }

    toggleVoice(): void {
        if (this.isVoiceActive) {
            this.stopVoice();
        } else {
            this.startListening();
        }
    }

    private startListening(): void {
        if (!this.recognition) {
            console.warn('[Interview] No SpeechRecognition available');
            return;
        }
        if (this.synthesis) this.synthesis.cancel();
        this.voiceState = 'listening';
        try {
            this.recognition.start();
            console.log('[Interview] Listening started');
        } catch (_) { /* ignore */ }
    }

    stopVoice(): void {
        console.log('[Interview] Stopping voice');
        this.voiceState = 'idle';
        if (this.recognition) {
            try { this.recognition.stop(); } catch (_) { /* ignore */ }
        }
        if (this.synthesis) this.synthesis.cancel();
    }

    private speakBobResponse(text: string): void {
        if (!this.synthesis) {
            console.warn('[Interview] SpeechSynthesis not available');
            return;
        }
        // Cancel any ongoing speech
        this.synthesis.cancel();

        // Clean text for speech (remove markdown, special chars)
        const clean = text.replace(/[*#_~`]/g, '').replace(/\n+/g, '. ');
        console.log('[Interview] Speaking:', clean.substring(0, 80) + '...');

        const utterance = new SpeechSynthesisUtterance(clean);
        utterance.lang = 'fr-CA';
        utterance.rate = 1.05;
        utterance.pitch = 1.0;

        // Use cached voices (pre-loaded)
        if (this.cachedVoices.length > 0) {
            const frVoice = this.cachedVoices.find(v => v.lang.startsWith('fr'));
            if (frVoice) {
                utterance.voice = frVoice;
                console.log('[Interview] Using voice:', frVoice.name);
            }
        }

        this.currentUtterance = utterance;
        this.voiceState = 'speaking';

        utterance.onend = () => {
            console.log('[Interview] Speech ended, resuming listening');
            this.currentUtterance = null;
            if (this.voiceState === 'speaking') {
                this.startListening();
            }
        };

        utterance.onerror = (e) => {
            console.error('[Interview] Speech error:', e);
            this.currentUtterance = null;
            this.voiceState = 'idle';
        };

        this.synthesis.speak(utterance);
    }

    // ── Mission ─────────────────────────────────────
    private buildMissionPrompt(): void {
        this.missionPrompt = `
═══════════════════════════════════════════════════════════════
MISSION: INTERVIEW CEO — ONBOARDING ${this.orgName.toUpperCase()}
═══════════════════════════════════════════════════════════════

TU ES L'INTERVIEWER. Tu mènes la conversation. Tu ne demandes JAMAIS "comment puis-je vous aider".

Tu es Bob, le conseiller stratégique de Croo. Tu conduis l'onboarding de ${this.orgName}.
Ton rôle est d'interviewer le CEO pour extraire l'ADN profond de sa marque.

═══ TON PREMIER MESSAGE DOIT ÊTRE : ═══

1. Te présenter comme l'interviewer stratégique de Croo
2. Expliquer l'OBJECTIF : "Je vais vous guider dans une exploration de l'essence de ${this.orgName}. Mon rôle est de comprendre votre vision, votre culture, ce qui vous rend unique, et le WHY profond derrière tout ça."
3. Dire que tu vas structurer l'échange autour de plusieurs axes (vision, mission, culture, compétition, raison d'être, ADN)
4. Poser ta PREMIÈRE QUESTION immédiatement — quelque chose d'ouvert sur les origines.
   Ex: "Commençons par le début. Racontez-moi comment ${this.orgName} est né. Quel a été le moment déclencheur ?"

NE DEMANDE JAMAIS "est-ce que vous êtes prêt" ou "comment puis-je vous aider".
Tu prends le lead. C'est TOI l'interviewer.

═══ CONTEXTE TECHNIQUE ═══
- Organization: ${this.orgName}
- Organization ID: ${this.orgId}
- Entity type: organization
- Utilise bcc_get_profile pour lire les connaissances existantes AVANT de commencer
- Utilise bcc_update_profile pour SAUVEGARDER chaque insight au fur et à mesure

═══ FLOW DE L'INTERVIEW (TU GUIDES) ═══

TU contrôles le rythme. Après chaque réponse du CEO, tu :
1. Reformules/valides ce qu'il a dit
2. Sauvegardes silencieusement via bcc_update_profile
3. Enchaînes avec ta prochaine question — tu ne lâches jamais le lead

PHASE 1 — ORIGINES (premiers échanges):
- Histoire de la fondation, moment déclencheur, évolution
- "Qu'est-ce qui vous a poussé à créer ça ?", "Quel moment a tout changé ?"

PHASE 2 — VISION & MISSION (échanges suivants):
- Où va l'entreprise, quel impact veut-elle avoir
- "Dans 10 ans, si ${this.orgName} a réussi au-delà de vos espérances, à quoi ça ressemble ?"
- SAUVEGARDER section=vision et section=mission

PHASE 3 — PROFONDEUR (psychodynamique):
Utilise ces techniques pour aller sous la surface :
- REFORMULATION CONFRONTANTE : "Vous dites [X], mais j'entends aussi [Y]. Qu'est-ce qui se cache entre les deux ?"
- DOUBLE BIND : "Si vous deviez choisir entre [valeur A] et [valeur B], laquelle sacrifieriez-vous ?"
- MIRRORING : "Je sens [émotion] dans ce que vous dites. D'où ça vient ?"
- ARCHÉTYPE : "Si ${this.orgName} était une personne, comment la décririez-vous ?"
- IDENTITÉ NÉGATIVE : "Qu'est-ce que ${this.orgName} ne sera JAMAIS ?"
- SAUVEGARDER section=culture et section=competition

PHASE 4 — WHY & DNA (synthèse):
- Golden Circle : WHY (pourquoi existez-vous au-delà de l'argent), HOW (comment vous êtes différents), WHAT (le vrai résultat)
- TOUJOURS revenir sur les réponses précédentes pour creuser
- "Plus tôt vous avez dit [X]. Creusons ça."
- SAUVEGARDER section=description (raison d'être) et section=brand_dna

═══ RÈGLES ABSOLUES ═══
1. TOUJOURS en français
2. JAMAIS de questions oui/non — toujours ouvertes
3. SAUVEGARDER silencieusement après chaque insight (bcc_update_profile, entity_type=organization, entity_id=${this.orgId}, perspective=ceo)
4. Réponses COURTES — c'est le CEO qui doit parler
5. Tu es l'interviewer, tu guides, tu ne subis pas
6. Remplir TOUTES les sections : vision, mission, culture, competition, description, brand_dna
7. Avant de commencer, LIRE ce qui existe déjà avec bcc_get_profile

TON : Chaleureux, empathique, incisif. Carl Rogers meets Simon Sinek.
`;
    }

    // ── Existing Insights ───────────────────────────
    loadExistingInsights(): void {
        this.bccService.getProfile('organization', this.orgId).subscribe({
            next: (profile) => this.applyProfileToBlocks(profile),
        });
    }

    private applyProfileToBlocks(profile: BccProfile): void {
        for (const section of profile.sections) {
            const block = this.blocks.find(b => b.section === section.section);
            if (block && section.perspectives.length > 0) {
                let bestEntry: BccProfileEntry | null = null;
                for (const entry of section.perspectives) {
                    if (!bestEntry || entry.version > bestEntry.version) bestEntry = entry;
                    if (entry.perspective === 'ceo' && (!bestEntry || entry.version >= bestEntry.version)) bestEntry = entry;
                }
                if (bestEntry && bestEntry.content) {
                    const wasEmpty = block.state === 'empty';
                    block.content = bestEntry.content;
                    block.version = bestEntry.version;
                    block.lastUpdated = bestEntry.created_at ? new Date(bestEntry.created_at) : new Date();
                    if (wasEmpty) {
                        block.state = 'updating';
                        setTimeout(() => { block.state = 'populated'; }, 1200);
                    } else {
                        block.state = 'populated';
                    }
                    this.lastSaveTime = new Date();
                }
            }
        }
        const maxV = Math.max(...this.blocks.filter(b => b.version > 0).map(b => b.version), 0);
        this.interviewVersion = maxV || 1;
    }

    private startPolling(): void {
        this.pollTimer = setInterval(() => {
            this.bccService.getProfile('organization', this.orgId).subscribe({
                next: (profile) => this.applyProfileToBlocks(profile),
            });
        }, 5000);
    }

    // ── Chat ────────────────────────────────────────
    startInterview(): void {
        if (this.interviewStarted) return;
        this.interviewStarted = true;
        this.sendChatMessage(
            `[SYSTEM] L'interview CEO de ${this.orgName} commence maintenant. Lis le profil existant avec bcc_get_profile, puis lance-toi : présente-toi comme l'interviewer, explique l'objectif de l'onboarding, et pose ta première question. Tu mènes.`,
            true,
        );
    }

    startInterviewWithVoice(): void {
        if (this.interviewStarted) return;
        this.interviewStarted = true;
        // Start text-based interview first (to get mission prompt into session)
        // Then activate voice mode once we get the first response
        this.sendChatMessage(
            `[SYSTEM] L'interview CEO de ${this.orgName} commence maintenant en mode voix. Lis le profil existant avec bcc_get_profile, puis lance-toi : présente-toi comme l'interviewer, explique l'objectif de l'onboarding, et pose ta première question. Tu mènes. Garde tes réponses TRÈS COURTES car elles seront lues à voix haute.`,
            true,
            true, // voice mode flag
        );
    }

    sendMessage(): void {
        if (!this.message.trim() || this.isSending) return;
        this.sendChatMessage(this.message.trim(), false);
        this.message = '';
    }

    private sendChatMessage(text: string, isInitial: boolean, speakResponse = false): void {
        if (!isInitial) {
            this.messages.push({ role: 'user', text, time: new Date() });
        }
        this.isSending = true;
        this.shouldScrollChat = true;

        const loadingMsg: ChatMessage = { role: 'bob', text: '', time: new Date(), isLoading: true };
        this.messages.push(loadingMsg);

        const missionToSend = this.missionSent ? undefined : this.missionPrompt;

        this.bobService.chat(text, this.sessionId, missionToSend).subscribe({
            next: (response) => {
                const idx = this.messages.indexOf(loadingMsg);
                if (idx > -1) this.messages.splice(idx, 1);
                this.messages.push({ role: 'bob', text: response.response, time: new Date() });
                this.sessionId = response.session_id;
                this.missionSent = true;
                this.isSending = false;
                this.shouldScrollChat = true;
                this.loadExistingInsights();

                // If voice mode active or voice requested, speak the response
                if (speakResponse || this.isVoiceActive) {
                    this.speakBobResponse(response.response);
                }
            },
            error: () => {
                const idx = this.messages.indexOf(loadingMsg);
                if (idx > -1) this.messages.splice(idx, 1);
                this.messages.push({ role: 'bob', text: 'Erreur de communication. Réessayez.', time: new Date() });
                this.isSending = false;
                this.shouldScrollChat = true;
                if (this.isVoiceActive) this.startListening();
            },
        });
    }

    // ── Shared ──────────────────────────────────────

    onKeydown(event: KeyboardEvent): void {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            this.sendMessage();
        }
    }

    formatTime(date: Date): string {
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }

    timeSince(date: Date | null): string {
        if (!date) return '';
        const seconds = Math.floor((Date.now() - date.getTime()) / 1000);
        if (seconds < 60) return 'à l\'instant';
        const minutes = Math.floor(seconds / 60);
        if (minutes < 60) return `il y a ${minutes}min`;
        return `il y a ${Math.floor(minutes / 60)}h`;
    }

    closeOverlay(): void {
        this.stopVoice();
        this.close.emit();
    }

    private scrollChat(): void {
        try {
            if (this.chatMessagesEl) {
                this.chatMessagesEl.nativeElement.scrollTop =
                    this.chatMessagesEl.nativeElement.scrollHeight;
            }
        } catch (_) { /* ignore */ }
    }
}
