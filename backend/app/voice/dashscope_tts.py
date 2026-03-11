"""DashScope (Alibaba Cloud) TTS service for Pipecat.

Streams audio from Qwen3-TTS-Flash via the DashScope REST API.
Qwen3-TTS supports 10 languages including English, French, Spanish,
Portuguese, German, Japanese, Korean, Russian, Italian, and Chinese.

Audio format: Each SSE chunk arrives as a WAV container (44-byte RIFF header
+ PCM 16-bit mono). The header is stripped and the real sample rate is read
from it so Pipecat resamples correctly.

Voice cloning: When ref_audio_path is provided (e.g. for the 'Rick' voice),
the audio file is encoded as base64 and passed as ref_audio on each TTS call
(zero-shot cloning, no persistent enrollment needed).
"""

import base64
import json
import os
import re
from typing import AsyncGenerator

import aiohttp
import structlog
from pipecat.frames.frames import (
    ErrorFrame,
    Frame,
    TTSAudioRawFrame,
    TTSStartedFrame,
    TTSStoppedFrame,
)
from pipecat.services.tts_service import TTSService

logger = structlog.get_logger(__name__)

DASHSCOPE_INTL_URL = (
    "https://dashscope-intl.aliyuncs.com/api/v1"
    "/services/aigc/multimodal-generation/generation"
)

LANGUAGE_MAP = {
    "en": "English",
    "fr": "French",
    "fr-FR": "French",
    "fr-CA": "French",
    "es": "Spanish",
    "pt": "Portuguese",
    "auto": "Auto",
}

DASHSCOPE_SAMPLE_RATE = 24000

_THINK_TAG_RE = re.compile(r"<think>.*?</think>\s*", flags=re.DOTALL)


class DashScopeTTSService(TTSService):
    """Pipecat TTS service backed by Alibaba Cloud DashScope Qwen3-TTS.

    Supports built-in voices (Cherry, Ethan, Jennifer, Ryan, Katerina, Elias)
    and custom cloned voices via ref_audio_path (e.g. "Rick").
    When ref_audio_path is set, the audio file is base64-encoded and passed
    as ref_audio on every TTS call for zero-shot voice cloning.
    """

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "qwen3-tts-instruct-flash",
        voice: str = "Cherry",
        language: str = "en",
        instructions: str = "",
        ref_audio_path: str = "",
        ref_text: str = "",
        speed: float = 1.0,
        **kwargs,
    ):
        super().__init__(
            sample_rate=DASHSCOPE_SAMPLE_RATE,
            push_stop_frames=False,
            **kwargs,
        )
        self._api_key = api_key
        self._model = model
        self._voice = voice
        self._language_code = language
        self._language = LANGUAGE_MAP.get(language, "Auto")
        self._instructions = instructions
        self._ref_text = ref_text
        self._speed = max(0.5, min(2.0, speed))  # clamp to DashScope range
        self._session: aiohttp.ClientSession | None = None
        # Voice cloning via ref_audio
        self._ref_audio_b64: str = ""
        if ref_audio_path and os.path.isfile(ref_audio_path):
            with open(ref_audio_path, "rb") as f:
                self._ref_audio_b64 = base64.b64encode(f.read()).decode("utf-8")
            logger.info(
                "dashscope_tts_ref_audio_loaded",
                path=ref_audio_path,
                size_kb=os.path.getsize(ref_audio_path) // 1024,
            )
        elif ref_audio_path:
            logger.warning("dashscope_tts_ref_audio_not_found", path=ref_audio_path)

    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    def can_generate_metrics(self) -> bool:
        return True

    async def run_tts(self, text: str, context_id: str) -> AsyncGenerator[Frame, None]:
        """Synthesize text via DashScope streaming API and yield audio frames."""
        text = _THINK_TAG_RE.sub("", text).strip()
        if not text:
            yield TTSStoppedFrame(context_id=context_id)
            return
        yield TTSStartedFrame(context_id=context_id)
        await self.start_ttfb_metrics()

        session = await self._ensure_session()
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "X-DashScope-SSE": "enable",
        }
        input_params: dict = {
            "text": text,
            "voice": self._voice,
            "language_type": self._language,
            "speed": self._speed,
        }
        if self._ref_audio_b64:
            input_params["ref_audio"] = self._ref_audio_b64
            if self._ref_text:
                input_params["ref_text"] = self._ref_text
        # BENCHMARK RESULTS (2026-03-11):
        # instruct-flash + ref_audio WITHOUT instructions = 82s TTFB (!)
        # instruct-flash + ref_audio WITH instructions    = 3.1s TTFB
        # → instructions MUST be sent even with ref_audio on instruct model
        # optimize_instructions=True adds ~6s — keep disabled
        if self._instructions:
            input_params["instructions"] = self._instructions
        payload = {
            "model": self._model,
            "input": input_params,
        }

        measuring_ttfb = True

        try:
            logger.debug(
                "dashscope_tts_request",
                voice=self._voice,
                has_ref_audio=bool(self._ref_audio_b64),
                text_len=len(text),
            )
            async with session.post(
                DASHSCOPE_INTL_URL,
                headers=headers,
                json=payload,
            ) as resp:
                logger.debug("dashscope_tts_response", status=resp.status, content_type=resp.content_type)
                if resp.status != 200:
                    body = await resp.text()
                    logger.error("dashscope_tts_error", status=resp.status, body=body[:500])
                    yield ErrorFrame(error=f"DashScope TTS error: {resp.status}")
                    yield TTSStoppedFrame(context_id=context_id)
                    return

                content_type = resp.content_type or ""

                if "text/event-stream" in content_type:
                    chunk_count = 0
                    async for frame in self._parse_sse(resp, context_id):
                        if measuring_ttfb:
                            await self.stop_ttfb_metrics()
                            measuring_ttfb = False
                        if hasattr(frame, 'audio'):
                            chunk_count += 1
                        yield frame
                    logger.debug("dashscope_tts_sse_done", audio_chunks=chunk_count)

                else:
                    body = await resp.json()
                    audio_data = body.get("output", {}).get("audio", {}).get("data")
                    if audio_data:
                        if measuring_ttfb:
                            await self.stop_ttfb_metrics()
                            measuring_ttfb = False
                        raw = base64.b64decode(audio_data)
                        if raw[:4] == b"RIFF" and len(raw) >= 44:
                            actual_sr = int.from_bytes(raw[24:28], "little")
                            pcm = raw[44:]
                        else:
                            pcm = raw
                            actual_sr = DASHSCOPE_SAMPLE_RATE
                        if pcm:
                            yield TTSAudioRawFrame(
                                audio=pcm,
                                sample_rate=actual_sr,
                                num_channels=1,
                                context_id=context_id,
                            )

        except Exception as e:
            logger.error("dashscope_tts_exception", error=str(e))
            yield ErrorFrame(error=f"DashScope TTS exception: {e}")

        yield TTSStoppedFrame(context_id=context_id)

    async def _parse_sse(self, resp: aiohttp.ClientResponse, context_id: str) -> AsyncGenerator[Frame, None]:
        """Parse Server-Sent Events stream from DashScope."""
        buffer = ""
        chunk_count = 0
        total_pcm_bytes = 0
        async for line_bytes in resp.content:
            line = line_bytes.decode("utf-8", errors="replace")
            buffer += line

            while "\n" in buffer:
                raw_line, buffer = buffer.split("\n", 1)
                raw_line = raw_line.strip()

                if not raw_line or raw_line.startswith(":"):
                    continue

                if raw_line.startswith("data:"):
                    data_str = raw_line[5:].strip()
                    if data_str == "[DONE]":
                        return

                    try:
                        data = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue

                    audio_obj = data.get("output", {}).get("audio", {})
                    audio_b64 = audio_obj.get("data")
                    if audio_b64:
                        raw = base64.b64decode(audio_b64)
                        chunk_count += 1
                        total_pcm_bytes += len(raw)

                        # DashScope wraps each SSE chunk in a WAV container.
                        # Strip the 44-byte RIFF/WAV header to get raw PCM.
                        if raw[:4] == b"RIFF" and len(raw) >= 44:
                            actual_sr = int.from_bytes(raw[24:28], "little")
                            pcm = raw[44:]
                        else:
                            pcm = raw
                            actual_sr = DASHSCOPE_SAMPLE_RATE

                        if pcm:
                            yield TTSAudioRawFrame(
                                audio=pcm,
                                sample_rate=actual_sr,
                                num_channels=1,
                                context_id=context_id,
                            )

    async def cleanup(self):
        if self._session and not self._session.closed:
            await self._session.close()
        await super().cleanup()
