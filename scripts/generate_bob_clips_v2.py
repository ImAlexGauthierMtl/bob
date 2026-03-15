#!/usr/bin/env python3
"""
=============================================================================
  10 PUNCHY BOB CLIPS — Social Media Edition
  Orpheus TTS via Groq API
=============================================================================
  10 viral-style, humorous, punchy clips about Big Bob.
  Each clip uses a DIFFERENT voice for variety.
  Fast, funny, catchy — ready for TikTok / Reels / YouTube Shorts.

  Voices (all 6, cycling):
    autumn, troy, diana, austin, hannah, daniel

  USAGE:
    python3 scripts/generate_bob_clips_v2.py

  OUTPUT: ./clips_v2/
=============================================================================
"""

import os, sys, io, wave, time
from pathlib import Path

try:
    from groq import Groq
except ImportError:
    print("ERROR: pip3 install groq"); sys.exit(1)

MODEL = "canopylabs/orpheus-v1-english"
OUTPUT_DIR = "clips_v2"
RATE_LIMIT_DELAY = 0.8
PAUSE_MS = 250
PAUSE_BEAT_MS = 500  # comedic beat pauses

# ─── 10 Punchy Clips ───────────────────────────────────────────────────────
# (filename, voice, title, segments)
# Voices cycle: autumn, troy, diana, austin, hannah, daniel, autumn, troy, diana, austin

CLIPS = [
    # ── CLIP 1: "I Broke Up With My Apps" ───────────────────────────────
    ("bob_v2_01_breakup.wav", "autumn", "I Broke Up With My Apps", [
        ("[excited]", "Okay story time. I was using fifteen different apps to run my business."),
        ("[sarcastic]", "Fifteen! One for email, one for CRM, one for notes, one for scheduling,"),
        ("[sarcastic]", "one for invoicing, one for project management, one that I forgot what it even does."),
        ("[excited]", "I was basically a human copy-paste machine."),
        ("[cheerful]", "Then I got Bob. And I literally broke up with all of them."),
        ("[excited]", "I texted my CRM: it's not you, it's Bob."),
        ("[cheerful]", "Bob absorbed every single function. Every. Single. One."),
        ("[confident]", "Now I just talk to Bob. That's it. I talk and stuff gets done."),
        ("[excited]", "My credit card statement went from fifteen subscriptions to one."),
        ("[cheerful]", "My accountant called me and asked if I'd gone out of business."),
        ("[excited]", "No honey. I got promoted. Because I let Bob do my job!"),
    ]),

    # ── CLIP 2: "Bob's First Meeting" ───────────────────────────────────
    ("bob_v2_02_first_meeting.wav", "troy", "Bob's First Meeting", [
        ("[confident]", "So we introduced Bob to the team for the first time on a Monday morning call."),
        ("[cheerful]", "This dude pops up on the Google Meet in a Hawaiian shirt."),
        ("[confident]", "My operations manager literally said, who invited the beach guy?"),
        ("[excited]", "Then the CEO asks, does anyone remember what we decided about the Chicago deal?"),
        ("[confident]", "Silence. Dead silence. Twelve people. Nobody remembers."),
        ("[excited]", "Bob goes, actually, on October third you agreed to a fifteen percent margin."),
        ("[excited]", "Here are the three action items. Two are overdue. Want me to send reminders?"),
        ("[confident]", "The room went completely quiet."),
        ("[excited]", "Then my boss said, Bob is never leaving this team."),
        ("[cheerful]", "The beach guy became the MVP of the company. In a Hawaiian shirt."),
    ]),

    # ── CLIP 3: "Friday at 4:55" ────────────────────────────────────────
    ("bob_v2_03_friday.wav", "diana", "Friday at Four Fifty-Five", [
        ("[excited]", "It's Friday. Four fifty-five PM. I'm about to close my laptop."),
        ("[sarcastic]", "Then boom. My boss drops a fire email. Need the quarterly report by Monday."),
        ("[sarcastic]", "The old me would've cried into my coffee and cancelled my weekend plans."),
        ("[excited]", "But I have Bob now. I forwarded the email and said, Bob, handle it."),
        ("[cheerful]", "Bob said, deadass, boss. I got it. Go enjoy your weekend."),
        ("[confident]", "Monday morning I walk in. Report is done. Formatted. Charts included."),
        ("[excited]", "My boss said, this is the best report you've ever delivered."),
        ("[cheerful]", "I said, thank you, I worked really hard on it. While sipping a Margarita."),
        ("[excited]", "Bob doesn't need weekends. Bob doesn't need sleep."),
        ("[cheerful]", "Bob needs one thing. For you to finally take a break."),
    ]),

    # ── CLIP 4: "300 Resumes, 1 Afternoon" ─────────────────────────────
    ("bob_v2_04_resumes.wav", "austin", "Three Hundred Resumes One Afternoon", [
        ("[confident]", "We posted a job listing on a Tuesday. By Wednesday, three hundred resumes."),
        ("[sarcastic]", "Three hundred! I don't even know three hundred people."),
        ("[confident]", "Normally that's three weeks of screening. Reading the same buzzwords over and over."),
        ("[sarcastic]", "Team player. Self-starter. Proficient in Microsoft Word. Groundbreaking."),
        ("[excited]", "I gave the whole pile to Bob. I said, find me the ten best. Go."),
        ("[confident]", "Two hours later, Bob sends me a ranked shortlist with summaries for each."),
        ("[excited]", "He even flagged one candidate who never uses buzzwords but has insane GitHub projects."),
        ("[cheerful]", "We hired her. She's now our best developer."),
        ("[confident]", "Bob didn't just screen resumes. Bob found talent that humans would've missed."),
        ("[excited]", "Three hundred resumes. One afternoon. Zero headaches. Thanks Bob."),
    ]),

    # ── CLIP 5: "Bob vs. My Notifications" ─────────────────────────────
    ("bob_v2_05_notifications.wav", "hannah", "Bob Versus My Notifications", [
        ("[excited]", "I used to get over two hundred notifications a day. Two hundred!"),
        ("[sarcastic]", "My phone sounded like a casino slot machine that only pays out in stress."),
        ("[sarcastic]", "Slack, email, calendar, Teams, WhatsApp, LinkedIn, project boards."),
        ("[excited]", "My screen time report said eight hours and it was being generous."),
        ("[confident]", "Then Bob stepped in. I said, Bob, filter my life."),
        ("[cheerful]", "Bob now intercepts everything. He categorizes, prioritizes, and summarizes."),
        ("[confident]", "Out of two hundred notifications, Bob surfaces maybe twelve that actually matter."),
        ("[excited]", "Twelve! The rest? Handled, archived, or responded to."),
        ("[cheerful]", "My phone is quiet now. Like suspiciously quiet."),
        ("[excited]", "I actually heard a bird sing outside my window for the first time in three years."),
        ("[cheerful]", "Thanks Bob. You gave me back my ears."),
    ]),

    # ── CLIP 6: "The Night Owl Accountant" ─────────────────────────────
    ("bob_v2_06_accountant.wav", "daniel", "The Night Owl Accountant", [
        ("[confident]", "Quarter end used to be my personal horror movie. Three days, no sleep."),
        ("[sarcastic]", "Twelve hundred transactions. Receipt matching. Variance reports."),
        ("[sarcastic]", "By hour forty I start seeing numbers in my dreams. Not good numbers."),
        ("[excited]", "This quarter I uploaded everything to Bob and said, go to work big guy."),
        ("[confident]", "Bob processed twelve hundred transactions in under an hour."),
        ("[excited]", "Categorized, matched, analyzed, and built the variance report."),
        ("[cheerful]", "He flagged seven items that needed my brain. Just seven."),
        ("[confident]", "I reviewed them in thirty minutes. Approved five. Adjusted two."),
        ("[excited]", "Quarter end was done by lunch. By lunch!"),
        ("[cheerful]", "I picked up my kids from school that day. First time during quarter end, ever."),
        ("[excited]", "My wife thought I got fired. No babe. I got Bob."),
    ]),

    # ── CLIP 7: "Bob Speaks Quebec" ────────────────────────────────────
    ("bob_v2_07_quebec.wav", "autumn", "Bob Speaks Quebec", [
        ("[excited]", "So the funniest thing happened. We deployed Bob for a client in Quebec."),
        ("[cheerful]", "And the first thing the foreman says is, this thing better not speak France French."),
        ("[excited]", "Bob opens his mouth and starts talking like he's from Chicoutimi."),
        ("[excited]", "The whole crew lost it. They were dying laughing."),
        ("[cheerful]", "The foreman goes, okay, this guy can stay."),
        ("[confident]", "Bob doesn't just translate languages. He understands the culture."),
        ("[confident]", "The slang, the humor, the references. He gets Quebec, not textbook French."),
        ("[excited]", "By the end of the week, the crew was calling him Bobby."),
        ("[cheerful]", "They'd say, Bobby, what's the weather looking like for the pour on Thursday?"),
        ("[confident]", "And Bob would answer with the forecast, the concrete specs, and a joke."),
        ("[excited]", "Bob doesn't immigrate to your country. He becomes a citizen. In a Hawaiian shirt."),
    ]),

    # ── CLIP 8: "I Took a Vacation. Bob Didn't." ──────────────────────
    ("bob_v2_08_vacation.wav", "troy", "I Took a Vacation, Bob Didn't", [
        ("[confident]", "I haven't taken a real vacation in six years. I'm a founder. You know how it is."),
        ("[sarcastic]", "Every time I tried, something exploded. Client crisis. Server down. Team drama."),
        ("[confident]", "But last month I said, screw it. I'm going to Lisbon. No laptop."),
        ("[confident]", "Bob ran my company for ten days. Ten. Days."),
        ("[excited]", "He ran the meetings. Handled three client escalations. Sent the board report."),
        ("[excited]", "He even closed a deal using the negotiation style I taught him!"),
        ("[cheerful]", "I was sitting on a terrace with wine, watching the sunset, and my phone buzzed."),
        ("[excited]", "It was Bob. Deadass, boss. Everything's handled. Enjoy your trip."),
        ("[cheerful]", "I almost cried into my port wine."),
        ("[passionate]", "Six years of never disconnecting. Bob gave me my first real vacation."),
        ("[excited]", "I came back tanned, rested, and my company was in better shape than when I left."),
    ]),

    # ── CLIP 9: "The SaaS Graveyard" ──────────────────────────────────
    ("bob_v2_09_graveyard.wav", "diana", "The SaaS Graveyard", [
        ("[excited]", "Let me show you something. This is my old credit card statement."),
        ("[sarcastic]", "Forty-nine ninety-nine, HubSpot. Twenty-nine ninety-nine, Notion."),
        ("[sarcastic]", "Fourteen ninety-nine, Calendly. Ninety-nine, Zoom premium."),
        ("[sarcastic]", "Twelve ninety-nine for an app I subscribed to in twenty twenty-one and forgot about."),
        ("[excited]", "Total monthly SaaS spend? Over four hundred dollars. For one person!"),
        ("[confident]", "Bob replaced all of them. Every. Single. One."),
        ("[cheerful]", "CRM? Bob. Calendar? Bob. Meeting notes? Bob. Email drafting? Bob."),
        ("[excited]", "I cancelled twelve subscriptions in one afternoon. It felt like a cleanse."),
        ("[cheerful]", "My inbox is now full of sad breakup emails from apps saying, we'll miss you."),
        ("[excited]", "Sorry Notion. I've moved on. Bob wears a Hawaiian shirt and he gets me."),
    ]),

    # ── CLIP 10: "Deadass, I Got Promoted" ─────────────────────────────
    ("bob_v2_10_promoted.wav", "austin", "Deadass I Got Promoted", [
        ("[excited]", "Okay you want the craziest Bob story? Here it is."),
        ("[confident]", "I was a mid-level manager drowning in operational noise."),
        ("[sarcastic]", "Reports, scheduling, approvals, data entry. The glamorous corporate life."),
        ("[confident]", "I started using Bob six months ago. Gave him all the repetitive stuff."),
        ("[cheerful]", "Suddenly I had time. Time to actually think. Time to be strategic."),
        ("[confident]", "I started proposing ideas in meetings instead of just surviving them."),
        ("[excited]", "My boss noticed. She said, you've changed. You're more creative, more present."),
        ("[cheerful]", "I got promoted. Three months later, promoted again."),
        ("[excited]", "My buddy asked me, what's your secret?"),
        ("[excited]", "I said, I let Bob do my job. And now I do the job I was always meant to do."),
        ("[excited]", "Deadass. Bob didn't replace me. Bob unlocked me."),
        ("[passionate]", "That's the whole point. Bob doesn't take your job. He gives you a better one."),
    ]),
]


def silence(ms, sr=24000):
    return b'\x00\x00' * int(sr * ms / 1000)


def pcm_from_wav(data):
    with io.BytesIO(data) as b:
        with wave.open(b, 'rb') as w:
            return w.readframes(w.getnframes())


def get_key():
    k = os.environ.get("GROQ_API_KEY")
    if k: return k
    for p in [Path(__file__).parent.parent / ".env",
              Path(__file__).parent.parent / "backend" / ".env"]:
        if p.exists():
            for l in open(p):
                l = l.strip()
                if l.startswith("GROQ_API_KEY=") and not l.startswith("#"):
                    return l.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def gen_clip(client, idx, fname, voice, title, segs, out_dir):
    n = len(segs)
    audio = []
    print(f"\n  {'='*60}")
    print(f"  🎬 Clip {idx}/10: {title}")
    print(f"  🎙️  Voice: {voice}")
    print(f"  {'='*60}")

    for i, (d, t) in enumerate(segs):
        inp = f"{d} {t}"
        if len(inp) > 200:
            inp = f"{d} {t[:200 - len(d) - 1]}"
        print(f"    [{i+1:2d}/{n}] {t[:60]}...")

        for attempt in range(3):
            try:
                r = client.audio.speech.create(
                    model=MODEL, voice=voice, input=inp, response_format="wav")
                audio.append(pcm_from_wav(r.read()))
                audio.append(silence(PAUSE_MS))
                break
            except Exception as e:
                err = str(e)
                if "429" in err or "rate_limit" in err.lower():
                    w = RATE_LIMIT_DELAY * (attempt + 2)
                    print(f"        ⏳ Rate limit {w:.0f}s...")
                    time.sleep(w)
                elif attempt < 2:
                    print(f"        ⚠️  Retry: {err[:80]}")
                    time.sleep(RATE_LIMIT_DELAY)
                else:
                    print(f"        ❌ Failed: {err[:80]}")
                    audio.append(silence(300))
        time.sleep(RATE_LIMIT_DELAY)

    path = out_dir / fname
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000)
        for d in audio: w.writeframes(d)

    with wave.open(str(path), 'rb') as w:
        dur = w.getnframes() / w.getframerate()
    sz = path.stat().st_size / (1024*1024)
    m, s = int(dur//60), int(dur%60)
    print(f"  ✅ {fname} — {m}m{s:02d}s | {sz:.1f}MB")
    return dur


def main():
    key = get_key()
    if not key: print("ERROR: GROQ_API_KEY not found"); sys.exit(1)

    client = Groq(api_key=key)
    out = Path(__file__).parent.parent / OUTPUT_DIR
    out.mkdir(exist_ok=True)

    print("=" * 70)
    print("  🔥 10 PUNCHY BOB CLIPS — Social Media Edition")
    print(f"  Model: {MODEL}")
    print(f"  Output: {out}/")
    print("=" * 70)

    total = 0
    for i, (fn, voice, title, segs) in enumerate(CLIPS, 1):
        total += gen_clip(client, i, fn, voice, title, segs, out)

    m, s = int(total//60), int(total%60)
    print(f"\n{'='*70}")
    print(f"  🎬 ALL 10 CLIPS DONE! Total: {m}m{s:02d}s")
    print(f"  📁 {out}/")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
