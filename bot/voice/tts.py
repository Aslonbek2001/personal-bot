"""Talaffuz: matn -> ovoz (Groq TTS) -> Telegram uchun OGG/Opus."""

import asyncio
import tempfile
from pathlib import Path

from bot.config import settings
from bot.voice.stt import FFMPEG_TIMEOUT, client


async def speak(text: str) -> bytes:
    """Matnni Telegram ovozli xabari uchun OGG/Opus ga aylantiradi."""
    response = await client.audio.speech.create(
        model=settings.tts_model,
        voice=settings.tts_voice,
        input=text,
        response_format="wav",
    )
    with tempfile.TemporaryDirectory() as folder:
        source = Path(folder) / "speech.wav"
        target = Path(folder) / "speech.ogg"
        source.write_bytes(response.content)
        process = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y", "-loglevel", "error", "-i", str(source),
            "-c:a", "libopus", "-b:a", "48k", str(target),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(process.communicate(), timeout=FFMPEG_TIMEOUT)
        if process.returncode != 0:
            raise RuntimeError(stderr.decode(errors="ignore")[:300])
        return target.read_bytes()
