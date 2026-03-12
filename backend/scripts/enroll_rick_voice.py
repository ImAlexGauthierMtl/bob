"""One-time script to enroll the 'Rick' custom voice on DashScope (Qwen TTS VC).

Run once:
    cd backend && source venv/bin/activate
    python scripts/enroll_rick_voice.py --audio /tmp/rick_ref.wav

The voice_id returned is bound to cosyvoice-v2 to be used via DashScope TTS VC.
Then copy the returned voice_id into .env as RICK_VOICE_ID=<id>
"""

import argparse
import os
import sys

import dashscope


def load_api_key() -> str:
    """Load DashScope API key from env or .env file."""
    api_key = os.environ.get("DASHSCOPE_API_KEY") or os.environ.get("DASHSCOPE_KEY")
    if not api_key:
        from pathlib import Path
        env_file = Path(__file__).parent.parent / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.startswith("DASHSCOPE_API_KEY="):
                    api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    if not api_key:
        print("ERROR: DASHSCOPE_API_KEY not found in environment or .env")
        sys.exit(1)
    return api_key


def upload_audio(audio_path: str, api_key: str) -> str:
    """Upload audio to DashScope Files API and return the file URL."""
    print(f"Uploading {audio_path} to DashScope Files API...")
    dashscope.api_key = api_key

    response = dashscope.Files.upload(file_path=audio_path, purpose="inference")

    print(f"Upload response: {response}")

    # Extract URL from response
    if hasattr(response, "url"):
        return response.url
    elif hasattr(response, "id"):
        # Some versions return a file ID — build the URL
        file_id = response.id
        return f"fileid://{file_id}"
    elif isinstance(response, dict):
        return response.get("url") or response.get("id") or str(response)
    else:
        raise RuntimeError(f"Unexpected upload response: {response}")


def enroll_voice(audio_url: str, api_key: str, target_model: str) -> str:
    """Enroll voice using the DashScope VoiceEnrollmentService SDK."""
    from dashscope.audio.tts_v2.enrollment import VoiceEnrollmentService

    print(f"Enrolling voice with URL: {audio_url}")
    print(f"Target model: {target_model}")

    service = VoiceEnrollmentService(api_key=api_key)
    voice_id = service.create_voice(
        target_model=target_model,
        prefix="rick",
        url=audio_url,
        language_hints=["fr"],
    )
    return voice_id


def main():
    parser = argparse.ArgumentParser(description="Enroll Rick custom voice on DashScope")
    parser.add_argument(
        "--audio",
        default="/tmp/rick_ref.wav",
        help="Path to WAV reference audio (mono, 24kHz, 10-20s)",
    )
    parser.add_argument(
        "--target-model",
        default="cosyvoice-v2",
        help="DashScope TTS model for this voice (cosyvoice-v2 or cosyvoice-v3-flash)",
    )
    parser.add_argument(
        "--skip-upload",
        help="Skip upload and use this URL directly (if you already have one)",
    )
    args = parser.parse_args()

    if not os.path.isfile(args.audio) and not args.skip_upload:
        print(f"ERROR: Audio file not found: {args.audio}")
        sys.exit(1)

    api_key = load_api_key()

    # Step 1: Upload audio to DashScope Files
    if args.skip_upload:
        audio_url = args.skip_upload
        print(f"Using provided URL: {audio_url}")
    else:
        audio_url = upload_audio(args.audio, api_key)
        print(f"Audio uploaded: {audio_url}")

    # Step 2: Enroll the voice
    voice_id = enroll_voice(audio_url, api_key, args.target_model)

    print("\n" + "=" * 55)
    print(f"✅ Voice 'Rick' enrolled successfully!")
    print(f"   voice_id  = {voice_id}")
    print(f"   model     = {args.target_model}")
    print("=" * 55)
    print("\nAdd this to your backend/.env file:")
    print(f"RICK_VOICE_ID={voice_id}")
    print("\nNote: Use this voice with DashScope CosyVoice TTS,")
    print("not with qwen3-tts-flash (different API).")


if __name__ == "__main__":
    main()
