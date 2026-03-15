#!/usr/bin/env python3
"""
=============================================================================
  VEO 3.1 AI VIDEO: Clip 04 — "300 Resumes, 1 Afternoon"
  Google AI Studio / Gemini API — Realistic, Canadian context
=============================================================================
  Generates 4 x 8-second AI video segments using Veo 3.1,
  then concatenates with ffmpeg into a ~32 second clip.

  USAGE:
    python3 scripts/generate_veo_clip04.py

  OUTPUT: ./videos_veo/bob_veo_04_resumes.mp4
=============================================================================
"""

import os, sys, time
from pathlib import Path

FFMPEG_PATH = str(Path(__file__).parent / "ffmpeg")

try:
    from google import genai
    from google.genai import types
except ImportError:
    print("ERROR: pip3 install google-genai")
    sys.exit(1)

# ─── Config ─────────────────────────────────────────────────────────────────
API_KEY = "AIzaSyC3-lN8UIt0fCz2XGm9taXopUDHJYLL7F4"
MODEL = "veo-3.1-generate-preview"
OUTPUT_DIR = "videos_veo"
ASPECT_RATIO = "9:16"      # Vertical for social media
DURATION_SECS = 8           # Max per segment

# ─── 4 Realistic Scenes — Canadian Office ──────────────────────────────────
# Cinematic, realistic prompts with Canadian context

SCENES = [
    {
        "name": "scene1_resume_overload",
        "prompt": (
            "Realistic cinematic shot, warm indoor lighting. "
            "A stressed Canadian HR manager in her mid-30s at a modern Montreal office desk "
            "with floor-to-ceiling windows showing the city skyline. "
            "She stares at her laptop overwhelmed as hundreds of printed resumes and CVs "
            "are stacked impossibly high on her desk, some falling off. "
            "She rubs her temples in frustration. Coffee cup beside her. "
            "Natural color grading, shallow depth of field. "
            "Ambient office sounds, keyboard clicking, paper rustling, a quiet sigh."
        )
    },
    {
        "name": "scene2_bob_takes_over",
        "prompt": (
            "Realistic cinematic shot, warm golden lighting. "
            "A confident friendly man in a colorful Hawaiian shirt walks into a clean modern "
            "Canadian startup office. He sits down at a laptop with a knowing smile. "
            "His fingers start rapidly typing. The screen glows with data and charts. "
            "He radiates competence and calm energy. Shallow depth of field. "
            "Sound of confident typing, a subtle upbeat electronic hum."
        )
    },
    {
        "name": "scene3_ai_sorting",
        "prompt": (
            "Realistic close-up cinematic shot. "
            "A laptop screen in a Montreal office showing a sleek dashboard interface. "
            "Resume profiles scroll rapidly with green checkmark and red X icons appearing. "
            "A ranking list auto-populates with top candidate names and scores. "
            "The Hawaiian-shirt man watches from behind the screen, nodding approvingly. "
            "Blue screen light reflects on his face. "
            "Digital UI sounds, subtle satisfying click sounds for each sorted resume."
        )
    },
    {
        "name": "scene4_perfect_hire",
        "prompt": (
            "Realistic cinematic shot, warm natural light from large windows. "
            "In a bright modern Canadian boardroom, the HR manager shakes hands warmly "
            "with a confident young professional who just got hired. Both are smiling. "
            "In the background through glass walls, the man in the Hawaiian shirt "
            "gives a subtle proud thumbs up and walks away casually. "
            "The desk is clean with just a laptop and a single printed offer letter. "
            "Montreal skyline visible through the windows. Golden hour lighting. "
            "Cheerful ambient music, handshake sound, subtle celebratory tone."
        )
    },
]


def generate_scene(client, scene, output_dir):
    """Generate one 8-second video segment via Veo 3.1."""
    name = scene["name"]
    prompt = scene["prompt"]
    output_path = output_dir / f"{name}.mp4"

    print(f"\n  🎬 Generating: {name}")
    print(f"     Prompt: {prompt[:100]}...")

    try:
        operation = client.models.generate_videos(
            model=MODEL,
            prompt=prompt,
            config=types.GenerateVideosConfig(
                aspect_ratio=ASPECT_RATIO,
                duration_seconds=DURATION_SECS,
                person_generation="allow_all",
            ),
        )

        # Poll until done
        poll_count = 0
        while not operation.done:
            poll_count += 1
            elapsed = poll_count * 15
            m, s = divmod(elapsed, 60)
            print(f"     ⏳ Generating... {m}m{s:02d}s")
            time.sleep(15)
            operation = client.operations.get(operation)

        # Download the video
        generated_video = operation.response.generated_videos[0]
        client.files.download(file=generated_video.video)
        generated_video.video.save(str(output_path))

        size_mb = output_path.stat().st_size / (1024 * 1024)
        print(f"  ✅ {name}.mp4 — {size_mb:.1f}MB")
        return output_path

    except Exception as e:
        print(f"  ❌ Error: {e}")
        return None


def concatenate_videos(scene_paths, output_path):
    """Concatenate multiple video files using ffmpeg."""
    list_file = output_path.parent / "concat_list.txt"
    with open(list_file, 'w') as f:
        for p in scene_paths:
            f.write(f"file '{p}'\n")

    import subprocess
    # Re-encode to ensure consistent format for concat
    cmd = [
        FFMPEG_PATH, "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(list_file),
        "-c:v", "libx264",
        "-preset", "fast",
        "-c:a", "aac",
        "-b:a", "192k",
        str(output_path)
    ]

    print(f"\n  🔧 Concatenating {len(scene_paths)} scenes...")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        size_mb = output_path.stat().st_size / (1024 * 1024)
        print(f"  ✅ Final: {output_path.name} — {size_mb:.1f}MB")
    else:
        print(f"  ❌ ffmpeg error: {result.stderr[:300]}")

    list_file.unlink(missing_ok=True)


def main():
    client = genai.Client(api_key=API_KEY)

    output_dir = Path(__file__).parent.parent / OUTPUT_DIR
    output_dir.mkdir(exist_ok=True)

    print("=" * 65)
    print("  🎬 VEO 3.1 — Realistic AI Video Generation")
    print(f"  Model: {MODEL}")
    print(f"  Clip: 300 Resumes, 1 Afternoon")
    print(f"  Format: {ASPECT_RATIO} vertical | {DURATION_SECS}s per scene")
    print(f"  Scenes: {len(SCENES)} (total ~32s)")
    print(f"  Style: Realistic, Canadian context (Montreal)")
    print("=" * 65)

    scene_paths = []
    for i, scene in enumerate(SCENES, 1):
        print(f"\n  {'─'*55}")
        print(f"  Scene {i}/{len(SCENES)}")
        print(f"  {'─'*55}")

        path = generate_scene(client, scene, output_dir)
        if path:
            scene_paths.append(path)
        else:
            print(f"  ⚠️  Scene {i} failed, continuing...")

    if scene_paths:
        final_path = output_dir / "bob_veo_04_resumes.mp4"
        concatenate_videos(scene_paths, final_path)
    else:
        print("\n  ❌ No scenes were generated")

    print(f"\n{'='*65}")
    print(f"  🎬 Done! {len(scene_paths)}/{len(SCENES)} scenes generated")
    print(f"  📁 Output: {output_dir}/")
    print(f"{'='*65}")


if __name__ == "__main__":
    main()
