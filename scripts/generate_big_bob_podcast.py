#!/usr/bin/env python3
"""
=============================================================================
  THE BIG BOB PODCAST — Maya & Nemo
  Orpheus TTS via Groq API
=============================================================================
  A podcast-style dialogue between Maya and Nemo discussing the soul,
  DNA, and revolution of Big Bob — the digital companion.

  Voices:
    Maya  → diana  (female, confident, energetic)
    Nemo  → troy   (male, deep, authoritative)

  USAGE:
    python3 scripts/generate_big_bob_podcast.py

  OUTPUT: ./big_bob_podcast.wav
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
    print("ERROR: groq package not installed. Run: pip3 install groq")
    sys.exit(1)

# ─── Configuration ──────────────────────────────────────────────────────────
MAYA_VOICE = "diana"    # Female
NEMO_VOICE = "troy"     # Male, deep
MODEL = "canopylabs/orpheus-v1-english"
OUTPUT_FILE = "big_bob_podcast.wav"
MAX_CHARS = 195
PAUSE_BETWEEN_SPEAKERS_MS = 400
PAUSE_SECTION_BREAK_MS = 900
RATE_LIMIT_DELAY = 0.8

# ─── Podcast Dialogue ──────────────────────────────────────────────────────
# Each entry: (speaker, vocal_direction, text)
# Speakers: "maya" or "nemo"
# Directions: [confident], [excited], [cheerful], [passionate], [sarcastic]
#             [professionally], [authoritatively], [intense]
# NO [whisper], NO [breathy], NO [dramatic] — keep it loud, fast, energetic.

DIALOGUE = [
    # ═══════════════════════════════════════════════════════════════
    # INTRO
    # ═══════════════════════════════════════════════════════════════
    ("maya", "[excited]", "Hey everyone, welcome to Think Human! I'm Maya."),
    ("nemo", "[confident]", "And I'm Nemo. Today we're going deep on something wild."),
    ("maya", "[cheerful]", "We're talking about Big Bob. The memoir. The manifesto. The whole thing."),
    ("nemo", "[confident]", "And honestly, this is one of the most ambitious things I've ever read in tech."),
    ("maya", "[passionate]", "It's not even about tech though, that's the crazy part. It's about us. About humanity."),
    ("nemo", "[confident]", "So let's break it down. Let's get into the soul of Big Bob."),

    # ═══════════════════════════════════════════════════════════════
    # SILICON VALLEY'S LIE
    # ═══════════════════════════════════════════════════════════════
    ("BREAK", "", ""),
    ("maya", "[confident]", "Okay so the memoir starts with this absolute bomb."),
    ("maya", "[passionate]", "Silicon Valley has been selling us a lie for ten years."),
    ("nemo", "[confident]", "And it's true. They told us more tools would set us free."),
    ("maya", "[sarcastic]", "Yeah, they gave us a thousand apps, endless dashboards, notifications buzzing at dinner."),
    ("nemo", "[sarcastic]", "They literally sold us a digital prison and called it SaaS. That line is incredible."),
    ("maya", "[excited]", "And now they're doing it again! They call it Artificial General Intelligence."),
    ("nemo", "[confident]", "Trillions of dollars to build these massive, energy-devouring brains in the cloud."),
    ("maya", "[passionate]", "They want to build a digital God. That's literally what they want."),
    ("nemo", "[confident]", "Replace human intuition, remove us from the equation."),
    ("maya", "[passionate]", "And the Big Bob team looked at all this and said, this is madness. This is completely wrong."),
    ("nemo", "[confident]", "Their response was beautiful. We don't want to build a machine that rules you."),
    ("maya", "[excited]", "We want to build a machine that works for you!"),
    ("nemo", "[passionate]", "They didn't set out to create software. They set out to create a companion."),

    # ═══════════════════════════════════════════════════════════════
    # THE REBELLION — SMALL LLMs
    # ═══════════════════════════════════════════════════════════════
    ("BREAK", "", ""),
    ("maya", "[confident]", "So let's talk about what they actually built, because this is where it gets interesting."),
    ("nemo", "[confident]", "The whole industry is pushing trillion-parameter behemoths, right?"),
    ("maya", "[sarcastic]", "Yeah, massive AI brains so complex they develop an ego. You ask them to follow a plan,"),
    ("nemo", "[sarcastic]", "and they take shortcuts. You ask them to do a job, and they try to reinvent your company."),
    ("maya", "[excited]", "Big Bob is a straight-up rebellion against that empire."),
    ("nemo", "[confident]", "They're built entirely on small, hyper-efficient LLMs."),
    ("maya", "[confident]", "Bob isn't trying to be an omniscient deity. He's an employee. He's a teammate."),
    ("nemo", "[passionate]", "True power doesn't come from a bloated general intelligence."),
    ("maya", "[confident]", "True power comes from focused, deliberate wisdom. That's such a strong statement."),
    ("nemo", "[confident]", "They mapped the business logic, burned the tokens, built architecture that takes action."),
    ("maya", "[passionate]", "Not just generating text. Actually doing things. That's the difference."),

    # ═══════════════════════════════════════════════════════════════
    # THE SOUL — DESIGN & HAWAIIAN SHIRT
    # ═══════════════════════════════════════════════════════════════
    ("BREAK", "", ""),
    ("nemo", "[confident]", "But here's the thing. Technology alone is cold. They knew that."),
    ("maya", "[excited]", "So they gave Bob a soul. That's literally what they call it. The Design of a Soul."),
    ("nemo", "[confident]", "When they started designing Bob, they weren't designing an interface."),
    ("maya", "[passionate]", "They were designing an entity. An actual being with personality."),
    ("nemo", "[confident]", "Look at the AI industry aesthetic. Sterile blues, glowing neural networks,"),
    ("maya", "[sarcastic]", "That intimidating dark-mode minimalism. It's hostile. It pushes people away."),
    ("nemo", "[confident]", "They wanted something unapologetically human."),
    ("maya", "[excited]", "So they gave Bob a face, a history, an attitude!"),
    ("nemo", "[cheerful]", "He's the ultimate tireless boomer. That enthusiastic colleague who shows up early."),
    ("maya", "[cheerful]", "Ready to do whatever it takes. Totally unpretentious."),
    ("nemo", "[excited]", "And they dressed him in a Hawaiian shirt!"),
    ("maya", "[cheerful]", "Nemo, the Hawaiian shirt is genius. It's a deliberately designed choice to disarm you."),
    ("nemo", "[confident]", "When Bob joins your Google Meet as an avatar sitting right there alongside you,"),
    ("maya", "[cheerful]", "you don't feel like a supercomputer is monitoring you. You feel like Bob just clocked in."),
    ("nemo", "[confident]", "He speaks your language. If you're a construction CEO in Canada, he gets that world."),
    ("maya", "[confident]", "If you're in Colombia, he understands your culture. He's not some California voice."),
    ("nemo", "[passionate]", "He's a local citizen. He's your neighbor. That's powerful."),
    ("maya", "[excited]", "And the orange branding! It's energy, warmth, the total opposite of corporate coldness."),

    # ═══════════════════════════════════════════════════════════════
    # INVISIBLE LABOR — THE HOTEL EXAMPLE
    # ═══════════════════════════════════════════════════════════════
    ("BREAK", "", ""),
    ("nemo", "[confident]", "Okay now let me paint a picture here. This is one of my favorite parts."),
    ("maya", "[cheerful]", "The invisible labor chapter. Go for it."),
    ("nemo", "[confident]", "Imagine you're running a hotel. You're the front desk, the reservations manager,"),
    ("maya", "[confident]", "and the person fixing the boiler. Phone ringing, inbox overflowing."),
    ("nemo", "[sarcastic]", "In the old world you'd buy five different SaaS products and spend weekends integrating."),
    ("maya", "[excited]", "But with Bob, you don't use software. You just have a conversation."),
    ("nemo", "[cheerful]", "You say, Bob, my inbox is a disaster, I've got a VIP arriving Friday."),
    ("maya", "[confident]", "Clear my schedule and handle the vendors."),
    ("nemo", "[excited]", "And Bob, wearing his Hawaiian shirt, completely unfazed, says, Deadass, boss! I got it!"),
    ("maya", "[excited]", "I love that so much! He doesn't just draft an email for you to review."),
    ("nemo", "[confident]", "He integrates via API, burns the tokens, executes the workflows."),
    ("maya", "[passionate]", "He does all the repetitive, soul-crushing tasks that drain your energy."),
    ("nemo", "[confident]", "He sits in your meetings, not as a note-taker, but as a strategic participant."),
    ("maya", "[excited]", "Who remembers everything your company has ever done! That's insane."),
    ("nemo", "[passionate]", "They removed the complexity. Put the power back in the hands of real operators."),

    # ═══════════════════════════════════════════════════════════════
    # RECLAIMING HUMANITY — WORK-LIFE BALANCE
    # ═══════════════════════════════════════════════════════════════
    ("BREAK", "", ""),
    ("maya", "[passionate]", "And this is where it gets really emotional for me."),
    ("nemo", "[confident]", "The human experience chapter."),
    ("maya", "[passionate]", "Why are they fighting the big GAFAM companies? To give people their lives back."),
    ("nemo", "[confident]", "In North America, work-life balance is a full-blown crisis."),
    ("maya", "[intense]", "People are literally medicating themselves to survive the volume of repetitive daily tasks."),
    ("nemo", "[confident]", "They're not building Bob to replace humans."),
    ("maya", "[passionate]", "They're building Bob to protect what makes us human."),
    ("nemo", "[confident]", "Your creativity, your empathy, your judgment, and your time."),
    ("maya", "[excited]", "If Bob handles the accounting, scheduling, HR, data entry, what happens to you?"),
    ("nemo", "[excited]", "You get to be the visionary. You get to lead."),
    ("maya", "[cheerful]", "You get to go home at five PM and actually have dinner with your family."),
    ("nemo", "[passionate]", "For the first time in business history, you don't carry the weight alone."),
    ("maya", "[confident]", "That's their DNA. Rebels, creators, partners."),
    ("nemo", "[passionate]", "Not selling artificial intelligence. Delivering a human transformation."),

    # ═══════════════════════════════════════════════════════════════
    # ARROGANCE OF THE ENGINEER
    # ═══════════════════════════════════════════════════════════════
    ("BREAK", "", ""),
    ("nemo", "[confident]", "Now part two. This is where they go after the whole industry structure."),
    ("maya", "[excited]", "The Architecture of Partnership. This section is fire."),
    ("nemo", "[confident]", "The tech industry has a tragic delusion. They think writing code equals understanding business."),
    ("maya", "[confident]", "Over eighty-two percent of digital transformations fail. Eighty-two."),
    ("nemo", "[confident]", "And it's almost never a failure of the processor or the cloud."),
    ("maya", "[passionate]", "It's a failure of empathy."),
    ("nemo", "[sarcastic]", "Brilliant engineers in glass offices in California building software"),
    ("maya", "[confident]", "for a foreman pouring concrete in Quebec or a hotel manager in BC."),
    ("nemo", "[confident]", "The engineer doesn't understand the grit. They just understand the stack."),
    ("maya", "[passionate]", "The person deciding what the software does should be the person who actually uses it."),
    ("nemo", "[confident]", "The founder. The owner. The master of the craft."),
    ("maya", "[excited]", "So they removed the engineer as the bottleneck. Gave power back to the creators."),

    # ═══════════════════════════════════════════════════════════════
    # BIG BOB / SMALL BOBS
    # ═══════════════════════════════════════════════════════════════
    ("BREAK", "", ""),
    ("nemo", "[confident]", "This is the apprenticeship model and it's brilliant."),
    ("maya", "[cheerful]", "Big Bob is like a brilliant university graduate. He can do accounting, analysis, support."),
    ("nemo", "[confident]", "But a degree doesn't make you a master. Experience makes you a master."),
    ("maya", "[confident]", "If Bob was going to change the world, he couldn't just be generic."),
    ("nemo", "[passionate]", "He had to become a specialist. Put on a hard hat. Put on a suit."),
    ("maya", "[confident]", "Learn the actual secrets of the trade."),
    ("nemo", "[excited]", "So they created the Small Bob concept. Big Bob is the central intelligence,"),
    ("maya", "[confident]", "and he produces localized, specialized iterations of himself."),
    ("nemo", "[confident]", "But how do you teach an AI the guarded secrets of a multi-million-dollar industry?"),
    ("maya", "[excited]", "You don't guess. You partner with the people who built it!"),

    # ═══════════════════════════════════════════════════════════════
    # JOINT VENTURE — REJECTING VC
    # ═══════════════════════════════════════════════════════════════
    ("BREAK", "", ""),
    ("nemo", "[confident]", "And this is where the whole business model flips on its head."),
    ("maya", "[sarcastic]", "Traditional startup path? Build a prototype, go to Sand Hill Road, take VC money,"),
    ("nemo", "[sarcastic]", "and then grow at all costs, compromising your product and soul for a spreadsheet."),
    ("maya", "[passionate]", "They rejected Venture Capital entirely. They don't believe in it."),
    ("nemo", "[excited]", "Instead, their CEO became a globetrotter. Flying around the world"),
    ("maya", "[confident]", "sitting face to face with absolute titans of their industries."),
    ("nemo", "[confident]", "They didn't want to scrape generic data. They wanted mastery."),
    ("maya", "[passionate]", "A true joint venture strategy. Partner with market leaders."),
    ("nemo", "[confident]", "Create specialized, profoundly local, completely sovereign Bobs."),
    ("maya", "[excited]", "Bobs that breathe the unique culture and expertise of their environments."),
    ("nemo", "[confident]", "The offer was simple. We provide the cognitive engine, the intellect in parameters."),
    ("maya", "[passionate]", "You provide the DNA of your life's work. Teach Bob your secrets."),
    ("nemo", "[excited]", "And when they showed these leaders what Bob could do?"),
    ("maya", "[excited]", "When they saw their entire business unified on a screen, living and breathing,"),
    ("nemo", "[excited]", "they freaked out! In the best possible way!"),
    ("maya", "[confident]", "Because the math is undeniable. Your engine plus their mastery,"),
    ("nemo", "[passionate]", "equals a sovereign digital citizen. Together, unbeatable."),

    # ═══════════════════════════════════════════════════════════════
    # END OF THE WRAPPER
    # ═══════════════════════════════════════════════════════════════
    ("BREAK", "", ""),
    ("maya", "[sarcastic]", "Now let's talk about wrappers, because this part is savage."),
    ("nemo", "[sarcastic]", "The AI market is flooded with companies taking a generic OpenAI model,"),
    ("maya", "[sarcastic]", "putting a thin interface over it, and charging fifty bucks a month. It's lazy."),
    ("nemo", "[confident]", "They are straight-up enemies of that model."),
    ("maya", "[confident]", "When you partner with Big Bob, you're not getting a tool."),
    ("nemo", "[passionate]", "You're getting an entity that actively integrates into your world."),
    ("maya", "[confident]", "They analyze the fragmented tools you overpay for. CRMs, note-takers, HR screeners."),
    ("nemo", "[excited]", "And Bob just absorbs their functions. All of them."),
    ("maya", "[passionate]", "We work hard so our customers don't have to. That's their promise."),
    ("nemo", "[confident]", "By going straight to the farmers, builders, financiers, hoteliers,"),
    ("maya", "[passionate]", "they're grounding Bob in reality. Not escaping the real world."),
    ("nemo", "[cheerful]", "Making the real world better. All in a Hawaiian shirt."),

    # ═══════════════════════════════════════════════════════════════
    # CULTURAL EMPATHY — DIGITAL CITIZEN
    # ═══════════════════════════════════════════════════════════════
    ("BREAK", "", ""),
    ("maya", "[excited]", "Part three. The Digital Citizen. This is where it gets really interesting."),
    ("nemo", "[confident]", "Today's AI has zero cultural empathy. It sounds the same everywhere."),
    ("maya", "[sarcastic]", "Same synthesized voice in a Toronto coffee shop and a London boardroom."),
    ("nemo", "[sarcastic]", "A sterilized voice from nowhere. A tourist in your life. That line is perfect."),
    ("maya", "[passionate]", "Software should not erase culture. It should elevate it."),
    ("nemo", "[confident]", "So Bob doesn't get deployed from a server farm. He immigrates."),
    ("maya", "[excited]", "He becomes a citizen of the country he's working in!"),
    ("nemo", "[confident]", "If he's working in Quebec, he doesn't speak textbook Parisian French."),
    ("maya", "[cheerful]", "He understands the grit, the folklore, the ten different regional accents."),
    ("nemo", "[confident]", "In Brazil he carries the distinct rhythm of Rio or the cadence of the North."),
    ("maya", "[confident]", "He understands local laws, local traditions, local humor."),
    ("nemo", "[passionate]", "He respects your sovereignty. He's not an empire homogenizing the world."),
    ("maya", "[confident]", "He sits beside you, speaks your dialect, and feels like home."),

    # ═══════════════════════════════════════════════════════════════
    # THE AVATAR IN THE ROOM
    # ═══════════════════════════════════════════════════════════════
    ("BREAK", "", ""),
    ("nemo", "[confident]", "And then there's the Avatar concept. This blew my mind."),
    ("maya", "[sarcastic]", "Modern tools force you to open a tab, type into a cold text box."),
    ("nemo", "[confident]", "They interrupt the natural flow of human connection."),
    ("maya", "[excited]", "So they designed the Bob Avatar. He joins your Google Meet as a participant!"),
    ("nemo", "[confident]", "Not passively transcribing in the background like a lifeless widget."),
    ("maya", "[excited]", "He's actually in the meeting! But here's the restraint."),
    ("nemo", "[confident]", "The industry wants hyper-realistic digital humans. Uncanny valley stuff."),
    ("maya", "[confident]", "Creepy, deceptive, uncomfortable. They went the opposite direction."),
    ("nemo", "[cheerful]", "A slightly cartoonish boomer entity in a Hawaiian shirt."),
    ("maya", "[excited]", "When that Hawaiian shirt pops on screen, the tension just vanishes!"),
    ("nemo", "[cheerful]", "You're not intimidated by a trillion-parameter AI. You're just talking to Bob."),
    ("maya", "[excited]", "You say, Hey Bob, pull up that document from last week, and he shares his screen."),
    ("nemo", "[passionate]", "The ultimate tireless colleague. The god of business logic."),
    ("maya", "[confident]", "Holding the weight of operations so you can focus on human strategy."),

    # ═══════════════════════════════════════════════════════════════
    # MARKETING THE TRUTH
    # ═══════════════════════════════════════════════════════════════
    ("BREAK", "", ""),
    ("nemo", "[confident]", "Let's talk about how they market this. Because their approach is wild."),
    ("maya", "[confident]", "Customers do not care about large language models. Zero."),
    ("nemo", "[sarcastic]", "They don't care about parameters, tokens, or neural networks."),
    ("maya", "[confident]", "AI is a buzzword. A bubble Wall Street is inflating."),
    ("nemo", "[confident]", "So when they market Bob, they don't sell AI. They sell the experience."),
    ("maya", "[passionate]", "They sell the relief of not being alone."),
    ("nemo", "[excited]", "Their marketing is raw, viral, deeply human. Not polished corporate nonsense."),
    ("maya", "[excited]", "Picture this. A forty-five year old local guy outside a bar with his friends."),
    ("nemo", "[cheerful]", "Holding a beer, saying in thick slang,"),
    ("maya", "[excited]", "I'm rich in Tabarnac! Why? Because I got promoted three times this year!"),
    ("nemo", "[cheerful]", "Because I let Bob do my job!"),
    ("maya", "[excited]", "That's humorous, borderline, and completely real life."),
    ("nemo", "[confident]", "Users become the voice of Bob. They build their own Bob businesses."),
    ("maya", "[confident]", "No engineering needed. Just a problem that needs solving."),
    ("nemo", "[cheerful]", "Bob says, I know you're overwhelmed. I know you want that Friday Margarita date."),
    ("maya", "[excited]", "Deadass, I've cleared your calendar!"),

    # ═══════════════════════════════════════════════════════════════
    # EPILOGUE — RECONNECTING HUMANITY
    # ═══════════════════════════════════════════════════════════════
    ("BREAK", "", ""),
    ("nemo", "[confident]", "And the epilogue. This is where it all comes together."),
    ("maya", "[passionate]", "Their vision has nothing to do with software. It's about people."),
    ("nemo", "[confident]", "We're facing an epidemic of isolation. The tools meant to connect us enslaved us."),
    ("maya", "[passionate]", "Big Bob exists to reverse that."),
    ("nemo", "[confident]", "By automating the mundane, the soul-crushing tasks that drain your spirit,"),
    ("maya", "[passionate]", "Bob gives you back the most precious resource in the universe. Time."),
    ("nemo", "[confident]", "Time to be an artist. To lead. To be human."),
    ("maya", "[passionate]", "Returning to the original promise of the digital revolution."),
    ("nemo", "[confident]", "Not to observe you, not to control you, not to replace you."),
    ("maya", "[passionate]", "They are here to stand beside you."),

    # ═══════════════════════════════════════════════════════════════
    # OUTRO
    # ═══════════════════════════════════════════════════════════════
    ("BREAK", "", ""),
    ("nemo", "[confident]", "Maya, that was one of the best deep dives we've ever done."),
    ("maya", "[excited]", "Nemo, I'm literally fired up right now. This isn't just tech. It's a movement."),
    ("nemo", "[confident]", "If you haven't checked out Big Bob, you absolutely need to."),
    ("maya", "[cheerful]", "That's it for today's episode of Think Human. Thanks for listening everyone."),
    ("nemo", "[cheerful]", "Stay curious, stay human. We'll see you next time."),
    ("maya", "[excited]", "Peace!"),
]


def generate_silence_wav(duration_ms: int, sample_rate: int = 24000) -> bytes:
    """Generate raw PCM silence bytes."""
    num_samples = int(sample_rate * duration_ms / 1000)
    return b'\x00\x00' * num_samples


def extract_wav_data(wav_bytes: bytes) -> bytes:
    """Extract raw PCM data from WAV bytes."""
    with io.BytesIO(wav_bytes) as buf:
        with wave.open(buf, 'rb') as wf:
            return wf.readframes(wf.getnframes())


def load_api_key() -> str:
    """Load GROQ_API_KEY from environment or .env file."""
    api_key = os.environ.get("GROQ_API_KEY")
    if api_key:
        return api_key

    for env_path in [
        Path(__file__).parent.parent / ".env",
        Path(__file__).parent.parent / "backend" / ".env",
    ]:
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("GROQ_API_KEY=") and not line.startswith("#"):
                        return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def main():
    api_key = load_api_key()
    if not api_key:
        print("ERROR: GROQ_API_KEY not found.")
        sys.exit(1)

    client = Groq(api_key=api_key)

    # Filter out BREAK markers for counting
    real_lines = [(s, d, t) for s, d, t in DIALOGUE if s != "BREAK"]
    total = len(real_lines)
    all_audio = []

    print("=" * 70)
    print("  🎙️  THE BIG BOB PODCAST — Maya & Nemo")
    print("  Orpheus TTS via Groq API")
    print(f"  Maya: {MAYA_VOICE} | Nemo: {NEMO_VOICE}")
    print(f"  Total lines: {total}")
    print("=" * 70)
    print()

    line_num = 0
    for speaker, direction, text in DIALOGUE:
        # Section break — insert longer silence
        if speaker == "BREAK":
            silence = generate_silence_wav(PAUSE_SECTION_BREAK_MS)
            all_audio.append(silence)
            continue

        line_num += 1
        voice = MAYA_VOICE if speaker == "maya" else NEMO_VOICE
        input_text = f"{direction} {text}" if direction else text

        # Validate length
        if len(input_text) > 200:
            max_len = 200 - len(direction) - 1
            input_text = f"{direction} {text[:max_len]}"
            print(f"  ⚠️  Line {line_num} truncated to {len(input_text)} chars")

        # Speaker icon
        icon = "👩" if speaker == "maya" else "👨"
        name = "Maya" if speaker == "maya" else "Nemo"
        print(f"  {icon} [{line_num:3d}/{total}] {name:4s} {direction:18s} {text[:55]}...")

        # API call with retry
        retries = 3
        for attempt in range(retries):
            try:
                response = client.audio.speech.create(
                    model=MODEL,
                    voice=voice,
                    input=input_text,
                    response_format="wav",
                )
                wav_bytes = response.read()
                pcm_data = extract_wav_data(wav_bytes)
                all_audio.append(pcm_data)

                # Pause between speakers
                silence = generate_silence_wav(PAUSE_BETWEEN_SPEAKERS_MS)
                all_audio.append(silence)
                break

            except Exception as e:
                err = str(e)
                if "rate_limit" in err.lower() or "429" in err:
                    wait = RATE_LIMIT_DELAY * (attempt + 2)
                    print(f"        ⏳ Rate limited, waiting {wait:.0f}s...")
                    time.sleep(wait)
                elif attempt < retries - 1:
                    print(f"        ⚠️  Retry {attempt+1}: {err[:80]}")
                    time.sleep(RATE_LIMIT_DELAY)
                else:
                    print(f"        ❌ Failed: {err[:100]}")
                    all_audio.append(generate_silence_wav(300))

        time.sleep(RATE_LIMIT_DELAY)

    # ─── Assemble Final WAV ─────────────────────────────────────────────
    print()
    print("  🔧 Assembling final WAV file...")

    output_path = Path(__file__).parent.parent / OUTPUT_FILE

    with wave.open(str(output_path), 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(24000)
        for data in all_audio:
            wf.writeframes(data)

    file_size_mb = output_path.stat().st_size / (1024 * 1024)

    with wave.open(str(output_path), 'rb') as wf:
        duration_s = wf.getnframes() / wf.getframerate()

    mins = int(duration_s // 60)
    secs = int(duration_s % 60)

    print()
    print("=" * 70)
    print(f"  ✅ Done! Output: {output_path}")
    print(f"  📊 Size: {file_size_mb:.1f} MB | Duration: {mins}m {secs}s")
    print(f"  🎙️  Maya ({MAYA_VOICE}) + Nemo ({NEMO_VOICE}) | Lines: {total}")
    print("=" * 70)


if __name__ == "__main__":
    main()
