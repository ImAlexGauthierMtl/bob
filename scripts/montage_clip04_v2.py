#!/usr/bin/env python3
"""
=============================================================================
  BRANDED MONTAGE v2: Veo Scenes + TTS + Orange Highlights + Logo Outro
=============================================================================
  - No subtitle captions
  - Orange (#FF4500) highlight words on white background
  - Inter font (branding)
  - Final scene: Bob logo centered + "Make It until you Fake It" slogan
  - Dynamic cuts synced to narration

  USAGE:
    python3 scripts/montage_clip04_v2.py

  OUTPUT: videos_veo/bob_branded_04_resumes.mp4
=============================================================================
"""

import os, sys, math
from pathlib import Path

FFMPEG_PATH = str(Path(__file__).parent / "ffmpeg")
os.environ["IMAGEIO_FFMPEG_EXE"] = FFMPEG_PATH

from moviepy import (
    VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip,
    ImageClip, concatenate_videoclips, vfx, ColorClip
)
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# ─── Branding ───────────────────────────────────────────────────────────────
ACCENT = (255, 69, 0)       # #FF4500
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

# ─── Config ─────────────────────────────────────────────────────────────────
BASE = Path(__file__).parent.parent
VEO_DIR = BASE / "videos_veo"
ASSETS = BASE / "video_assets"
AUDIO_FILE = BASE / "clips_final" / "bob_v2_04_resumes.wav"
LOGO_FILE = BASE / "video_assets" / "bob_logo.png"
OUTPUT = VEO_DIR / "bob_branded_04_resumes.mp4"

FONT_BOLD = str(ASSETS / "Inter-Bold.ttf")
FONT_SEMI = str(ASSETS / "Inter-SemiBold.ttf")
FONT_REG = str(ASSETS / "Inter-Regular.ttf")

VIDEO_W = 1080
VIDEO_H = 1920
FPS = 24

# ─── Highlight text overlays ────────────────────────────────────────────────
# Key phrases that appear as BIG text overlays with orange highlight keywords
# (time_start_pct, text, highlight_words)
# time_start_pct is % of total audio duration

HIGHLIGHTS = [
    (0.00, "300 RESUMES", ["300"]),
    (0.09, "ONE TUESDAY", ["TUESDAY"]),
    (0.15, "THREE WEEKS\nof screening?", ["THREE WEEKS"]),
    (0.23, '"Self-starter"\n"Team player"', ['"Self-starter"', '"Team player"']),
    (0.30, "GAVE IT\nALL TO BOB", ["BOB"]),
    (0.38, "FIND ME\nTHE TEN BEST", ["TEN BEST"]),
    (0.48, "2 HOURS\nLATER", ["2 HOURS"]),
    (0.55, "RANKED\nSHORTLIST", ["RANKED"]),
    (0.63, "INSANE\nGITHUB PROJECTS", ["INSANE"]),
    (0.70, "WE HIRED HER", ["HIRED"]),
    (0.77, "BEST DEVELOPER", ["BEST"]),
    (0.84, "ZERO\nHEADACHES", ["ZERO"]),
    (0.91, "THANKS BOB", ["BOB"]),
]

OUTRO_DURATION = 3.0  # seconds for logo outro


def load_fonts():
    """Load Inter fonts for rendering."""
    try:
        bold_72 = ImageFont.truetype(FONT_BOLD, 82)
        bold_48 = ImageFont.truetype(FONT_BOLD, 52)
        semi_36 = ImageFont.truetype(FONT_SEMI, 38)
        reg_32 = ImageFont.truetype(FONT_REG, 32)
        return {"big": bold_72, "medium": bold_48, "small": semi_36, "tiny": reg_32}
    except Exception as e:
        print(f"  ⚠️ Font fallback: {e}")
        return {
            "big": ImageFont.load_default(),
            "medium": ImageFont.load_default(),
            "small": ImageFont.load_default(),
            "tiny": ImageFont.load_default(),
        }


def create_highlight_frame(text, highlight_words, video_w, video_h, fonts):
    """Create a highlight text overlay: big text, orange on highlight words, white bg pill."""
    img = Image.new('RGBA', (video_w, video_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    font = fonts["big"]
    lines = text.split('\n')

    # Measure total text block
    line_height = 100
    total_h = len(lines) * line_height + 50

    # White rounded rect background — center of screen
    block_w = video_w - 100
    y_center = video_h // 2
    bg_top = y_center - total_h // 2 - 30
    bg_bottom = y_center + total_h // 2 + 30
    bg_left = 50
    bg_right = video_w - 50

    draw.rounded_rectangle(
        [bg_left, bg_top, bg_right, bg_bottom],
        radius=24,
        fill=(255, 255, 255, 240)
    )

    # Draw each line, highlighting specific words in orange
    for line_idx, line in enumerate(lines):
        y = y_center - total_h // 2 + line_idx * line_height + 15

        # Check if any highlight word matches the entire line
        is_highlight_line = any(hw.upper() == line.strip().upper() for hw in highlight_words)

        # Measure line width for centering
        bbox = draw.textbbox((0, 0), line, font=font)
        line_w = bbox[2] - bbox[0]
        x = (video_w - line_w) // 2

        if is_highlight_line:
            # Entire line in orange
            draw.text((x, y), line, font=font, fill=ACCENT + (255,))
        else:
            # Word-by-word coloring
            words = line.split(' ')
            cursor_x = x
            for wi, word in enumerate(words):
                is_highlight = any(
                    word.strip('"').upper() == hw.strip('"').upper()
                    for hw in highlight_words
                )
                color = ACCENT + (255,) if is_highlight else BLACK + (255,)
                draw.text((cursor_x, y), word, font=font, fill=color)
                wbbox = draw.textbbox((0, 0), word + " ", font=font)
                cursor_x += wbbox[2] - wbbox[0]

    return np.array(img)


def create_logo_outro(video_w, video_h, fonts, duration):
    """Create the ending scene: white bg + Bob logo + slogan."""
    img = Image.new('RGBA', (video_w, video_h), WHITE + (255,))
    draw = ImageDraw.Draw(img)

    # Load the Bob logo
    if LOGO_FILE.exists():
        logo = Image.open(str(LOGO_FILE)).convert('RGBA')
        # Scale logo to ~40% of width
        logo_target_w = int(video_w * 0.45)
        ratio = logo_target_w / logo.width
        logo_target_h = int(logo.height * ratio)
        logo = logo.resize((logo_target_w, logo_target_h), Image.LANCZOS)

        # Center logo
        logo_x = (video_w - logo_target_w) // 2
        logo_y = (video_h - logo_target_h) // 2 - 120
        img.paste(logo, (logo_x, logo_y), logo)
        print(f"     ✅ Logo loaded: {logo_target_w}x{logo_target_h}")
    else:
        # Fallback: draw "Bob" in large orange text
        font_huge = ImageFont.truetype(FONT_BOLD, 160)
        bbox = draw.textbbox((0, 0), "Bob", font=font_huge)
        tw = bbox[2] - bbox[0]
        x = (video_w - tw) // 2
        y = video_h // 2 - 200
        draw.text((x, y), "Bob", font=font_huge, fill=ACCENT + (255,))

    # Slogan below logo
    slogan = "Make It until you Fake It"
    font_slogan = fonts["medium"]
    bbox = draw.textbbox((0, 0), slogan, font=font_slogan)
    sw = bbox[2] - bbox[0]
    sx = (video_w - sw) // 2
    sy = video_h // 2 + 100

    draw.text((sx, sy), slogan, font=font_slogan, fill=BLACK + (255,))

    # Subtle accent line under slogan
    line_w = int(sw * 0.6)
    line_x = (video_w - line_w) // 2
    line_y = sy + 70
    draw.rectangle(
        [line_x, line_y, line_x + line_w, line_y + 4],
        fill=ACCENT + (255,)
    )

    return np.array(img.convert('RGB'))


def build_montage():
    """Build the branded montage."""
    print("=" * 65)
    print("  🎬 BRANDED MONTAGE v2")
    print("  Orange highlights + Logo outro + Inter font")
    print("=" * 65)

    fonts = load_fonts()

    # ─── Load audio ─────────────────────────────────────────────────────
    print("\n  🎵 Loading audio track...")
    audio = AudioFileClip(str(AUDIO_FILE))
    audio_duration = audio.duration
    # Total video = audio + outro
    total_duration = audio_duration + OUTRO_DURATION
    print(f"     Audio: {audio_duration:.1f}s + Outro: {OUTRO_DURATION}s = {total_duration:.1f}s")

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
            print(f"     ✅ {sf}: {clip.duration:.1f}s")
            scenes.append(clip)
        else:
            print(f"     ⚠️  {sf}: not found")

    # ─── Scene distribution (dynamic cuts) ──────────────────────────────
    # More dynamic: faster cuts, scenes mapped to narrative beats
    scene_segments = [
        (0.00, 0.30),   # Scene 1: problem setup (0-30%)
        (0.30, 0.48),   # Scene 2: Bob arrives (30-48%)
        (0.48, 0.70),   # Scene 3: AI sorting magic (48-70%)
        (0.70, 0.91),   # Scene 4: result + hire (70-91%)
        (0.91, 1.00),   # Scene 1 reprise: final beat (91-100%)
    ]

    print("\n  🎞️  Building video timeline...")
    video_segments = []

    for i, (pct_start, pct_end) in enumerate(scene_segments):
        t_start = pct_start * audio_duration
        t_end = pct_end * audio_duration
        seg_dur = t_end - t_start

        # Scene index (loop back for extra segments)
        scene = scenes[i % len(scenes)]
        scene_dur = scene.duration

        # Loop if needed
        if scene_dur < seg_dur:
            loops = math.ceil(seg_dur / scene_dur)
            looped = concatenate_videoclips([scene] * loops)
            segment = looped.subclipped(0, seg_dur)
        else:
            segment = scene.subclipped(0, min(seg_dur, scene_dur))

        # Resize to cover
        w, h = segment.size
        scale = max(VIDEO_W / w, VIDEO_H / h)
        segment = segment.resized(scale)
        segment = segment.cropped(
            x_center=segment.size[0] // 2,
            y_center=segment.size[1] // 2,
            width=VIDEO_W,
            height=VIDEO_H,
        )

        video_segments.append(segment)
        print(f"     Segment {i+1}: {t_start:.1f}s → {t_end:.1f}s ({seg_dur:.1f}s) ✅")

    base_video = concatenate_videoclips(video_segments)
    if base_video.duration > audio_duration:
        base_video = base_video.subclipped(0, audio_duration)

    # ─── Create highlight overlays ──────────────────────────────────────
    print("\n  🔶 Rendering orange highlight overlays...")
    highlight_clips = []

    for idx, (pct, text, words) in enumerate(HIGHLIGHTS):
        # Calculate time range
        if idx < len(HIGHLIGHTS) - 1:
            next_pct = HIGHLIGHTS[idx + 1][0]
        else:
            next_pct = 1.0
        t_start = pct * audio_duration
        duration = (next_pct - pct) * audio_duration

        # Create highlight frame
        frame = create_highlight_frame(text, words, VIDEO_W, VIDEO_H, fonts)

        clip = (
            ImageClip(frame)
            .with_duration(duration)
            .with_start(t_start)
        )

        highlight_clips.append(clip)

    print(f"     ✅ {len(HIGHLIGHTS)} highlights rendered")

    # ─── Logo outro scene ───────────────────────────────────────────────
    print("\n  🏷️  Creating logo outro scene...")
    outro_frame = create_logo_outro(VIDEO_W, VIDEO_H, fonts, OUTRO_DURATION)
    outro_clip = ImageClip(outro_frame).with_duration(OUTRO_DURATION)

    # ─── Assemble final video ───────────────────────────────────────────
    print("\n  🎨 Compositing...")

    # Main video with highlights
    main_composite = CompositeVideoClip(
        [base_video] + highlight_clips,
        size=(VIDEO_W, VIDEO_H)
    )
    main_composite = main_composite.with_audio(audio)

    # Concatenate with outro
    final = concatenate_videoclips([main_composite, outro_clip])

    # ─── Render ─────────────────────────────────────────────────────────
    print(f"\n  📹 Rendering {OUTPUT.name}...")
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
    print(f"  ✅ BRANDED MONTAGE COMPLETE!")
    print(f"  📁 {OUTPUT}")
    print(f"  📐 {VIDEO_W}x{VIDEO_H} @ {FPS}fps")
    print(f"  ⏱️  {total_duration:.0f}s | {size_mb:.1f}MB")
    print(f"  🔶 {len(HIGHLIGHTS)} orange highlights")
    print(f"  🏷️  Logo outro: Bob + 'Make It until you Fake It'")
    print(f"  🎵 Audio: TTS + beat (post-produced)")
    print(f"{'='*65}")


if __name__ == "__main__":
    build_montage()
