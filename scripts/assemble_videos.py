#!/usr/bin/env python3
"""
=============================================================================
  VIDEO ASSEMBLY: Cartoon Clips + Audio → MP4
=============================================================================
  Combines cartoon images from video_assets/ with audio from clips_final/
  into 10 social-media-ready MP4 videos.

  Effects:
    - Ken Burns (slow zoom) on each image
    - Smooth crossfade transitions between scenes
    - 9:16 vertical format (1080x1920) for TikTok/Reels
    - Audio synced from processed clips

  USAGE:
    python3 scripts/assemble_videos.py

  INPUT:  video_assets/*.png + clips_final/*.wav
  OUTPUT: videos_final/*.mp4
=============================================================================
"""

import os, sys, glob
from pathlib import Path

# Point to local ffmpeg
FFMPEG_PATH = str(Path(__file__).parent / "ffmpeg")
os.environ["IMAGEIO_FFMPEG_EXE"] = FFMPEG_PATH

from moviepy import (
    ImageClip, AudioFileClip, concatenate_videoclips,
    CompositeVideoClip, vfx
)
from PIL import Image
import numpy as np

OUTPUT_DIR = "videos_final"
ASSETS_DIR = "video_assets"
AUDIO_DIR = "clips_final"
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
FPS = 24
CROSSFADE_DURATION = 0.5

# Map clip numbers to their image files and audio files
CLIPS = [
    {
        "num": 1, "title": "I Broke Up With My Apps",
        "audio": "bob_v2_01_breakup.wav",
        "images": ["clip01_scene1", "clip01_scene2", "clip01_scene3"],
        "output": "bob_video_01_breakup.mp4"
    },
    {
        "num": 2, "title": "Bob's First Meeting",
        "audio": "bob_v2_02_first_meeting.wav",
        "images": ["clip02_scene1", "clip02_scene2", "clip02_scene3"],
        "output": "bob_video_02_meeting.mp4"
    },
    {
        "num": 3, "title": "Friday at 4:55",
        "audio": "bob_v2_03_friday.wav",
        "images": ["clip03_scene1", "clip03_scene2", "clip03_scene3"],
        "output": "bob_video_03_friday.mp4"
    },
    {
        "num": 4, "title": "300 Resumes",
        "audio": "bob_v2_04_resumes.wav",
        "images": ["clip04_scene1", "clip04_scene2", "clip04_scene3"],
        "output": "bob_video_04_resumes.mp4"
    },
    {
        "num": 5, "title": "Bob vs Notifications",
        "audio": "bob_v2_05_notifications.wav",
        "images": ["clip05_scene1", "clip05_scene2", "clip05_scene3"],
        "output": "bob_video_05_notifications.mp4"
    },
    {
        "num": 6, "title": "The Night Owl Accountant",
        "audio": "bob_v2_06_accountant.wav",
        "images": ["clip06_scene1", "clip06_scene2", "clip06_scene3"],
        "output": "bob_video_06_accountant.mp4"
    },
    {
        "num": 7, "title": "Bob Speaks Quebec",
        "audio": "bob_v2_07_quebec.wav",
        "images": ["clip07_scene1", "clip07_scene2", "clip07_scene3"],
        "output": "bob_video_07_quebec.mp4"
    },
    {
        "num": 8, "title": "Vacation",
        "audio": "bob_v2_08_vacation.wav",
        "images": ["clip08_scene1", "clip08_scene2", "clip08_scene3"],
        "output": "bob_video_08_vacation.mp4"
    },
    {
        "num": 9, "title": "The SaaS Graveyard",
        "audio": "bob_v2_09_graveyard.wav",
        "images": ["clip09_scene1", "clip09_scene2", "clip09_scene3"],
        "output": "bob_video_09_graveyard.mp4"
    },
    {
        "num": 10, "title": "Deadass I Got Promoted",
        "audio": "bob_v2_10_promoted.wav",
        "images": ["clip10_scene1", "clip10_scene2", "clip10_scene3"],
        "output": "bob_video_10_promoted.mp4"
    },
]


def find_image(assets_dir, prefix):
    """Find image file by prefix (handles timestamp suffix)."""
    matches = glob.glob(str(assets_dir / f"{prefix}*.png"))
    if matches:
        return matches[0]
    return None


def prepare_image_for_video(img_path, target_w, target_h):
    """Resize and crop image to fill target dimensions (cover mode)."""
    img = Image.open(img_path).convert("RGB")
    w, h = img.size

    # Calculate scale to cover the target area
    scale = max(target_w / w, target_h / h)
    new_w = int(w * scale)
    new_h = int(h * scale)
    img = img.resize((new_w, new_h), Image.LANCZOS)

    # Center crop
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    img = img.crop((left, top, left + target_w, top + target_h))

    return np.array(img)


def create_ken_burns_clip(img_array, duration, zoom_start=1.0, zoom_end=1.15):
    """Create a clip with Ken Burns zoom effect."""
    h, w = img_array.shape[:2]

    def make_frame(t):
        progress = t / duration
        zoom = zoom_start + (zoom_end - zoom_start) * progress

        # Calculate crop region
        crop_w = int(w / zoom)
        crop_h = int(h / zoom)
        x = (w - crop_w) // 2
        y = (h - crop_h) // 2

        # Crop and resize back
        cropped = img_array[y:y+crop_h, x:x+crop_w]
        # Resize back to original dimensions
        from PIL import Image as PILImage
        pil_img = PILImage.fromarray(cropped)
        pil_img = pil_img.resize((w, h), PILImage.LANCZOS)
        return np.array(pil_img)

    clip = ImageClip(img_array).with_duration(duration)
    clip = clip.transform(lambda get_frame, t: make_frame(t))
    return clip


def assemble_clip(clip_config, base_dir, assets_dir, audio_dir, output_dir):
    """Assemble one video clip from images and audio."""
    num = clip_config["num"]
    title = clip_config["title"]
    audio_file = audio_dir / clip_config["audio"]
    output_file = output_dir / clip_config["output"]

    print(f"\n  {'='*55}")
    print(f"  🎬 Clip {num}/10: {title}")
    print(f"  {'='*55}")

    # Check audio
    if not audio_file.exists():
        print(f"  ❌ Audio not found: {audio_file}")
        return None

    # Load audio to get duration
    audio = AudioFileClip(str(audio_file))
    total_duration = audio.duration
    print(f"  🎵 Audio: {total_duration:.1f}s")

    # Find and load images
    images = []
    for prefix in clip_config["images"]:
        img_path = find_image(assets_dir, prefix)
        if img_path:
            img_array = prepare_image_for_video(img_path, VIDEO_WIDTH, VIDEO_HEIGHT)
            images.append(img_array)
            print(f"  🖼️  {prefix}: loaded")
        else:
            print(f"  ⚠️  {prefix}: not found")

    if not images:
        print(f"  ❌ No images found, skipping")
        return None

    # Calculate duration per image
    n_images = len(images)
    scene_duration = total_duration / n_images

    # Create clips with Ken Burns effect, alternating zoom direction
    video_clips = []
    for i, img in enumerate(images):
        if i % 2 == 0:
            # Zoom in
            clip = create_ken_burns_clip(img, scene_duration, 1.0, 1.12)
        else:
            # Zoom out
            clip = create_ken_burns_clip(img, scene_duration, 1.12, 1.0)

        # Add crossfade
        if i > 0:
            clip = clip.with_effects([vfx.CrossFadeIn(CROSSFADE_DURATION)])

        video_clips.append(clip)

    # Concatenate with crossfade
    final_video = concatenate_videoclips(video_clips, method="compose")

    # Add audio
    final_video = final_video.with_audio(audio)

    # Write video
    print(f"  📹 Rendering {output_file.name}...")
    final_video.write_videofile(
        str(output_file),
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        logger=None,
        threads=4,
        preset="fast"
    )

    size_mb = output_file.stat().st_size / (1024 * 1024)
    print(f"  ✅ {output_file.name} — {total_duration:.0f}s | {size_mb:.1f}MB")
    return total_duration


def main():
    base_dir = Path(__file__).parent.parent
    assets_dir = base_dir / ASSETS_DIR
    audio_dir = base_dir / AUDIO_DIR
    output_dir = base_dir / OUTPUT_DIR
    output_dir.mkdir(exist_ok=True)

    print("=" * 65)
    print("  🎬 VIDEO ASSEMBLY: Cartoon + Audio → MP4")
    print(f"  📁 Assets: {assets_dir}")
    print(f"  🎵 Audio:  {audio_dir}")
    print(f"  📹 Output: {output_dir}")
    print(f"  📐 Format: {VIDEO_WIDTH}x{VIDEO_HEIGHT} (9:16 vertical)")
    print("=" * 65)

    total_duration = 0
    success = 0

    for clip_config in CLIPS:
        dur = assemble_clip(clip_config, base_dir, assets_dir, audio_dir, output_dir)
        if dur:
            total_duration += dur
            success += 1

    m, s = int(total_duration // 60), int(total_duration % 60)
    print(f"\n{'='*65}")
    print(f"  🎬 DONE! {success}/10 videos assembled")
    print(f"  📁 Output: {output_dir}")
    print(f"  ⏱️  Total: {m}m{s:02d}s")
    print(f"  📐 Format: {VIDEO_WIDTH}x{VIDEO_HEIGHT} @ {FPS}fps")
    print(f"{'='*65}")


if __name__ == "__main__":
    main()
