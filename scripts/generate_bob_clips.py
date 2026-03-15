#!/usr/bin/env python3
"""
=============================================================================
  10 BOB CLIPS — "What Bob Does For You"
  Orpheus TTS via Groq API
=============================================================================
  10 individual ~1 min narrator clips showing Bob in action
  helping real people in their daily work.

  Voice: troy (deep male narrator)

  USAGE:
    python3 scripts/generate_bob_clips.py

  OUTPUT: ./clips/bob_clip_01.wav ... bob_clip_10.wav
=============================================================================
"""

import os
import sys
import io
import wave
import time
from pathlib import Path

try:
    from groq import Groq
except ImportError:
    print("ERROR: pip3 install groq")
    sys.exit(1)

# ─── Config ─────────────────────────────────────────────────────────────────
VOICE = "troy"
MODEL = "canopylabs/orpheus-v1-english"
OUTPUT_DIR = "clips"
RATE_LIMIT_DELAY = 0.8
PAUSE_BETWEEN_LINES_MS = 350
PAUSE_INTRO_MS = 600

# ─── 10 Clips ──────────────────────────────────────────────────────────────
# Each clip: (filename, title, list of (direction, text) segments)
# ~150 words per clip ≈ ~1 min of audio
# Directions: [confident], [excited], [cheerful], [passionate], [intense]

CLIPS = [
    # ── CLIP 1: The Hotel Manager ───────────────────────────────────────
    ("bob_clip_01_hotel.wav", "The Hotel Manager", [
        ("[confident]", "Meet Sarah. She runs a boutique hotel in downtown Montreal."),
        ("[confident]", "Every morning she's at the front desk by six AM."),
        ("[confident]", "She's the receptionist, the reservations manager, and the person fixing the boiler."),
        ("[intense]", "The phone is ringing. The inbox has forty-seven unread emails."),
        ("[confident]", "A VIP guest is arriving on Friday and nothing is ready."),
        ("[confident]", "But Sarah has Bob. She pulls out her phone and says,"),
        ("[cheerful]", "Bob, my inbox is a disaster and I have a VIP arriving Friday. Handle the vendors."),
        ("[excited]", "Bob says, Deadass, boss. I got it."),
        ("[confident]", "Within minutes, Bob has confirmed the florist, emailed the caterer,"),
        ("[confident]", "blocked Sarah's calendar for the walkthrough, and drafted the welcome package."),
        ("[confident]", "Sarah didn't open a single app. She just had a conversation."),
        ("[passionate]", "That's what Bob does. He removes the chaos so you can focus on the guest experience."),
        ("[confident]", "Sarah goes home at five. The VIP arrives to perfection."),
    ]),

    # ── CLIP 2: The Construction CEO ────────────────────────────────────
    ("bob_clip_02_construction.wav", "The Construction CEO", [
        ("[confident]", "Marc runs a thirty-million-dollar construction company in Quebec City."),
        ("[confident]", "Seven active job sites. Forty-two employees. Three project managers."),
        ("[intense]", "Every day is a war against deadlines, permits, and weather delays."),
        ("[confident]", "Marc used to spend his evenings reviewing timesheets and chasing subcontractors."),
        ("[confident]", "Now, Bob handles it. All of it."),
        ("[confident]", "Bob tracks every project milestone and flags delays before they become problems."),
        ("[confident]", "He cross-references the weather forecast with the pour schedule."),
        ("[excited]", "He even joins the Monday morning site call as an avatar in his Hawaiian shirt."),
        ("[cheerful]", "The foremen love it. They say, Bob, what's the status on the Beaumont project?"),
        ("[confident]", "And Bob pulls up the data, the timeline, and the budget in real time."),
        ("[confident]", "Marc stopped working weekends. His wife noticed first."),
        ("[passionate]", "Bob didn't replace Marc. Bob gave Marc his life back."),
    ]),

    # ── CLIP 3: The Midnight Inbox ──────────────────────────────────────
    ("bob_clip_03_inbox.wav", "The Midnight Inbox", [
        ("[confident]", "It's eleven PM. Lisa, a financial advisor in Toronto, is lying in bed."),
        ("[intense]", "She can't sleep because her inbox has a hundred and twelve unread messages."),
        ("[confident]", "Client requests, compliance updates, meeting confirmations, spam."),
        ("[confident]", "Before Bob, Lisa would set her alarm for five AM to tackle it."),
        ("[confident]", "Now she just says, Bob, sort my inbox. Flag anything urgent. Draft replies."),
        ("[confident]", "Bob goes to work. He categorizes every email by priority and topic."),
        ("[confident]", "He identifies three urgent client requests and drafts personalized responses."),
        ("[confident]", "He schedules two follow-up meetings and archives sixty-eight irrelevant messages."),
        ("[cheerful]", "When Lisa wakes up at seven, her inbox has twelve items. All organized, all ready."),
        ("[confident]", "She reviews Bob's drafts over coffee. Approves them with one click."),
        ("[passionate]", "Lisa sleeps now. Actually sleeps. That's what Bob does."),
        ("[confident]", "He takes the invisible weight off your shoulders so you can breathe again."),
    ]),

    # ── CLIP 4: The HR Nightmare ────────────────────────────────────────
    ("bob_clip_04_hiring.wav", "The HR Nightmare", [
        ("[confident]", "David is the head of HR at a growing tech company. They're hiring fast."),
        ("[intense]", "Three hundred applications for a single senior developer role."),
        ("[confident]", "Normally, David would spend three weeks screening resumes. Three entire weeks."),
        ("[confident]", "With Bob, it takes an afternoon."),
        ("[confident]", "Bob reads every resume. He cross-references skills against the job description."),
        ("[confident]", "He checks for culture fit based on the company's values that David defined."),
        ("[confident]", "He ranks the top twenty candidates and writes a one-paragraph summary for each."),
        ("[cheerful]", "David reviews the shortlist, adjusts two picks, and sends interview invites."),
        ("[confident]", "Bob then schedules every single interview around the team's availability."),
        ("[confident]", "He even prepares customized interview questions for each candidate."),
        ("[passionate]", "David used to dread hiring season. Now it's his favorite part of the job."),
        ("[confident]", "Because Bob handles the grind. David handles the people."),
    ]),

    # ── CLIP 5: The Meeting Where Bob Remembers ─────────────────────────
    ("bob_clip_05_meeting.wav", "The Meeting Where Bob Remembers", [
        ("[confident]", "Picture this. A quarterly strategy meeting. Eight people on a Google Meet."),
        ("[confident]", "The CEO, the CTO, two product managers, sales, marketing, and finance."),
        ("[cheerful]", "And Bob. Sitting right there in his Hawaiian shirt."),
        ("[confident]", "The CEO asks, what did we decide about the European expansion last quarter?"),
        ("[confident]", "Everyone looks at each other. Nobody remembers the exact details."),
        ("[excited]", "Bob speaks up. He pulls up the notes from March fourteenth."),
        ("[confident]", "He reads the three action items that were assigned, who owned them, and the deadlines."),
        ("[confident]", "He then shows the current status of each item without anyone having to check."),
        ("[confident]", "The room goes quiet for a second. Then the CEO smiles."),
        ("[passionate]", "Bob isn't just a note-taker. He's the institutional memory of the company."),
        ("[confident]", "He remembers every document, every decision, every conversation."),
        ("[confident]", "Your team forgets. Bob never does."),
    ]),

    # ── CLIP 6: The Quarter-End Accountant ──────────────────────────────
    ("bob_clip_06_accountant.wav", "The Quarter-End Accountant", [
        ("[confident]", "Nathalie is a senior accountant at a mid-size manufacturing firm."),
        ("[intense]", "Quarter-end is approaching. That means seventy-two hours of data entry hell."),
        ("[confident]", "Receipt reconciliation, expense categorization, variance analysis."),
        ("[confident]", "The kind of work that makes your eyes blur and your soul ache."),
        ("[confident]", "This quarter, Nathalie has Bob. She uploads the raw data and says,"),
        ("[cheerful]", "Bob, reconcile Q4 expenses against the budget. Flag anything over ten percent variance."),
        ("[confident]", "Bob processes twelve hundred transactions in under an hour."),
        ("[confident]", "He categorizes every expense, matches receipts, and builds the variance report."),
        ("[confident]", "He flags seven items that need human review with clear explanations."),
        ("[cheerful]", "Nathalie reviews the seven flags. Approves five, adjusts two."),
        ("[confident]", "What used to take three days now takes three hours."),
        ("[passionate]", "Nathalie left the office at four thirty. She picked up her kids from school."),
        ("[confident]", "For the first time during quarter-end, she was home for dinner."),
    ]),

    # ── CLIP 7: The Owner Who Goes Home at 5 ────────────────────────────
    ("bob_clip_07_five_pm.wav", "The Owner Who Goes Home at Five", [
        ("[confident]", "James owns a chain of three restaurants in Vancouver."),
        ("[intense]", "For fifteen years, he hasn't left work before nine PM. Not once."),
        ("[confident]", "Inventory, scheduling, payroll, vendor negotiations, customer complaints,"),
        ("[confident]", "health inspections, marketing, social media. All on his shoulders."),
        ("[confident]", "James was burning out. His doctor told him to slow down."),
        ("[confident]", "Then he got Bob. And everything changed."),
        ("[confident]", "Bob handles vendor orders based on inventory levels and predicted foot traffic."),
        ("[confident]", "He builds the weekly staff schedule around availability and labor costs."),
        ("[confident]", "He responds to Google reviews with personalized, on-brand replies."),
        ("[confident]", "He even tracks food cost percentages and alerts James when something drifts."),
        ("[cheerful]", "Last Tuesday, James left at four forty-five. He went to his daughter's soccer game."),
        ("[passionate]", "He sat in the stands with a coffee, watching her play, and his phone didn't buzz once."),
        ("[confident]", "Because Bob had it. All of it. The restaurants ran perfectly."),
    ]),

    # ── CLIP 8: The Marketing Team ──────────────────────────────────────
    ("bob_clip_08_marketing.wav", "The Marketing Team", [
        ("[confident]", "A four-person marketing team at a growing e-commerce brand."),
        ("[intense]", "They need to produce content for six platforms, manage ads, and analyze results."),
        ("[confident]", "Before Bob, they were drowning. Sixty-hour weeks. Constant burnout."),
        ("[confident]", "Now, Bob sits in their Slack channel like a fifth team member."),
        ("[cheerful]", "Monday morning, the team lead says, Bob, what performed best last week?"),
        ("[confident]", "Bob pulls analytics from every platform and delivers a summary in thirty seconds."),
        ("[confident]", "He identifies trending topics in their niche and suggests three content angles."),
        ("[confident]", "He drafts the social calendar for the entire week based on optimal posting times."),
        ("[confident]", "He even monitors competitor activity and flags anything worth responding to."),
        ("[cheerful]", "The team went from reactive to strategic overnight."),
        ("[confident]", "They stopped chasing metrics and started building a brand."),
        ("[passionate]", "Bob didn't make them work less. He made their work matter more."),
    ]),

    # ── CLIP 9: The Farmer's Logistics ──────────────────────────────────
    ("bob_clip_09_farmer.wav", "The Farmer's Logistics", [
        ("[confident]", "Pierre runs an organic farm outside of Sherbrooke."),
        ("[confident]", "He sells to twelve local restaurants, three grocery stores, and a weekend market."),
        ("[intense]", "Managing delivery routes, order volumes, and seasonal availability is a nightmare."),
        ("[confident]", "Pierre's expertise is growing incredible food. Not spreadsheets."),
        ("[confident]", "With Bob, Pierre just talks. He says what's ready for harvest this week."),
        ("[confident]", "Bob calculates the optimal delivery routes based on order volumes and locations."),
        ("[confident]", "He sends order confirmations to every client with expected delivery times."),
        ("[confident]", "He tracks payments and flags anyone who's overdue."),
        ("[cheerful]", "When the restaurant calls to increase their tomato order, Bob adjusts the route."),
        ("[confident]", "Pierre doesn't touch a computer. He's in the field where he belongs."),
        ("[passionate]", "Bob was built for people like Pierre. Masters of their craft"),
        ("[confident]", "who deserve a partner that handles the business so they can do what they love."),
    ]),

    # ── CLIP 10: The Founder's First Vacation ───────────────────────────
    ("bob_clip_10_vacation.wav", "The Founder's First Vacation", [
        ("[confident]", "Amira founded her company six years ago. She hasn't taken a vacation since."),
        ("[intense]", "Every time she tried, something broke. A deal fell through. A crisis hit."),
        ("[confident]", "She was the only one who knew everything. The entire business lived in her head."),
        ("[confident]", "But over the past year, Bob learned everything Amira knows."),
        ("[confident]", "Her processes, her client preferences, her negotiation style, her standards."),
        ("[confident]", "Bob became her institutional memory and her operational backbone."),
        ("[cheerful]", "Last month, Amira booked a flight to Portugal. Ten days. No laptop."),
        ("[confident]", "Bob ran the Monday meetings. He handled three client escalations."),
        ("[confident]", "He prepared the monthly report and sent it to the board on time."),
        ("[confident]", "He even closed a deal using the negotiation framework Amira taught him."),
        ("[cheerful]", "Amira sat on a terrace in Lisbon with a glass of wine, watching the sunset."),
        ("[confident]", "Her phone buzzed once. It was Bob."),
        ("[excited]", "Deadass, boss. Everything's handled. Enjoy your trip."),
        ("[passionate]", "For the first time in six years, Amira didn't worry. Because Bob had her back."),
    ]),
]


def generate_silence(duration_ms: int, sr: int = 24000) -> bytes:
    return b'\x00\x00' * int(sr * duration_ms / 1000)


def extract_pcm(wav_bytes: bytes) -> bytes:
    with io.BytesIO(wav_bytes) as buf:
        with wave.open(buf, 'rb') as wf:
            return wf.readframes(wf.getnframes())


def load_api_key() -> str:
    key = os.environ.get("GROQ_API_KEY")
    if key:
        return key
    for p in [Path(__file__).parent.parent / ".env",
              Path(__file__).parent.parent / "backend" / ".env"]:
        if p.exists():
            for line in open(p):
                line = line.strip()
                if line.startswith("GROQ_API_KEY=") and not line.startswith("#"):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def generate_clip(client, clip_idx, filename, title, segments, output_dir):
    """Generate one clip WAV file."""
    total_segs = len(segments)
    all_audio = []

    print(f"\n  {'='*60}")
    print(f"  📹 Clip {clip_idx}/10: {title}")
    print(f"  {'='*60}")

    for i, (direction, text) in enumerate(segments):
        input_text = f"{direction} {text}"
        if len(input_text) > 200:
            max_t = 200 - len(direction) - 1
            input_text = f"{direction} {text[:max_t]}"

        print(f"    [{i+1:2d}/{total_segs}] {text[:65]}...")

        retries = 3
        for attempt in range(retries):
            try:
                response = client.audio.speech.create(
                    model=MODEL,
                    voice=VOICE,
                    input=input_text,
                    response_format="wav",
                )
                pcm = extract_pcm(response.read())
                all_audio.append(pcm)
                all_audio.append(generate_silence(PAUSE_BETWEEN_LINES_MS))
                break
            except Exception as e:
                err = str(e)
                if "rate_limit" in err.lower() or "429" in err:
                    wait = RATE_LIMIT_DELAY * (attempt + 2)
                    print(f"        ⏳ Rate limit, waiting {wait:.0f}s...")
                    time.sleep(wait)
                elif attempt < retries - 1:
                    print(f"        ⚠️  Retry {attempt+1}: {err[:80]}")
                    time.sleep(RATE_LIMIT_DELAY)
                else:
                    print(f"        ❌ Failed: {err[:100]}")
                    all_audio.append(generate_silence(300))

            time.sleep(RATE_LIMIT_DELAY)

    # Write clip WAV
    clip_path = output_dir / filename
    with wave.open(str(clip_path), 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(24000)
        for data in all_audio:
            wf.writeframes(data)

    # Stats
    with wave.open(str(clip_path), 'rb') as wf:
        dur = wf.getnframes() / wf.getframerate()
    size_mb = clip_path.stat().st_size / (1024 * 1024)
    m, s = int(dur // 60), int(dur % 60)
    print(f"  ✅ {filename} — {m}m{s:02d}s | {size_mb:.1f} MB")
    return dur


def main():
    api_key = load_api_key()
    if not api_key:
        print("ERROR: GROQ_API_KEY not found.")
        sys.exit(1)

    client = Groq(api_key=api_key)
    output_dir = Path(__file__).parent.parent / OUTPUT_DIR
    output_dir.mkdir(exist_ok=True)

    print("=" * 70)
    print("  📹 10 BOB CLIPS — What Bob Does For You")
    print(f"  Voice: {VOICE} | Model: {MODEL}")
    print(f"  Output: {output_dir}/")
    print("=" * 70)

    total_duration = 0
    for idx, (filename, title, segments) in enumerate(CLIPS, 1):
        dur = generate_clip(client, idx, filename, title, segments, output_dir)
        total_duration += dur

    total_m = int(total_duration // 60)
    total_s = int(total_duration % 60)

    print()
    print("=" * 70)
    print(f"  🎬 ALL 10 CLIPS DONE!")
    print(f"  📁 Output: {output_dir}/")
    print(f"  ⏱️  Total duration: {total_m}m{total_s:02d}s")
    print("=" * 70)


if __name__ == "__main__":
    main()
