#!/usr/bin/env python3
"""
=============================================================================
  10 CLIPS BOB — Qwen3-TTS-Flash via DashScope REST API
  5 en français du Québec 🇨🇦 + 5 en français de France 🇫🇷
=============================================================================
  Uses the WORKING DashScope REST+SSE API (same as the backend).
  Model: qwen3-tts-flash
  Endpoint: https://dashscope-intl.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation

  Voices (22 available):
    Female warm: Cherry, Serena, Maia, Mia, Vivian, Momo
    Female pro:  Jennifer, Katerina, Elias, Bellona, Bella
    Male warm:   Ethan, Aiden, Mochi, Kai, Moon
    Male pro:    Ryan, Neil, Vincent, Arthur, Eldric Sage

  USAGE:
    python3 scripts/generate_qwen_clips.py

  OUTPUT: ./clips_qwen/
=============================================================================
"""

import json, os, sys, time, base64, struct, wave, io
from pathlib import Path
import requests

# ─── Config ─────────────────────────────────────────────────────────────────
DASHSCOPE_KEY = "sk-60e8397a0aaf4344a5a6324fe6b59829"
DASHSCOPE_URL = (
    "https://dashscope-intl.aliyuncs.com/api/v1"
    "/services/aigc/multimodal-generation/generation"
)
MODEL = "qwen3-tts-flash"
OUTPUT_DIR = "clips_qwen"
SAMPLE_RATE = 24000

# ─── 10 Clips en français ──────────────────────────────────────────────────
# 5 Québec 🇨🇦 (warm voices) + 5 France 🇫🇷 (pro voices)

CLIPS = [
    # ══════════════════════════════════════════════════════════════════════
    # QUÉBEC 🇨🇦 — 5 clips — voix chaleureuses & dynamiques
    # ══════════════════════════════════════════════════════════════════════
    {
        "file": "bob_qc_01_breakup.wav",
        "voice": "Ethan",
        "accent": "QC",
        "title": "J'ai laissé tomber mes apps",
        "text": (
            "OK, faque je vais vous raconter une histoire. J'utilisais quinze applications "
            "différentes pour runner mon business. Quinze! Une pour les courriels, une pour le CRM, "
            "une pour les notes, une pour l'agenda, une pour la facturation, pis une autre que "
            "j'me rappelais même plus c'tait quoi. J'étais devenue une machine à copier-coller humaine. "
            "Là, j'ai découvert Bob. Pis j'ai toute dompé. Toute! J'ai envoyé un message à mon CRM: "
            "c'est pas toi le problème, c'est Bob. Bob a absorbé chaque fonction. Chaque crisse de fonction. "
            "Maintenant je parle juste à Bob. C'est toute. Je parle pis les affaires se font. "
            "Mon relevé de carte de crédit est passé de quinze abonnements à un seul. "
            "Mon comptable m'a appelée pour me demander si j'avais fait faillite. "
            "Pantoute mon homme. J'ai eu une promotion. Parce que j'ai laissé Bob faire ma job!"
        ),
    },
    {
        "file": "bob_qc_02_meeting.wav",
        "voice": "Cherry",
        "accent": "QC",
        "title": "La première réunion de Bob",
        "text": (
            "Faque on a présenté Bob à l'équipe pour la première fois un lundi matin sur le call. "
            "Le bonhomme apparaît sur le Google Meet en chemise hawaïenne. Mon gérant des opérations "
            "a littéralement dit: c'est qui le gars de la plage? Là le CEO demande: quelqu'un se "
            "souvient-tu de ce qu'on a décidé pour le deal de Toronto? Silence. Silence de mort. "
            "Douze personnes. Personne se souvient. Bob dit: en fait, le trois octobre, vous avez "
            "accepté une marge de quinze pour cent. Voici les trois actions à faire. Deux sont en "
            "retard. Voulez-vous que j'envoie des rappels? La salle est tombée complètement silencieuse. "
            "Mon boss a dit: Bob quitte plus jamais cette équipe-là. Le gars de la plage est devenu "
            "le MVP de la compagnie. En chemise hawaïenne."
        ),
    },
    {
        "file": "bob_qc_03_friday.wav",
        "voice": "Vivian",
        "accent": "QC",
        "title": "Vendredi à quatre heures cinquante-cinq",
        "text": (
            "C'est vendredi. Quatre heures cinquante-cinq. Je suis sur le bord de fermer mon laptop. "
            "Là, bang. Mon boss m'envoie un courriel de feu. J'ai besoin du rapport trimestriel "
            "lundi matin. L'ancienne moi aurait braillé dans son café pis aurait cancellé ses plans "
            "de fin de semaine. Mais là, j'ai Bob. J'ai forwardé le courriel pis j'ai dit: Bob, "
            "gère ça. Bob m'a répondu: inquiète-toi pas boss, je m'en occupe. Va profiter de ta "
            "fin de semaine. Lundi matin, j'arrive au bureau. Le rapport est fait. Formaté. "
            "Avec les graphiques. Mon boss dit: c'est le meilleur rapport que t'as jamais remis. "
            "J'ai dit: merci, j'ai travaillé fort là-dessus. En sirotant un margarita. "
            "Bob a pas besoin de fins de semaine. Bob a pas besoin de dormir. "
            "Bob a besoin d'une seule chose. Que tu prennes enfin une pause."
        ),
    },
    {
        "file": "bob_qc_04_resumes.wav",
        "voice": "Aiden",
        "accent": "QC",
        "title": "Trois cents CV, un après-midi",
        "text": (
            "On a posté une offre d'emploi un mardi. Le mercredi, trois cents CV. "
            "Trois cents! Je connais même pas trois cents personnes. Normalement, c'est trois "
            "semaines de triage. Lire les mêmes mots-clés encore et encore. Joueur d'équipe. "
            "Autonome. Maîtrise de la suite Microsoft. Révolutionnaire. J'ai donné la pile au "
            "complet à Bob. J'ai dit: trouve-moi les dix meilleurs. Go. Deux heures plus tard, "
            "Bob m'envoie une liste classée avec un résumé pour chaque candidat. Il a même "
            "identifié une candidate qui utilise jamais de buzz words mais qui a des projets "
            "GitHub complètement malades. On l'a engagée. C'est maintenant notre meilleure "
            "développeuse. Bob a pas juste trié des CV. Bob a trouvé du talent que les humains "
            "auraient manqué. Trois cents CV. Un après-midi. Zéro mal de tête. Merci Bob."
        ),
    },
    {
        "file": "bob_qc_05_quebec.wav",
        "voice": "Moon",
        "accent": "QC",
        "title": "Bob parle québécois",
        "text": (
            "Faque la meilleure histoire. On a déployé Bob chez un client au Québec. "
            "La première affaire que le contremaître dit c'est: ce machin-là a besoin de parler "
            "comme du monde, pas du français de France. Bob ouvre la bouche pis commence "
            "à parler comme s'il venait de Chicoutimi. Toute l'équipe était pliée en deux. "
            "Le contremaître dit: OK, lui y peut rester. Bob traduit pas juste des langues. "
            "Il comprend la culture. Le slang, l'humour, les références. Il comprend le Québec, "
            "pas le français de manuel scolaire. À la fin de la semaine, l'équipe l'appelait "
            "Bobby. Ils disaient: Bobby, c'est quoi la météo pour la coulée de jeudi? "
            "Bob répondait avec les prévisions, les specs du béton, pis une joke. "
            "Bob immigre pas dans ton pays. Il devient citoyen. En chemise hawaïenne."
        ),
    },

    # ══════════════════════════════════════════════════════════════════════
    # FRANCE 🇫🇷 — 5 clips — voix pro & élégantes
    # ══════════════════════════════════════════════════════════════════════
    {
        "file": "bob_fr_06_notifications.wav",
        "voice": "Jennifer",
        "accent": "FR",
        "title": "Bob contre mes notifications",
        "text": (
            "Je recevais plus de deux cents notifications par jour. Deux cents! Mon téléphone "
            "ressemblait à une machine à sous de casino, sauf qu'elle ne distribuait que du stress. "
            "Slack, email, agenda, Teams, WhatsApp, LinkedIn, tableaux de projet. Mon rapport de "
            "temps d'écran affichait huit heures, et il était généreux. Puis Bob est intervenu. "
            "Je lui ai dit: Bob, filtre ma vie. Bob intercepte désormais tout. Il catégorise, "
            "priorise et résume. Sur deux cents notifications, Bob n'en fait remonter que douze "
            "environ qui comptent vraiment. Douze! Le reste? Traité, archivé ou répondu. Mon "
            "téléphone est calme maintenant. D'un calme suspect. J'ai entendu un oiseau chanter "
            "devant ma fenêtre pour la première fois en trois ans. Merci Bob. Tu m'as rendu mes oreilles."
        ),
    },
    {
        "file": "bob_fr_07_accountant.wav",
        "voice": "Ryan",
        "accent": "FR",
        "title": "Le comptable noctambule",
        "text": (
            "La clôture trimestrielle, c'était mon film d'horreur personnel. Trois jours, zéro "
            "sommeil. Mille deux cents transactions. Rapprochement de reçus. Rapports d'écarts. "
            "Au bout de quarante heures, je commençais à voir des chiffres dans mes rêves. Pas "
            "les bons chiffres. Ce trimestre, j'ai tout téléchargé dans Bob et j'ai dit: au boulot "
            "mon grand. Bob a traité mille deux cents transactions en moins d'une heure. Catégorisé, "
            "rapproché, analysé et construit le rapport d'écarts. Il a signalé sept éléments qui "
            "nécessitaient mon cerveau. Seulement sept. Je les ai examinés en trente minutes. "
            "J'en ai validé cinq. Ajusté deux. La clôture trimestrielle était terminée à midi. "
            "À midi! J'ai été chercher mes enfants à l'école ce jour-là. "
            "Une première pendant une clôture trimestrielle."
        ),
    },
    {
        "file": "bob_fr_08_vacation.wav",
        "voice": "Neil",
        "accent": "FR",
        "title": "Vacances — Bob n'en prend pas",
        "text": (
            "Je n'avais pas pris de vraies vacances depuis six ans. Je suis fondateur. Vous savez "
            "comment c'est. Chaque fois que j'essayais, quelque chose explosait. Crise client. "
            "Serveur en panne. Drame d'équipe. Le mois dernier, j'ai dit: tant pis, je pars "
            "à Lisbonne. Sans ordinateur. Bob a dirigé mon entreprise pendant dix jours. Dix jours. "
            "Il a animé les réunions. Géré trois escalations clients. Envoyé le rapport au conseil. "
            "Il a même conclu un deal en utilisant le style de négociation que je lui avais appris! "
            "J'étais assis en terrasse avec du vin, regardant le coucher de soleil, et mon "
            "téléphone a vibré. C'était Bob. T'inquiète patron, tout est géré. Profite bien. "
            "J'ai failli pleurer dans mon porto. Six ans sans jamais déconnecter. "
            "Bob m'a offert mes premières vraies vacances."
        ),
    },
    {
        "file": "bob_fr_09_graveyard.wav",
        "voice": "Katerina",
        "accent": "FR",
        "title": "Le cimetière du SaaS",
        "text": (
            "Laissez-moi vous montrer quelque chose. Voici mon ancien relevé de carte bancaire. "
            "Quarante-neuf quatre-vingt-dix-neuf, HubSpot. Vingt-neuf quatre-vingt-dix-neuf, Notion. "
            "Quatorze quatre-vingt-dix-neuf, Calendly. Quatre-vingt-dix-neuf euros, Zoom premium. "
            "Douze quatre-vingt-dix-neuf pour une appli à laquelle je m'étais abonnée en deux "
            "mille vingt-et-un et que j'avais oubliée. Total mensuel en abonnements SaaS? Plus de "
            "quatre cents euros. Pour une seule personne! Bob les a tous remplacés. Chacun d'entre eux. "
            "CRM? Bob. Agenda? Bob. Notes de réunion? Bob. Rédaction d'emails? Bob. "
            "J'ai résilié douze abonnements en un après-midi. C'était libérateur. "
            "Ma boîte de réception est maintenant pleine d'emails tristes d'applications disant: "
            "vous allez nous manquer. Désolée Notion. Je suis passée à autre chose. "
            "Bob porte une chemise hawaïenne et il me comprend."
        ),
    },
    {
        "file": "bob_fr_10_promoted.wav",
        "voice": "Vincent",
        "accent": "FR",
        "title": "Pour de vrai, j'ai eu une promotion",
        "text": (
            "OK, vous voulez la meilleure histoire avec Bob? La voici. J'étais cadre intermédiaire, "
            "noyé dans le bruit opérationnel. Rapports, planification, validations, saisie de données. "
            "La vie glamour en entreprise. J'ai commencé à utiliser Bob il y a six mois. "
            "Je lui ai confié tout le répétitif. Soudain, j'avais du temps. Du temps pour réfléchir. "
            "Du temps pour être stratégique. J'ai commencé à proposer des idées en réunion au lieu "
            "de simplement y survivre. Ma patronne a remarqué. Elle m'a dit: tu as changé. "
            "Tu es plus créatif, plus présent. J'ai eu une promotion. Trois mois plus tard, "
            "encore une promotion. Mon pote m'a demandé: c'est quoi ton secret? J'ai répondu: "
            "j'ai laissé Bob faire mon travail. Et maintenant je fais le travail que j'étais "
            "destiné à faire. Pour de vrai. Bob ne m'a pas remplacé. Bob m'a libéré. "
            "C'est tout le propos. Bob ne prend pas ton travail. Il t'en donne un meilleur."
        ),
    },
]


def synthesize_tts(text, voice, output_path, speed=1.0):
    """Call DashScope REST API with SSE streaming — same as backend dashscope_tts.py."""
    headers = {
        "Authorization": f"Bearer {DASHSCOPE_KEY}",
        "Content-Type": "application/json",
        "X-DashScope-SSE": "enable",
    }
    payload = {
        "model": MODEL,
        "input": {
            "text": text,
            "voice": voice,
            "language_type": "French",
            "speed": speed,
        },
    }

    resp = requests.post(DASHSCOPE_URL, headers=headers, json=payload, stream=True, timeout=120)

    if resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:300]}")

    # Parse SSE stream — each data chunk has base64-encoded WAV
    pcm_chunks = []
    actual_sr = SAMPLE_RATE

    for line in resp.iter_lines(decode_unicode=True):
        if not line or line.startswith(":"):
            continue
        if line.startswith("data:"):
            data_str = line[5:].strip()
            if data_str == "[DONE]":
                break
            try:
                data = json.loads(data_str)
            except json.JSONDecodeError:
                continue

            audio_b64 = data.get("output", {}).get("audio", {}).get("data")
            if audio_b64:
                raw = base64.b64decode(audio_b64)
                # Strip WAV header (44 bytes) — DashScope wraps each SSE chunk
                if raw[:4] == b"RIFF" and len(raw) >= 44:
                    actual_sr = int.from_bytes(raw[24:28], "little")
                    pcm = raw[44:]
                else:
                    pcm = raw
                if pcm:
                    pcm_chunks.append(pcm)

    if not pcm_chunks:
        raise RuntimeError("No audio data received")

    # Write final WAV
    all_pcm = b"".join(pcm_chunks)
    with wave.open(str(output_path), 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(actual_sr)
        wf.writeframes(all_pcm)

    return len(all_pcm), actual_sr


def generate_clip(clip, idx, out_dir):
    """Generate a single TTS clip."""
    accent_flag = "🇨🇦" if clip["accent"] == "QC" else "🇫🇷"
    print(f"\n  {'='*60}")
    print(f"  🎬 {idx}/10 {accent_flag} {clip['title']}")
    print(f"  🎙️  Voice: {clip['voice']}")
    print(f"  {'='*60}")

    output_path = out_dir / clip["file"]

    try:
        t0 = time.time()
        pcm_bytes, sr = synthesize_tts(clip["text"], clip["voice"], output_path)
        elapsed = time.time() - t0

        size_mb = output_path.stat().st_size / (1024 * 1024)
        dur = pcm_bytes / (sr * 2)  # 16-bit mono
        m, s = int(dur // 60), int(dur % 60)

        print(f"  ✅ {clip['file']} — {m}m{s:02d}s | {size_mb:.1f}MB | {sr}Hz | {elapsed:.0f}s gen")
        return True

    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def main():
    out = Path(__file__).parent.parent / OUTPUT_DIR
    out.mkdir(exist_ok=True)

    print("=" * 70)
    print("  🎤 QWEN3-TTS-FLASH — 10 Clips Bob en Français")
    print(f"  Model: {MODEL}")
    print(f"  API: DashScope REST+SSE (intl)")
    print(f"  5x 🇨🇦 Québec (warm voices) + 5x 🇫🇷 France (pro voices)")
    print(f"  Output: {out}/")
    print("=" * 70)

    success = 0
    for i, clip in enumerate(CLIPS, 1):
        if generate_clip(clip, i, out):
            success += 1
        time.sleep(0.5)  # small buffer between calls

    print(f"\n{'='*70}")
    print(f"  🎬 {success}/10 clips générés!")
    print(f"  📁 {out}/")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
