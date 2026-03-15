#!/usr/bin/env python3
"""
=============================================================================
  POST-PRODUCTION: Influencer-Style Audio Processing
=============================================================================
  Takes the 10 raw clips from clips_v2/ and applies:
    1. Trim silences (remove gaps > 150ms)
    2. Speed up 1.15x (punchier delivery)
    3. Programmatic lo-fi beat overlay (generated, no external file)
    4. Swoosh transition sounds between vocal sections
    5. Fade-out ending

  USAGE:
    python3 scripts/postprod_clips.py

  INPUT:  clips_v2/*.wav
  OUTPUT: clips_final/*.wav
=============================================================================
"""

import os, sys, struct, math, wave, io
import numpy as np
from pathlib import Path
from pydub import AudioSegment
from pydub.silence import detect_nonsilent

INPUT_DIR = "clips_v2"
OUTPUT_DIR = "clips_final"
SAMPLE_RATE = 24000
SPEED_FACTOR = 1.15
SILENCE_THRESH_DB = -40
MIN_SILENCE_MS = 150
KEEP_SILENCE_MS = 80       # keep this much silence between phrases
BEAT_VOLUME_DB = -20        # beat volume relative to voice
SWOOSH_VOLUME_DB = -12
FADE_OUT_MS = 2500

# ─── Programmatic Sound Generation ─────────────────────────────────────────

def generate_kick(sr=24000, duration_ms=120):
    """Generate a punchy kick drum sound."""
    n = int(sr * duration_ms / 1000)
    t = np.linspace(0, duration_ms / 1000, n, dtype=np.float64)
    # Frequency sweep from 150Hz down to 40Hz
    freq = 150 * np.exp(-t * 12)
    # Sine wave with frequency sweep
    phase = 2 * np.pi * np.cumsum(freq) / sr
    wave_data = np.sin(phase)
    # Amplitude envelope — fast attack, quick decay
    envelope = np.exp(-t * 25)
    wave_data *= envelope * 0.8
    return (wave_data * 32767).astype(np.int16).tobytes()


def generate_hihat(sr=24000, duration_ms=40):
    """Generate a short hi-hat sound (filtered noise)."""
    n = int(sr * duration_ms / 1000)
    noise = np.random.randn(n) * 0.3
    # Sharp decay
    t = np.linspace(0, 1, n)
    envelope = np.exp(-t * 15)
    wave_data = noise * envelope
    return (wave_data * 32767).astype(np.int16).tobytes()


def generate_snare(sr=24000, duration_ms=100):
    """Generate a snare-like sound (noise + tone)."""
    n = int(sr * duration_ms / 1000)
    t = np.linspace(0, duration_ms / 1000, n, dtype=np.float64)
    # Noise component
    noise = np.random.randn(n) * 0.4
    # Tone component at 200Hz
    tone = np.sin(2 * np.pi * 200 * t) * 0.3
    envelope = np.exp(-t * 20)
    wave_data = (noise + tone) * envelope
    return (wave_data * 32767).astype(np.int16).tobytes()


def generate_swoosh(sr=24000, duration_ms=250):
    """Generate a swoosh transition sound."""
    n = int(sr * duration_ms / 1000)
    t = np.linspace(0, 1, n, dtype=np.float64)
    # Filtered noise with volume envelope (crescendo then quick drop)
    noise = np.random.randn(n)
    # Bandpass-ish: modulate noise with a sweeping sine
    sweep = np.sin(2 * np.pi * (500 + 3000 * t) * t / sr * 50)
    envelope = np.sin(np.pi * t) ** 0.5  # smooth arc
    wave_data = noise * sweep * envelope * 0.5
    return (wave_data * 32767).astype(np.int16).tobytes()


def generate_beat_loop(bpm=95, bars=4, sr=24000):
    """
    Generate a lo-fi style beat loop.
    Pattern per bar (4 beats):
      Beat 1: kick + hihat
      Beat 2: hihat
      Beat 3: snare + hihat
      Beat 4: hihat
    With extra hihat on the "and" (off-beat).
    """
    beat_duration_ms = int(60000 / bpm)  # ms per beat
    half_beat_ms = beat_duration_ms // 2
    bar_samples = int(sr * beat_duration_ms * 4 / 1000)

    kick = generate_kick(sr)
    snare = generate_snare(sr)
    hihat = generate_hihat(sr)

    def samples_at_ms(ms):
        return int(sr * ms / 1000)

    bar_data = np.zeros(bar_samples, dtype=np.float64)

    def overlay_sound(data, sound_bytes, offset_ms):
        """Overlay a sound at a given offset."""
        start = samples_at_ms(offset_ms)
        sound = np.frombuffer(sound_bytes, dtype=np.int16).astype(np.float64) / 32767
        end = min(start + len(sound), len(data))
        length = end - start
        if length > 0:
            data[start:end] += sound[:length]

    for beat in range(4):
        beat_offset = beat * beat_duration_ms

        # Hi-hat on every beat
        overlay_sound(bar_data, hihat, beat_offset)
        # Hi-hat on off-beat
        overlay_sound(bar_data, hihat, beat_offset + half_beat_ms)

        # Kick on beat 1 and 3 (index 0 and 2)
        if beat == 0:
            overlay_sound(bar_data, kick, beat_offset)
        # Snare on beat 2 and 4 (index 1 and 3) — but lighter on 4
        if beat == 1:
            overlay_sound(bar_data, snare, beat_offset)
        if beat == 3:
            overlay_sound(bar_data, snare, beat_offset)

    # Normalize
    peak = np.max(np.abs(bar_data))
    if peak > 0:
        bar_data = bar_data / peak * 0.7

    # Repeat for N bars
    full_loop = np.tile(bar_data, bars)
    pcm = (full_loop * 32767).astype(np.int16).tobytes()

    # Convert to AudioSegment
    return AudioSegment(
        data=pcm,
        sample_width=2,
        frame_rate=sr,
        channels=1
    )


def generate_swoosh_segment():
    """Generate a swoosh as AudioSegment."""
    pcm = generate_swoosh()
    return AudioSegment(
        data=pcm,
        sample_width=2,
        frame_rate=SAMPLE_RATE,
        channels=1
    )


# ─── Audio Processing Functions ────────────────────────────────────────────

def trim_silences(audio, thresh_db=SILENCE_THRESH_DB,
                  min_silence=MIN_SILENCE_MS, keep=KEEP_SILENCE_MS):
    """Remove silences longer than min_silence, keeping 'keep' ms of gap."""
    nonsilent = detect_nonsilent(audio, min_silence_len=min_silence,
                                 silence_thresh=thresh_db)
    if not nonsilent:
        return audio

    pieces = []
    gap = AudioSegment.silent(duration=keep, frame_rate=audio.frame_rate)
    for i, (start, end) in enumerate(nonsilent):
        pieces.append(audio[start:end])
        if i < len(nonsilent) - 1:
            pieces.append(gap)

    return sum(pieces[1:], pieces[0]) if pieces else audio


def speed_up(audio, factor=SPEED_FACTOR):
    """Speed up audio by resampling (changes speed without pitch correction)."""
    # Get raw samples
    samples = np.frombuffer(audio.raw_data, dtype=np.int16).astype(np.float64)

    # Resample by interpolation
    old_len = len(samples)
    new_len = int(old_len / factor)
    indices = np.linspace(0, old_len - 1, new_len)
    new_samples = np.interp(indices, np.arange(old_len), samples)

    pcm = new_samples.astype(np.int16).tobytes()
    return AudioSegment(
        data=pcm,
        sample_width=audio.sample_width,
        frame_rate=audio.frame_rate,
        channels=audio.channels
    )


def overlay_beat(voice, beat_loop, beat_vol_db=BEAT_VOLUME_DB):
    """Loop the beat to match voice length and overlay at lower volume."""
    voice_len = len(voice)
    # Repeat beat loop to cover full voice duration
    repeats = (voice_len // len(beat_loop)) + 1
    full_beat = beat_loop * repeats
    full_beat = full_beat[:voice_len]
    # Reduce beat volume
    full_beat = full_beat + beat_vol_db
    return voice.overlay(full_beat)


def process_clip(input_path, output_path, beat_loop, swoosh):
    """Apply full post-production pipeline to one clip."""
    # Load
    audio = AudioSegment.from_wav(str(input_path))
    original_duration = len(audio) / 1000

    # 1. Trim silences
    audio = trim_silences(audio)

    # 2. Speed up
    audio = speed_up(audio)

    # 3. Add swoosh at beginning (short intro hit)
    intro_swoosh = swoosh + (SWOOSH_VOLUME_DB)
    # Small silence before voice
    intro = intro_swoosh + AudioSegment.silent(duration=100,
                                                frame_rate=SAMPLE_RATE)
    audio = intro + audio

    # 4. Overlay beat
    audio = overlay_beat(audio, beat_loop)

    # 5. Fade out
    audio = audio.fade_out(FADE_OUT_MS)

    # 6. Small fade in
    audio = audio.fade_in(200)

    # Export
    audio.export(str(output_path), format="wav")

    final_duration = len(audio) / 1000
    return original_duration, final_duration


def main():
    input_dir = Path(__file__).parent.parent / INPUT_DIR
    output_dir = Path(__file__).parent.parent / OUTPUT_DIR
    output_dir.mkdir(exist_ok=True)

    if not input_dir.exists():
        print(f"ERROR: {input_dir} not found. Run generate_bob_clips_v2.py first.")
        sys.exit(1)

    clips = sorted(input_dir.glob("*.wav"))
    if not clips:
        print(f"ERROR: No .wav files found in {input_dir}")
        sys.exit(1)

    print("=" * 70)
    print("  🎬 POST-PRODUCTION: Influencer-Style Processing")
    print(f"  Input:  {input_dir}/ ({len(clips)} clips)")
    print(f"  Output: {output_dir}/")
    print("=" * 70)

    # Generate the beat loop and swoosh
    print("\n  🥁 Generating beat loop (95 BPM, lo-fi style)...")
    beat_loop = generate_beat_loop(bpm=95, bars=4)
    print(f"     Beat loop: {len(beat_loop)}ms per cycle")

    print("  💨 Generating swoosh transition...")
    swoosh = generate_swoosh_segment()
    print(f"     Swoosh: {len(swoosh)}ms")

    print()
    print("  📋 Processing pipeline:")
    print("     1. Trim silences (>{MIN_SILENCE_MS}ms gaps removed)")
    print(f"     2. Speed up {SPEED_FACTOR}x")
    print("     3. Swoosh intro")
    print(f"     4. Beat overlay at {BEAT_VOLUME_DB}dB")
    print(f"     5. Fade out ({FADE_OUT_MS}ms)")
    print()

    total_before = 0
    total_after = 0

    for i, clip_path in enumerate(clips, 1):
        out_path = output_dir / clip_path.name
        print(f"  🎙️  [{i:2d}/{len(clips)}] {clip_path.name}...", end=" ", flush=True)

        before, after = process_clip(clip_path, out_path, beat_loop, swoosh)
        total_before += before
        total_after += after

        saved = ((before - after) / before * 100) if before > 0 else 0
        print(f"✅ {before:.0f}s → {after:.0f}s ({saved:.0f}% tighter)")

    tb_m, tb_s = int(total_before // 60), int(total_before % 60)
    ta_m, ta_s = int(total_after // 60), int(total_after % 60)
    saved_pct = ((total_before - total_after) / total_before * 100) if total_before > 0 else 0

    print()
    print("=" * 70)
    print(f"  ✅ ALL {len(clips)} CLIPS PROCESSED!")
    print(f"  📁 Output: {output_dir}/")
    print(f"  ⏱️  Before: {tb_m}m{tb_s:02d}s → After: {ta_m}m{ta_s:02d}s ({saved_pct:.0f}% tighter)")
    print(f"  🎧 Beat: 95 BPM lo-fi | Speed: {SPEED_FACTOR}x | Fade: {FADE_OUT_MS}ms")
    print("=" * 70)


if __name__ == "__main__":
    main()
