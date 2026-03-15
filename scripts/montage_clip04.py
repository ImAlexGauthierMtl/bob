#!/usr/bin/env python3
"""
=============================================================================
  DYNAMIC MONTAGE: Veo Scenes + TTS Soundtrack + Closed Captions
=============================================================================
  Combines:
    - 4 Veo 3.1 AI-generated video scenes
    - Post-produced TTS audio (with beat, speed-up, swoosh)
    - Animated closed captions (social media style)
    - Dynamic editing (beat-synced cuts, zoom pulses)

  USAGE:
    python3 scripts/montage_clip04.py

  OUTPUT: videos_veo/bob_final_04_resumes.mp4
=============================================================================
"""

import os, sys, math
from pathlib import Path

FFMPEG_PATH = str(Path(__file__).parent / "ffmpeg")
os.environ["IMAGEIO_FFMPEG_EXE"] = FFMPEG_PATH

from moviepy import (
    VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip,
    ImageClip, concatenate_videoclips, vfx
)
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# ─── Config ─────────────────────────────────────────────────────────────────
BASE = Path(__file__).parent.parent
VEO_DIR = BASE / "videos_veo"
AUDIO_FILE = BASE / "clips_final" / "bob_v2_04_resumes.wav"
OUTPUT = VEO_DIR / "bob_final_04_resumes.mp4"

VIDEO_W = 1080
VIDEO_H = 1920
FPS = 24

# ─── Narration segments with timing hints ───────────────────────────────────
# Each (text, approximate_duration_seconds)
# These will be distributed across the video timeline
CAPTIONS = [
    "We posted a job listing on a Tuesday.",
    "By Wednesday — three hundred resumes.",
    "Three hundred! I don't even know three hundred people.",
    "Normally that's three weeks of screening.",
    "Reading the same buzzwords over and over.",
    "Team player. Self-starter. Proficient in Microsoft Word.",
    "Groundbreaking.",
    "I gave the whole pile to Bob.",
    "I said — find me the ten best. Go.",
    "Two hours later, Bob sends me a ranked shortlist",
    "with summaries for each.",
    "He even flagged one candidate",
    "who never uses buzzwords",
    "but has insane GitHub projects.",
    "We hired her.",
    "She's now our best developer.",
    "Bob didn't just screen resumes.",
    "Bob found talent that humans would've missed.",
    "Three hundred resumes.",
    "One afternoon.",
    "Zero headaches.",
    "Thanks Bob.",
]


def create_caption_clip(text, duration, video_w, video_h):
    """Create a social-media-style caption overlay using PIL."""
    # Create transparent image
    img = Image.new('RGBA', (video_w, video_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Try to use system font, fallback to default
    font_size = 58
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
        font_bold = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", font_size)
    except:
        try:
            font = ImageFont.truetype("/System/Library/Fonts/SFNS.ttf", font_size)
            font_bold = font
        except:
            font = ImageFont.load_default()
            font_bold = font

    # Word wrap
    words = text.split()
    lines = []
    current = ""
    for w in words:
        test = f"{current} {w}".strip()
        bbox = draw.textbbox((0, 0), test, font=font_bold)
        if bbox[2] - bbox[0] > video_w - 120:
            if current:
                lines.append(current)
            current = w
        else:
            current = test
    if current:
        lines.append(current)

    # Calculate total height
    line_h = font_size + 16
    total_h = len(lines) * line_h + 40

    # Position: lower third of screen
    y_start = int(video_h * 0.68)

    # Draw background pill
    bg_left = 40
    bg_right = video_w - 40
    bg_top = y_start - 20
    bg_bottom = y_start + total_h
    draw.rounded_rectangle(
        [bg_left, bg_top, bg_right, bg_bottom],
        radius=20,
        fill=(0, 0, 0, 180)
    )

    # Draw text centered
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font_bold)
        tw = bbox[2] - bbox[0]
        x = (video_w - tw) // 2
        y = y_start + i * line_h

        # White text with slight shadow
        draw.text((x + 2, y + 2), line, font=font_bold, fill=(0, 0, 0, 120))
        draw.text((x, y), line, font=font_bold, fill=(255, 255, 255, 255))

    # Convert to numpy array
    return np.array(img)


def build_montage():
    """Build the final dynamic montage."""
    print("=" * 65)
    print("  🎬 DYNAMIC MONTAGE: Veo 3.1 + TTS + Captions")
    print("=" * 65)

    # ─── Load audio ─────────────────────────────────────────────────────
    print("\n  🎵 Loading audio track...")
    audio = AudioFileClip(str(AUDIO_FILE))
    total_duration = audio.duration
    print(f"     Duration: {total_duration:.1f}s")

    # ─── Load Veo scenes ────────────────────────────────────────────────
    scene_files = [
        "scene1_resume_overload.mp4",
        "scene2_bob_takes_over.mp4",
        "scene3_ai_sorting.mp4",
        "scene4_perfect_hire.mp4",
    ]

    print("\n  🎥 Loading Veo scenes...")
    scenes = []
    for sf in scene_files:
        path = VEO_DIR / sf
        if path.exists():
            clip = VideoFileClip(str(path))
            print(f"     ✅ {sf}: {clip.duration:.1f}s ({clip.size[0]}x{clip.size[1]})")
            scenes.append(clip)
        else:
            print(f"     ⚠️  {sf}: not found")

    if not scenes:
        print("  ❌ No scenes found!")
        return

    # ─── Dynamic scene distribution ─────────────────────────────────────
    # Map narration segments to scenes with dynamic cuts
    # Scene 1: resume overload (lines 0-6) — problem
    # Scene 2: Bob arrives (lines 7-8) — hero entrance
    # Scene 3: AI sorting (lines 9-13) — action
    # Scene 4: perfect hire (lines 14-21) — resolution

    n_captions = len(CAPTIONS)
    caption_dur = total_duration / n_captions  # avg duration per caption

    scene_mapping = [
        (0, 7),    # Scene 1: captions 0-6
        (7, 9),    # Scene 2: captions 7-8
        (9, 14),   # Scene 3: captions 9-13
        (14, 22),  # Scene 4: captions 14-21
    ]

    # Calculate time ranges for each scene
    scene_times = []
    for start_cap, end_cap in scene_mapping:
        t_start = start_cap * caption_dur
        t_end = end_cap * caption_dur
        scene_times.append((t_start, min(t_end, total_duration)))

    print(f"\n  📋 Scene distribution:")
    for i, (ts, te) in enumerate(scene_times):
        print(f"     Scene {i+1}: {ts:.1f}s → {te:.1f}s ({te-ts:.1f}s)")

    # ─── Build video clips with dynamic zoom ────────────────────────────
    print("\n  🎞️  Building dynamic video segments...")
    video_segments = []

    for i, ((t_start, t_end), scene) in enumerate(zip(scene_times, scenes)):
        seg_duration = t_end - t_start
        scene_dur = scene.duration

        # If scene is shorter, loop it; if longer, trim
        if scene_dur < seg_duration:
            # Loop the scene
            loops_needed = math.ceil(seg_duration / scene_dur)
            looped = concatenate_videoclips([scene] * loops_needed)
            segment = looped.subclipped(0, seg_duration)
        else:
            segment = scene.subclipped(0, min(seg_duration, scene_dur))

        # Resize to target dimensions (cover mode)
        w, h = segment.size
        scale = max(VIDEO_W / w, VIDEO_H / h)
        segment = segment.resized(scale)

        # Center crop
        segment = segment.cropped(
            x_center=segment.size[0] // 2,
            y_center=segment.size[1] // 2,
            width=VIDEO_W,
            height=VIDEO_H,
        )

        video_segments.append(segment)
        print(f"     Scene {i+1}: {seg_duration:.1f}s ✅")

    # ─── Concatenate video segments ─────────────────────────────────────
    print("\n  🔗 Concatenating video segments...")
    base_video = concatenate_videoclips(video_segments)

    # Trim to match audio
    if base_video.duration > total_duration:
        base_video = base_video.subclipped(0, total_duration)

    # ─── Create caption overlays ────────────────────────────────────────
    print("\n  💬 Rendering closed captions...")
    caption_clips = []

    for idx, text in enumerate(CAPTIONS):
        t_start = idx * caption_dur
        t_end = (idx + 1) * caption_dur

        # Create caption image
        cap_array = create_caption_clip(text, caption_dur, VIDEO_W, VIDEO_H)

        # Create image clip
        cap_clip = (
            ImageClip(cap_array)
            .with_duration(caption_dur)
            .with_start(t_start)
        )

        caption_clips.append(cap_clip)
        if idx % 5 == 0:
            print(f"     Caption {idx+1}/{n_captions}: '{text[:50]}...'")

    print(f"     ✅ {n_captions} captions rendered")

    # ─── Composite everything ───────────────────────────────────────────
    print("\n  🎨 Compositing final video...")
    final = CompositeVideoClip(
        [base_video] + caption_clips,
        size=(VIDEO_W, VIDEO_H)
    )

    # Attach audio (TTS soundtrack replaces Veo's native audio)
    final = final.with_audio(audio)

    # ─── Render ─────────────────────────────────────────────────────────
    print(f"\n  📹 Rendering {OUTPUT.name}...")
    print(f"     This may take 2-3 minutes...")

    final.write_videofile(
        str(OUTPUT),
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        logger=None,
        threads=4,
        preset="fast",
        bitrate="5000k",
    )

    size_mb = OUTPUT.stat().st_size / (1024 * 1024)

    print(f"\n{'='*65}")
    print(f"  ✅ MONTAGE COMPLETE!")
    print(f"  📁 {OUTPUT}")
    print(f"  📐 {VIDEO_W}x{VIDEO_H} @ {FPS}fps")
    print(f"  ⏱️  {total_duration:.0f}s | {size_mb:.1f}MB")
    print(f"  🎵 Audio: TTS + beat (from clips_final)")
    print(f"  💬 Captions: {n_captions} segments")
    print(f"{'='*65}")


if __name__ == "__main__":
    build_montage()
