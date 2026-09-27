"""Ovozli xabar: shovqinni tozalash va matnga o'girish (Groq Whisper)."""

import asyncio
import logging
import tempfile
from pathlib import Path

from openai import AsyncOpenAI

from bot.config import settings

log = logging.getLogger(__name__)

client = AsyncOpenAI(
    api_key=settings.groq_api_key.get_secret_value(),
    base_url=settings.stt_base_url,
)

# Past chastotali g'uvillash va yuqori chastotali shitirlashni kesadi,
# fon shovqinini kamaytiradi va ovoz balandligini tekislaydi.
NOISE_FILTER = "highpass=f=90,lowpass=f=7600,afftdn=nr=18:nf=-30:tn=1,dynaudnorm=f=150:g=15"
FFMPEG_TIMEOUT = 120


async def _clean(source: Path, target: Path) -> Path:
    """Shovqinni tozalaydi. ffmpeg ishlamasa, asl faylni qaytaradi."""
    command = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(source),
        "-af", NOISE_FILTER,
        "-ac", "1", "-ar", "16000",
        str(target),
    ]
    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(process.communicate(), timeout=FFMPEG_TIMEOUT)
    except (FileNotFoundError, asyncio.TimeoutError) as error:
        log.warning("ffmpeg ishlamadi (%s), asl audio ishlatiladi", error)
        return source
    if process.returncode != 0:
        log.warning("ffmpeg xatosi, asl audio ishlatiladi: %s", stderr.decode(errors="ignore")[:300])
        return source
    return target


async def transcribe(audio: bytes, prompt: str = "", language: str = "") -> str:
    """Telegram ovozli xabarini matnga aylantiradi."""
    with tempfile.TemporaryDirectory() as folder:
        source = Path(folder) / "voice.ogg"
        source.write_bytes(audio)
        path = await _clean(source, Path(folder) / "clean.flac")

        options: dict = {"model": settings.stt_model, "temperature": 0}
        if language := language or settings.stt_language:
            options["language"] = language
        if prompt:
            options["prompt"] = prompt

        result = await client.audio.transcriptions.create(
            file=(path.name, path.read_bytes()),
            **options,
        )
    return result.text.strip()
