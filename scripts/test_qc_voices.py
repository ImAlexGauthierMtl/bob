#!/usr/bin/env python3
"""
=============================================================================
  10 TENTATIVES QUÉBEC — Trouver le meilleur son québécois
=============================================================================
  Teste 10 combinaisons différentes:
    - Texte en VRAI joual (contractions, sacres légers, expressions QC)
    - Différentes voix (warm vs pro)
    - Différentes vitesses (0.9 à 1.1)
    - Model flash vs instruct-flash

  USAGE:
    python3 scripts/test_qc_voices.py

  OUTPUT: ./clips_qwen_test/
=============================================================================
"""

import json, os, sys, time, base64, wave
from pathlib import Path
import requests

# ─── Config ─────────────────────────────────────────────────────────────────
DASHSCOPE_KEY = "sk-60e8397a0aaf4344a5a6324fe6b59829"
DASHSCOPE_URL = (
    "https://dashscope-intl.aliyuncs.com/api/v1"
    "/services/aigc/multimodal-generation/generation"
)
OUTPUT_DIR = "clips_qwen_test"
SAMPLE_RATE = 24000

# ─── Texte en VRAI joual ───────────────────────────────────────────────────
# Clip "300 CV" — version hyper québécoise

TEXT_JOUAL_1 = (
    "Écoute ben ça. On a posté une job din petites annonces un mardi. "
    "Le mercredi? Trois cents CV dans boîte. Trois cents! "
    "J'connais même pas trois cents personnes moé! "
    "Normalement, c'est genre trois semaines de niaisage. "
    "Tu lis les mêmes affaires: joueur d'équipe, autonome, "
    "maîtrise de Excel. Ben oui, pis moé j'suis astronaute. "
    "Faque j'ai garroché la pile au complet à Bob. "
    "J'y ai dit: trouve-moé les dix meilleurs, pis grouille. "
    "Deux heures après, le gars m'envoie une liste classée "
    "avec des résumés pour chaque candidat. "
    "Y'a même spotté une fille qui utilise jamais de buzz words "
    "mais qui a des projets GitHub complètement capotés. "
    "On l'a engagée. C'est rendu notre meilleure développeuse. "
    "Bob a pas juste trié des CV. Bob a trouvé du talent "
    "que nous autres on aurait manqué. "
    "Trois cents CV. Un après-midi. Zéro mal de tête. Merci Bob."
)

TEXT_JOUAL_2 = (
    "Heille, faut que j'te conte ça. On a mis une job en ligne mardi. "
    "Mercredi matin? Trois cents CV. Trois cents tabarouette! "
    "Moé, j'connais genre quarante personnes pis la moitié c'est ma famille. "
    "D'habitude, trier ça, c'est trois semaines de calvaire. "
    "Tu lis la même patente: dynamique, polyvalent, maîtrise de Word. "
    "Wow, c'est révolutionnaire ça, Word en 2026. "
    "Faque j'ai toute dompé ça à Bob. Toute! "
    "J'y ai dit: checke ça, trouve-moé les dix meilleurs pis fais ça vite. "
    "Deux heures plus tard, Bob m'envoie une liste parfaite. "
    "Classée, avec des notes pour chaque monde. "
    "Y'a même pogné une candidate que personne aurait regardée "
    "parce qu'elle avait pas de buzz words dans son CV "
    "mais ses projets GitHub étaient malades. "
    "On l'a engagée drette là. Meilleure développeuse qu'on a. "
    "Bob a pas juste trié des papiers. Bob a trouvé du talent qu'on aurait scrappé. "
    "Trois cents CV. Un après-midi. Zéro casse-tête. Merci Bob."
)

TEXT_JOUAL_3 = (
    "OK là, écoute ben. Mardi on a posté une offre d'emploi. "
    "Mercredi matin, j'ouvre mon ordi: trois cents CV. "
    "Trois cents ostie de CV! Ça se peut pas! "
    "Ça là, normalement, c'est genre trois semaines assis à lire "
    "du monde qui écrivent toute la même affaire. "
    "Travaillant. Motivé. Connaissance de la suite Office. Aye, lâche-moé. "
    "Faque j'ai dit à Bob: tiens, prends ça, pis débrouille-toé. "
    "Trouve-moé les dix meilleurs. Enwoye, go. "
    "Le bonhomme a fait ça en deux heures. Deux heures! "
    "Y m'a envoyé la liste avec des résumés pis toute. "
    "Y'a même trouvé une fille dont le CV avait l'air de rien "
    "mais elle avait des projets GitHub écoeurants. "
    "On l'a embauchée su'l spot. C'est notre meilleure maintenant. "
    "Bob a pas juste trié des CV. Y'a trouvé du talent "
    "que nous autres on aurait passé drette à côté. "
    "Trois cents CV. Un après-midi. Aucun mal de tête. Merci Bob."
)

TEXT_CASUAL_QC = (
    "Bon, je vais vous raconter celle-là. Mardi, on poste une offre d'emploi. "
    "Mercredi? Trois cents CV. Trois cents! "
    "Moi je connais même pas trois cents personnes. "
    "Normalement ça c'est trois semaines de triage. "
    "Tu lis les mêmes niaiseries: joueur d'équipe, autonome, "
    "maîtrise de la suite Microsoft. Wow, impressionnant. "
    "J'ai donné le paquet au complet à Bob. "
    "J'ai dit: trouve-moi les dix meilleurs, pis vite. "
    "Deux heures plus tard, Bob m'envoie la liste classée. "
    "Avec un résumé pour chaque candidat. "
    "Il a même trouvé une candidate qui mettait jamais de mots-clés, "
    "mais qui avait des projets GitHub complètement fous. "
    "On l'a engagée. C'est rendu notre meilleure développeuse. "
    "Bob a pas juste trié des CV. Bob a trouvé du talent "
    "que nous on aurait manqué. "
    "Trois cents CV. Un après-midi. Zéro problème. Merci Bob."
)

# ─── 10 Tentatives ─────────────────────────────────────────────────────────
# Différentes combinaisons voix × texte × vitesse × modèle

TESTS = [
    # Heavy joual + warm male voices
    {"file": "test01_ethan_joual_fast.wav",    "voice": "Ethan",  "model": "qwen3-tts-flash", "speed": 1.1, "text": TEXT_JOUAL_1, "desc": "Ethan + joual léger + rapide"},
    {"file": "test02_aiden_joual_heavy.wav",    "voice": "Aiden",  "model": "qwen3-tts-flash", "speed": 1.0, "text": TEXT_JOUAL_2, "desc": "Aiden + joual heavy + normal"},
    {"file": "test03_moon_joual_raw.wav",       "voice": "Moon",   "model": "qwen3-tts-flash", "speed": 0.95, "text": TEXT_JOUAL_3, "desc": "Moon + joual cru + lent"},
    {"file": "test04_mochi_joual_punchy.wav",   "voice": "Mochi",  "model": "qwen3-tts-flash", "speed": 1.1, "text": TEXT_JOUAL_2, "desc": "Mochi + joual heavy + punchy"},
    {"file": "test05_kai_joual_chill.wav",      "voice": "Kai",    "model": "qwen3-tts-flash", "speed": 0.9, "text": TEXT_JOUAL_1, "desc": "Kai + joual léger + chill"},

    # Warm female voices
    {"file": "test06_cherry_joual.wav",         "voice": "Cherry", "model": "qwen3-tts-flash", "speed": 1.05, "text": TEXT_JOUAL_2, "desc": "Cherry + joual heavy"},
    {"file": "test07_vivian_joual.wav",         "voice": "Vivian", "model": "qwen3-tts-flash", "speed": 1.0, "text": TEXT_JOUAL_3, "desc": "Vivian + joual cru"},
    {"file": "test08_momo_joual.wav",           "voice": "Momo",   "model": "qwen3-tts-flash", "speed": 1.1, "text": TEXT_JOUAL_1, "desc": "Momo + joual léger + rapide"},

    # Casual QC (less slang, more natural)
    {"file": "test09_ethan_casual.wav",         "voice": "Ethan",  "model": "qwen3-tts-flash", "speed": 1.0, "text": TEXT_CASUAL_QC, "desc": "Ethan + casual QC"},
    {"file": "test10_aiden_casual_fast.wav",    "voice": "Aiden",  "model": "qwen3-tts-flash", "speed": 1.1, "text": TEXT_CASUAL_QC, "desc": "Aiden + casual QC + rapide"},
]


def synthesize_tts(text, voice, model, speed, output_path):
    """Call DashScope REST+SSE API."""
    headers = {
        "Authorization": f"Bearer {DASHSCOPE_KEY}",
        "Content-Type": "application/json",
        "X-DashScope-SSE": "enable",
    }
    payload = {
        "model": model,
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
                if raw[:4] == b"RIFF" and len(raw) >= 44:
                    actual_sr = int.from_bytes(raw[24:28], "little")
                    pcm = raw[44:]
                else:
                    pcm = raw
                if pcm:
                    pcm_chunks.append(pcm)

    if not pcm_chunks:
        raise RuntimeError("No audio data received")

    all_pcm = b"".join(pcm_chunks)
    with wave.open(str(output_path), 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(actual_sr)
        wf.writeframes(all_pcm)

    return len(all_pcm), actual_sr


def main():
    out = Path(__file__).parent.parent / OUTPUT_DIR
    out.mkdir(exist_ok=True)

    print("=" * 70)
    print("  🇨🇦 10 TENTATIVES QUÉBEC — Qwen3-TTS")
    print(f"  Objectif: trouver le meilleur son québécois")
    print(f"  Voix testées: Ethan, Aiden, Moon, Mochi, Kai, Cherry, Vivian, Momo")
    print(f"  Texte: joual authentique (contractions, sacres, expressions QC)")
    print(f"  Output: {out}/")
    print("=" * 70)

    success = 0
    for i, test in enumerate(TESTS, 1):
        print(f"\n  {'─'*60}")
        print(f"  🎬 {i}/10: {test['desc']}")
        print(f"  🎙️  {test['voice']} | {test['model']} | speed={test['speed']}")
        print(f"  {'─'*60}")

        try:
            t0 = time.time()
            pcm_bytes, sr = synthesize_tts(
                test["text"], test["voice"], test["model"],
                test["speed"], out / test["file"]
            )
            elapsed = time.time() - t0
            dur = pcm_bytes / (sr * 2)
            m, s = int(dur // 60), int(dur % 60)
            size_mb = (out / test["file"]).stat().st_size / (1024 * 1024)
            print(f"  ✅ {test['file']} — {m}m{s:02d}s | {size_mb:.1f}MB | {elapsed:.0f}s gen")
            success += 1
        except Exception as e:
            print(f"  ❌ Error: {e}")

        time.sleep(0.5)

    print(f"\n{'='*70}")
    print(f"  🇨🇦 {success}/10 tentatives générées!")
    print(f"  📁 {out}/")
    print(f"  🎧 Écoute-les et dis-moi lequel sonne le plus québécois!")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
