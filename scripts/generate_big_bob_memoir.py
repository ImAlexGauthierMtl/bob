#!/usr/bin/env python3
"""
=============================================================================
  THINK HUMAN: The Memoir of Big Bob — Orpheus TTS via Groq API
=============================================================================
  Generates a full WAV narration of the Big Bob memoir using Groq's
  Orpheus TTS API (canopylabs/orpheus-v1-english).

  Voice: diana (authoritative female — most human for narration)
  Emotion: Vocal directions [dramatic], [confident], [whisper], etc.

  USAGE:
    export GROQ_API_KEY=gsk_...
    python scripts/generate_big_bob_memoir.py

  OUTPUT: ./big_bob_memoir.wav
=============================================================================
"""

import os
import sys
import io
import wave
import time
import struct
import textwrap
from pathlib import Path

try:
    from groq import Groq
except ImportError:
    print("ERROR: groq package not installed. Run: pip install groq")
    sys.exit(1)

# ─── Configuration ──────────────────────────────────────────────────────────
VOICE = "diana"  # Female voices: autumn, diana, hannah
MODEL = "canopylabs/orpheus-v1-english"
OUTPUT_FILE = "big_bob_memoir.wav"
MAX_CHARS = 190  # Groq limit is 200 chars; leave margin for safety
PAUSE_BETWEEN_SECTIONS_MS = 800  # silence between major sections
PAUSE_BETWEEN_CHUNKS_MS = 300    # silence between sentence chunks
RATE_LIMIT_DELAY = 1.0           # seconds between API calls (respect rate limits)

# ─── The Memoir Text with Vocal Directions ──────────────────────────────────
# Each tuple is (vocal_direction, text)
# Vocal directions: [dramatic], [confident], [whisper], [authoritatively],
#   [warm], [passionate], [professionally], [cheerful], [sarcastic],
#   [excited], [gravelly whisper], [breathy], [intense]

MEMOIR_SEGMENTS = [
    # ═══════════════════════════════════════════════════════════════
    #  TITLE & FOREWORD
    # ═══════════════════════════════════════════════════════════════
    ("[dramatic]", "THINK HUMAN. The Memoir of Big Bob."),
    ("[warm]", "An exploration of our Soul, our DNA, and the unapologetic revolution of the digital companion."),
    ("[professionally]", "Authored in the spirit of the dent we are making in the universe."),

    # Foreword
    ("[authoritatively]", "Foreword. The Intersection of Technology and Humanity."),
    ("[dramatic]", "There are moments in human history when the noise becomes so deafening"),
    ("[whisper]", "that the only true innovation left, is silence."),
    ("[confident]", "For the last ten years, Silicon Valley has been selling us a lie."),
    ("[sarcastic]", "They told us that more tools would set us free."),
    ("[intense]", "They gave us thousands of disparate apps, endless dashboards,"),
    ("[frustrated]", "and notifications that vibrate in our pockets while we are trying to have dinner with our families."),
    ("[sarcastic]", "They sold us a digital prison, and called it SaaS."),
    ("[dramatic]", "And now, they are trying to sell us a new lie."),
    ("[sarcastic]", "They call it Artificial General Intelligence."),
    ("[intense]", "They are spending trillions of dollars to build massive, energy-devouring, trillion-parameter brains in the cloud."),
    ("[dramatic]", "They want to build a digital God."),
    ("[intense]", "They want to reinvent the world, replace human intuition, and remove us from the equation entirely."),
    ("[passionate]", "We looked at this, and thought: This is madness. This is completely wrong."),
    ("[confident]", "We don't want to build a machine that rules you."),
    ("[warm]", "We want to build a machine that works for you."),
    ("[passionate]", "We didn't set out to create software."),
    ("[dramatic]", "We set out to create a companion."),
    ("[whisper]", "This is the story of Big Bob."),

    # ═══════════════════════════════════════════════════════════════
    #  CHAPTER ONE
    # ═══════════════════════════════════════════════════════════════
    ("[authoritatively]", "Chapter One. The Anatomy of a Rebellion."),
    ("[passionate]", "It's not just what it looks like and feels like. Design is how it works."),
    ("[intense]", "And right now, the way the world works, is broken."),
    ("[professionally]", "When you look at the landscape of modern business, it is fragmented."),
    ("[sarcastic]", "You have an app for your notes, an app for your emails, an app for your CRM, an app for your hiring."),
    ("[frustrated]", "You are the human, but you have been reduced to a router."),
    ("[intense]", "A biological middleman desperately copying and pasting data between cold, indifferent systems."),
    ("[sarcastic]", "The industry's answer to this is to give you a massive AI."),
    ("[dramatic]", "A brain so large and complex that it develops an ego."),
    ("[sarcastic]", "You ask it to follow a simple plan, and it takes shortcuts."),
    ("[frustrated]", "You ask it to do a job, and it tries to reinvent your entire company."),
    ("[passionate]", "Big Bob is our rebellion against the Empire."),
    ("[confident]", "We are rejecting the trillion-parameter behemoths."),
    ("[intense]", "We proved them wrong by realizing that true power doesn't come from a bloated General Intelligence."),
    ("[dramatic]", "True power comes from focused, deliberate wisdom."),
    ("[professionally]", "Bob is built entirely on small, hyper-efficient LLMs."),
    ("[warm]", "He isn't trying to be an omniscient deity. He is an employee. He is a teammate."),
    ("[confident]", "We mapped the business logic, we burned the tokens,"),
    ("[passionate]", "and we built an architecture that doesn't just generate text. It takes action."),
    ("[whisper]", "But technology alone is not enough. Technology alone is cold."),
    ("[warm]", "To truly change the way people work, we had to give this technology a soul."),

    # ═══════════════════════════════════════════════════════════════
    #  CHAPTER TWO
    # ═══════════════════════════════════════════════════════════════
    ("[authoritatively]", "Chapter Two. The Design of a Soul."),
    ("[professionally]", "A perspective on craft and intent."),
    ("[warm]", "When we began to design Bob, we realized very early on that we were not designing an interface."),
    ("[dramatic]", "We were designing an entity."),
    ("[warm]", "There is a profound and enduring beauty in approachability."),
    ("[sarcastic]", "We looked at the aesthetic of the modern AI industry."),
    ("[frustrated]", "The sterile blues, the glowing neural networks, the intimidating, dark-mode minimalism."),
    ("[intense]", "And we found it incredibly hostile. It distances the user. It creates anxiety."),
    ("[passionate]", "We wanted something entirely different."),
    ("[confident]", "We wanted a design that was unapologetically human."),
    ("[cheerful]", "So, we gave Bob a face. We gave him a history. We gave him an attitude."),
    ("[warm]", "Bob is the ultimate, tireless Boomer."),
    ("[cheerful]", "He is that enthusiastic, ultra-hardworking colleague who shows up early,"),
    ("[warm]", "ready to do whatever it takes to support the team."),
    ("[cheerful]", "He is unpretentious. And to instantly communicate that lack of pretension,"),
    ("[excited]", "we dressed him in a Hawaiian shirt."),
    ("[confident]", "The Hawaiian shirt is not a joke. It is a profoundly deliberate design choice."),
    ("[warm]", "It disarms you."),
    ("[professionally]", "When Bob joins your Google Meet as a ghost in the machine,"),
    ("[warm]", "an avatar sitting right there alongside you,"),
    ("[cheerful]", "you don't feel like you are being monitored by a supercomputer."),
    ("[warm]", "You feel like your hardest worker just clocked in."),
    ("[professionally]", "We obsessed over his tone. Bob speaks your language."),
    ("[warm]", "If you are a construction CEO in Canada, Bob understands the grit and the accent of your world."),
    ("[warm]", "If you are in Colombia, he understands your culture."),
    ("[confident]", "He isn't a generic, homogenous voice from California. He is a local citizen. He is your neighbor."),
    ("[passionate]", "The Orange touch we use across the brand isn't just a color."),
    ("[excited]", "It is energy. It is warmth. It is the antithesis of corporate coldness."),

    # ═══════════════════════════════════════════════════════════════
    #  CHAPTER THREE
    # ═══════════════════════════════════════════════════════════════
    ("[authoritatively]", "Chapter Three. The Magic of Invisible Labor."),
    ("[whisper]", "You have to work hard to get your thinking clean, to make it simple."),
    ("[warm]", "But it's worth it in the end, because once you get there, you can move mountains."),
    ("[confident]", "We believe that the best technology is invisible. You shouldn't have to think about it."),
    ("[warm]", "Imagine you are running a hotel."),
    ("[professionally]", "You are the front desk, the reservations manager, and the person fixing the boiler."),
    ("[frustrated]", "The phone is ringing, the inbox is overflowing."),
    ("[sarcastic]", "In the old world, you would buy five different SaaS products"),
    ("[frustrated]", "and spend your weekends trying to make them talk to each other."),
    ("[confident]", "With Bob, you don't use software. You just have a conversation."),
    ("[cheerful]", "You say, Bob, my inbox is a disaster, and I have a VIP arriving on Friday."),
    ("[confident]", "Clear my schedule and handle the vendors."),
    ("[cheerful]", "And Bob, wearing his Hawaiian shirt, completely unfazed by the chaos,"),
    ("[excited]", "says, Deadass, boss. I got it."),
    ("[confident]", "He doesn't just draft an email for you to review."),
    ("[intense]", "He integrates with the systems via API. He burns the tokens. He executes the workflows."),
    ("[warm]", "He does the repetitive, soul-crushing tasks that drain your energy."),
    ("[professionally]", "He sits in your meetings, not just as a note-taker,"),
    ("[confident]", "but as a strategic participant who remembers everything your company has ever done."),
    ("[passionate]", "We removed the complexity. We removed the engineers who don't understand your business."),
    ("[dramatic]", "We put the power back into the hands of the people who actually run the world."),

    # ═══════════════════════════════════════════════════════════════
    #  CHAPTER FOUR
    # ═══════════════════════════════════════════════════════════════
    ("[authoritatively]", "Chapter Four. Reclaiming the Human Experience."),
    ("[passionate]", "Why are we doing this? Why are we fighting the big GAFAM companies?"),
    ("[warm]", "Because we want to give people their lives back."),
    ("[intense]", "In North America alone, the work-life balance is a crisis."),
    ("[frustrated]", "People are medicating themselves just to survive the sheer volume of repetitive tasks"),
    ("[intense]", "they have to do every single day."),
    ("[confident]", "We are not building Bob to replace humans."),
    ("[warm]", "We are building Bob to protect the parts of being human that actually matter."),
    ("[passionate]", "Your creativity, your empathy, your judgment, and your time."),
    ("[cheerful]", "If Bob can do the accounting, the scheduling, the HR screening, and the data entry,"),
    ("[excited]", "then what happens to you? You get to be the visionary. You get to lead."),
    ("[warm]", "You get to go home at five PM, and have dinner with your family."),
    ("[dramatic]", "For the first time in the history of business,"),
    ("[whisper]", "you don't have to carry the weight of the world alone."),
    ("[passionate]", "This is our DNA. We are rebels, we are creators, and we are partners."),
    ("[confident]", "We are not selling artificial intelligence."),
    ("[dramatic]", "We are delivering a human transformation."),
    ("[whisper]", "And we are just getting started."),

    # ═══════════════════════════════════════════════════════════════
    #  PART II
    # ═══════════════════════════════════════════════════════════════
    ("[dramatic]", "Part Two. The Architecture of Partnership."),
    ("[confident]", "How we rejected the arrogance of Silicon Valley,"),
    ("[intense]", "bypassed the Venture Capital machine, and built an alchemy of industry."),

    # CHAPTER FIVE
    ("[authoritatively]", "Chapter Five. The Arrogance of the Engineer."),
    ("[intense]", "For decades, the technology industry has operated under a profound and tragic delusion."),
    ("[sarcastic]", "The belief that writing code is the same thing as understanding a business."),
    ("[dramatic]", "Look at the statistics. Over eighty-two percent of digital transformations fail."),
    ("[intense]", "That is a staggering number."),
    ("[professionally]", "And when you look closely at why they fail,"),
    ("[confident]", "it is almost never a failure of the processor, or the database, or the cloud."),
    ("[dramatic]", "It is a failure of empathy."),
    ("[sarcastic]", "You have brilliant engineers sitting in glass offices in California"),
    ("[warm]", "trying to build software for a foreman pouring concrete in Quebec,"),
    ("[warm]", "or a hotel manager in British Columbia, or a financial analyst running legacy mainframes."),
    ("[frustrated]", "The engineer doesn't understand the grit of the construction site."),
    ("[frustrated]", "They don't understand the soul of customer service. They just understand the stack."),
    ("[passionate]", "We looked at this disconnect and thought, this is entirely backwards."),
    ("[intense]", "Why are we giving the power to shape a business to the IT department?"),
    ("[confident]", "The person who should be deciding what the software does is the person who actually uses it."),
    ("[dramatic]", "The founder. The owner. The master of the craft."),
    ("[passionate]", "We realized we had to completely remove the engineer as the bottleneck."),
    ("[confident]", "We had to give the power back to the creators."),

    # CHAPTER SIX
    ("[authoritatively]", "Chapter Six. Big Bob, Small Bobs, and the Apprenticeship."),
    ("[whisper]", "You can't just ask customers what they want and then try to give that to them."),
    ("[confident]", "By the time you get it built, they'll want something new."),
    ("[dramatic]", "You have to understand their world so deeply"),
    ("[whisper]", "that you know what they need, before they do."),
    ("[professionally]", "When we built the core cognition of Big Bob,"),
    ("[warm]", "we essentially built a brilliant university graduate."),
    ("[professionally]", "Big Bob is trained in the fundamentals."),
    ("[cheerful]", "He can be an accountant, an analyst, a customer service rep."),
    ("[confident]", "He has the generic capacity to understand logic and execute tasks."),
    ("[dramatic]", "But a university degree doesn't make you a master. Experience makes you a master."),
    ("[intense]", "We knew that if Bob was going to truly change the world, he couldn't just be generic."),
    ("[passionate]", "He had to become a specialist. He had to put on a hard hat. He had to put on a suit."),
    ("[whisper]", "He had to learn the secrets of the trade."),
    ("[confident]", "So, we conceptualized the Small Bob."),
    ("[professionally]", "Big Bob acts as the central intelligence,"),
    ("[confident]", "but he produces localized, highly specialized iterations of himself."),
    ("[dramatic]", "But how do you teach an AI the deeply guarded secrets of a multi-million-dollar industry?"),
    ("[confident]", "You don't guess. You partner with the people who built it."),

    # CHAPTER SEVEN
    ("[authoritatively]", "Chapter Seven. The Alchemy of the Joint Venture."),
    ("[sarcastic]", "The traditional path for a tech startup is incredibly predictable, and incredibly toxic."),
    ("[frustrated]", "You build a prototype, you go to Sand Hill Road, you take millions in Venture Capital,"),
    ("[intense]", "and then you are forced to grow at all costs,"),
    ("[frustrated]", "compromising your product, your vision, and your soul just to satisfy a spreadsheet."),
    ("[dramatic]", "We rejected Venture Capital. We don't believe in it."),
    ("[confident]", "We believe in partnerships."),
    ("[passionate]", "Instead of bowing to bankers who don't understand our craft,"),
    ("[excited]", "our CEO took to the skies. He became a globetrotter,"),
    ("[warm]", "traversing the world to sit face-to-face with the absolute titans of their respective fields."),
    ("[intense]", "We didn't want to scrape generic data. We wanted to capture mastery."),
    ("[dramatic]", "He sought out the very best actors across the globe"),
    ("[passionate]", "to forge a new kind of alchemy. A true Joint Venture strategy."),
    ("[confident]", "The mission was singular."),
    ("[warm]", "To partner with market leaders to create specialized, profoundly local,"),
    ("[dramatic]", "and completely sovereign Bobs"),
    ("[warm]", "that breathe the unique culture and expertise of their environments."),
    ("[professionally]", "We sat down with leaders who dominate their markets."),
    ("[warm]", "Visionaries generating staggering revenue"),
    ("[frustrated]", "but who have spent years trying and failing to find a development partner"),
    ("[intense]", "capable of building a system that actually understands their reality."),
    ("[confident]", "We proposed an unprecedented alliance, looking them directly in the eye."),
    ("[passionate]", "Our offer was simple."),
    ("[confident]", "We provide the cognitive engine, the pure intellect encapsulated in parameters,"),
    ("[dramatic]", "and you provide the DNA of your life's work."),
    ("[warm]", "Teach Bob your deeply guarded secrets, your strategies,"),
    ("[whisper]", "and the very spirit that makes you the best in the world."),
    ("[excited]", "When we showed them what Bob could do,"),
    ("[excited]", "when they saw their entire business unified, mapped out on a screen,"),
    ("[dramatic]", "living and breathing for the very first time,"),
    ("[excited]", "they freaked out. In the best possible way."),
    ("[confident]", "Because they immediately understood the math."),
    ("[professionally]", "If we provide the ultimate cognitive engine,"),
    ("[confident]", "and they provide the absolute mastery and localized IP,"),
    ("[dramatic]", "the result isn't just a software product. It is a sovereign digital citizen."),
    ("[passionate]", "And together, we become unbeatable."),

    # CHAPTER EIGHT
    ("[authoritatively]", "Chapter Eight. The End of the Wrapper."),
    ("[sarcastic]", "The current AI market is flooded with what we call wrappers."),
    ("[frustrated]", "Companies taking a generic model from OpenAI, putting a thin user interface over it,"),
    ("[sarcastic]", "and charging you fifty dollars a month. It's lazy. It lacks craft."),
    ("[intense]", "We are enemies of that model."),
    ("[confident]", "When you partner with Big Bob, you aren't just getting a tool."),
    ("[passionate]", "You are getting an entity that actively integrates into your world."),
    ("[professionally]", "We are going to systematically analyze the fragmented tools you overpay for,"),
    ("[confident]", "the CRMs, the note-takers, the HR screeners,"),
    ("[dramatic]", "and Bob will simply absorb their functions."),
    ("[passionate]", "We work hard so our customers don't have to. That is our promise."),
    ("[confident]", "By bypassing the tech-bros"),
    ("[warm]", "and going straight to the farmers, the builders, the financiers, and the hoteliers,"),
    ("[dramatic]", "we are grounding Bob in reality."),
    ("[confident]", "We aren't building an AI to escape the real world."),
    ("[warm]", "We are building Bob to make the real world a better place to live and work."),
    ("[cheerful]", "And he's doing it all in a Hawaiian shirt."),

    # ═══════════════════════════════════════════════════════════════
    #  PART III
    # ═══════════════════════════════════════════════════════════════
    ("[dramatic]", "Part Three. The Digital Citizen and the Art of Presence."),
    ("[confident]", "How we abandoned the monolithic voice of Silicon Valley"),
    ("[passionate]", "to build a companion with a passport, an accent, and an unapologetic soul."),

    # CHAPTER TEN
    ("[authoritatively]", "Chapter Ten. The Death of the Monolith."),
    ("[whisper]", "Design is not just what it looks like and feels like."),
    ("[dramatic]", "It is how it speaks. It is how it listens. It is how it belongs."),
    ("[professionally]", "If you look at the landscape of artificial intelligence today,"),
    ("[frustrated]", "you see a profound lack of cultural empathy."),
    ("[sarcastic]", "The massive tech empires of the West have built generic, monolithic voices."),
    ("[frustrated]", "A voice assistant today sounds exactly the same in a coffee shop in Toronto"),
    ("[frustrated]", "as it does in a boardroom in London."),
    ("[sarcastic]", "It is a synthesized, sterilized voice from nowhere. It is a tourist in your life."),
    ("[passionate]", "We fundamentally believe that software should not erase culture."),
    ("[dramatic]", "It should elevate it."),
    ("[confident]", "When we conceptualized Big Bob, we decided that he could not simply be deployed from a server farm."),
    ("[dramatic]", "He had to immigrate. He had to become a citizen of the country he was working in."),
    ("[warm]", "If Bob is working with a construction firm in Quebec,"),
    ("[confident]", "he shouldn't speak a standardized, Parisian, textbook French."),
    ("[warm]", "He needs to understand the grit, the folklore, and the ten different regional accents of Quebec."),
    ("[warm]", "If we bring Bob to Brazil, he shouldn't just speak Portuguese."),
    ("[excited]", "He needs to carry the distinct rhythm of Rio de Janeiro, or the unique cadence of the North."),
    ("[professionally]", "We are training Bob to understand local laws, local traditions, and local humor."),
    ("[confident]", "He doesn't just process your language. He understands your references."),
    ("[passionate]", "He respects your sovereignty."),
    ("[intense]", "We are not building an empire to homogenize the world."),
    ("[warm]", "We are building a companion who sits beside you, speaks your dialect, and feels like home."),

    # CHAPTER ELEVEN
    ("[authoritatively]", "Chapter Eleven. The Avatar in the Room."),
    ("[frustrated]", "There is an incredible arrogance in how modern productivity tools are designed."),
    ("[sarcastic]", "They force you to leave your human conversation, open a new tab,"),
    ("[frustrated]", "and type a prompt into a cold, empty text box."),
    ("[intense]", "They interrupt the natural flow of human connection."),
    ("[passionate]", "We asked ourselves,"),
    ("[intense]", "Why are we interacting with a machine like it's a database? Why isn't it just a person in the room?"),
    ("[confident]", "This is why we designed the Bob Avatar."),
    ("[professionally]", "When you have a meeting, Bob doesn't just passively transcribe in the background"),
    ("[excited]", "like a lifeless widget. Bob joins the Google Meet. He is a participant."),
    ("[professionally]", "But here is where design requires absolute restraint."),
    ("[sarcastic]", "The industry is currently obsessed with creating hyper-realistic uncanny valley digital humans."),
    ("[confident]", "We think that is a mistake. It's creepy, it's deceptive,"),
    ("[intense]", "and it makes people uncomfortable."),
    ("[confident]", "We want it to be abundantly clear that Bob is not a human,"),
    ("[passionate]", "but rather a profoundly capable, entirely unpretentious digital teammate."),
    ("[cheerful]", "So, we made him a character."),
    ("[warm]", "A slightly cartoonish, boomer-esque entity wearing a Hawaiian shirt."),
    ("[cheerful]", "When that Hawaiian shirt pops onto your screen, the tension in the room vanishes."),
    ("[warm]", "You aren't intimidated by a trillion-parameter AI."),
    ("[cheerful]", "You are simply talking to Bob."),
    ("[excited]", "You can look at the screen and say, Hey Bob, pull up that document we discussed last week,"),
    ("[cheerful]", "and he shares his screen."),
    ("[confident]", "He is the ultimate, tireless colleague,"),
    ("[dramatic]", "the God of the business logic,"),
    ("[warm]", "sitting right there with you, holding the weight of the operation"),
    ("[confident]", "so you can focus on the human strategy."),

    # CHAPTER TWELVE
    ("[authoritatively]", "Chapter Twelve. Marketing the Truth."),
    ("[whisper]", "To me, marketing is about values. This is a very complicated world."),
    ("[whisper]", "A very noisy world."),
    ("[confident]", "And we're not going to get a chance to get people to remember much about us."),
    ("[dramatic]", "No company is."),
    ("[passionate]", "So we have to be really clear on what we want them to know about us."),
    ("[intense]", "How do you market something as profound as a digital soul?"),
    ("[confident]", "You don't do it by talking about technology."),
    ("[sarcastic]", "Customers do not care about Large Language Models."),
    ("[sarcastic]", "They do not care about parameters, tokens, or neural networks."),
    ("[frustrated]", "AI is just a buzzword. A bubble that Wall Street is inflating."),
    ("[confident]", "When we market Bob, we don't sell AI. We sell the experience."),
    ("[warm]", "We sell the relief of not being alone."),
    ("[passionate]", "Our marketing isn't polished, corporate, or safe."),
    ("[dramatic]", "It is raw, viral, and deeply human."),
    ("[cheerful]", "Imagine a video of a forty-five year old local guy,"),
    ("[cheerful]", "standing outside a bar with his friends, holding a beer,"),
    ("[excited]", "and unapologetically saying in thick, everyday slang,"),
    ("[excited]", "I'm rich in Tabarnac! Why? Because I got promoted three times this year!"),
    ("[cheerful]", "Because I let Bob do my job."),
    ("[warm]", "It's humorous. It's borderline. It's real life."),
    ("[confident]", "We are building a machine of content where our users, our influencers, our community,"),
    ("[passionate]", "become the voice of Bob."),
    ("[confident]", "We give them the tools to build their own Bob businesses."),
    ("[warm]", "They don't need to be engineers. They just need to have a problem that needs solving."),
    ("[passionate]", "We are taking the fear out of the future."),
    ("[warm]", "We are showing the world a leader, an employee, and a companion who says,"),
    ("[cheerful]", "I know you're overwhelmed. I know you want to go to your Margarita date on Friday."),
    ("[excited]", "Deadass, I've cleared your calendar."),

    # ═══════════════════════════════════════════════════════════════
    #  EPILOGUE
    # ═══════════════════════════════════════════════════════════════
    ("[dramatic]", "Epilogue. Reconnecting Humanity."),
    ("[warm]", "In the end, our vision has nothing to do with software. It has to do with people."),
    ("[intense]", "We are facing an epidemic of isolation."),
    ("[frustrated]", "The very tools that were supposed to connect us, have enslaved us to our screens."),
    ("[passionate]", "We are building Big Bob to reverse that."),
    ("[warm]", "By automating the mundane, by taking on the invisible soul-crushing tasks that drain your spirit,"),
    ("[dramatic]", "Bob is giving you back the most precious resource in the universe."),
    ("[whisper]", "Time."),
    ("[warm]", "Time to be an artist. Time to lead. Time to be human."),
    ("[confident]", "We are returning to the original promise of the digital revolution."),
    ("[passionate]", "Not to observe you, not to control you,"),
    ("[dramatic]", "and certainly not to replace you."),
    ("[whisper]", "We are here to stand beside you."),
]

# ─── Section breaks (insert silence after these patterns) ───────────────────
SECTION_HEADERS = {
    "Foreword", "Chapter One", "Chapter Two", "Chapter Three", "Chapter Four",
    "Chapter Five", "Chapter Six", "Chapter Seven", "Chapter Eight",
    "Chapter Ten", "Chapter Eleven", "Chapter Twelve",
    "Part Two", "Part Three", "Epilogue",
}


def is_section_header(text: str) -> bool:
    """Check if this segment starts a new section."""
    for header in SECTION_HEADERS:
        if text.startswith(header):
            return True
    return False


def generate_silence_wav(duration_ms: int, sample_rate: int = 24000) -> bytes:
    """Generate raw PCM silence bytes for the given duration."""
    num_samples = int(sample_rate * duration_ms / 1000)
    return b'\x00\x00' * num_samples  # 16-bit silence


def extract_wav_data(wav_bytes: bytes) -> bytes:
    """Extract raw PCM data from a WAV file's bytes."""
    with io.BytesIO(wav_bytes) as buf:
        with wave.open(buf, 'rb') as wf:
            return wf.readframes(wf.getnframes())


def main():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        # Try loading from .env file in project root
        env_path = Path(__file__).parent.parent / ".env"
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("GROQ_API_KEY=") and not line.startswith("#"):
                        api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break

    if not api_key:
        print("ERROR: GROQ_API_KEY not found. Set it in environment or .env file.")
        sys.exit(1)

    client = Groq(api_key=api_key)

    total_segments = len(MEMOIR_SEGMENTS)
    all_audio_data = []

    print("=" * 70)
    print("  THINK HUMAN: The Memoir of Big Bob")
    print("  Orpheus TTS via Groq API")
    print(f"  Voice: {VOICE} | Model: {MODEL}")
    print(f"  Total segments: {total_segments}")
    print("=" * 70)
    print()

    for i, (direction, text) in enumerate(MEMOIR_SEGMENTS):
        # Build the input with vocal direction
        input_text = f"{direction} {text}"

        # Validate length
        if len(input_text) > 200:
            print(f"  ⚠️  Segment {i+1} too long ({len(input_text)} chars), truncating...")
            # Truncate text to fit within 200 chars with direction
            max_text_len = 200 - len(direction) - 1
            input_text = f"{direction} {text[:max_text_len]}"

        # Progress display
        section_marker = " 📖" if is_section_header(text) else ""
        print(f"  [{i+1:3d}/{total_segments}] {direction:20s} {text[:60]}...{section_marker}")

        # Add section silence before headers
        if is_section_header(text) and i > 0:
            silence = generate_silence_wav(PAUSE_BETWEEN_SECTIONS_MS)
            all_audio_data.append(silence)

        # Call Groq API
        retries = 3
        for attempt in range(retries):
            try:
                response = client.audio.speech.create(
                    model=MODEL,
                    voice=VOICE,
                    input=input_text,
                    response_format="wav",
                )

                # Extract raw PCM from the response WAV
                wav_bytes = response.read()
                pcm_data = extract_wav_data(wav_bytes)
                all_audio_data.append(pcm_data)

                # Small pause between chunks
                silence = generate_silence_wav(PAUSE_BETWEEN_CHUNKS_MS)
                all_audio_data.append(silence)

                break

            except Exception as e:
                error_str = str(e)
                if "rate_limit" in error_str.lower() or "429" in error_str:
                    wait_time = RATE_LIMIT_DELAY * (attempt + 2)
                    print(f"        ⏳ Rate limited, waiting {wait_time:.0f}s...")
                    time.sleep(wait_time)
                elif attempt < retries - 1:
                    print(f"        ⚠️  Error: {error_str[:80]}... retrying ({attempt+1}/{retries})")
                    time.sleep(RATE_LIMIT_DELAY)
                else:
                    print(f"        ❌ Failed after {retries} attempts: {error_str[:100]}")
                    # Insert silence as placeholder
                    silence = generate_silence_wav(500)
                    all_audio_data.append(silence)

        # Rate limit delay
        time.sleep(RATE_LIMIT_DELAY)

    # ─── Write final WAV ────────────────────────────────────────────────
    print()
    print("  🔧 Assembling final WAV file...")

    output_path = Path(__file__).parent.parent / OUTPUT_FILE

    with wave.open(str(output_path), 'wb') as wf:
        wf.setnchannels(1)       # Mono
        wf.setsampwidth(2)       # 16-bit
        wf.setframerate(24000)   # 24kHz (Orpheus standard)

        for data in all_audio_data:
            wf.writeframes(data)

    file_size_mb = output_path.stat().st_size / (1024 * 1024)

    # Calculate duration
    with wave.open(str(output_path), 'rb') as wf:
        duration_seconds = wf.getnframes() / wf.getframerate()

    minutes = int(duration_seconds // 60)
    seconds = int(duration_seconds % 60)

    print()
    print("=" * 70)
    print(f"  ✅ Done! Output: {output_path}")
    print(f"  📊 Size: {file_size_mb:.1f} MB | Duration: {minutes}m {seconds}s")
    print(f"  🎙️  Voice: {VOICE} | Segments: {total_segments}")
    print("=" * 70)


if __name__ == "__main__":
    main()
