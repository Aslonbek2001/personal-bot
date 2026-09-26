from pathlib import Path
from zoneinfo import ZoneInfo

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Telegram
    bot_token: SecretStr
    owner_id: int

    # Claude
    anthropic_api_key: SecretStr
    claude_model: str = "claude-sonnet-5"

    # Ovoz -> matn
    groq_api_key: SecretStr
    stt_base_url: str = "https://api.groq.com/openai/v1"
    stt_model: str = "whisper-large-v3"
    stt_language: str = "en"

    # Matn -> ovoz
    tts_model: str = "canopylabs/orpheus-v1-english"
    tts_voice: str = "troy"

    # Vaqt
    timezone: str = "Asia/Tashkent"
    lesson_hour: int = Field(default=5, ge=0, le=23)
    reminder_hour: int = Field(default=20, ge=0, le=23)
    review_day: str = "sun"
    review_hour: int = Field(default=11, ge=0, le=23)

    # Boshqa
    history_limit: int = 6
    data_dir: Path = Path("data")

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)

    @property
    def context_path(self) -> Path:
        return self.data_dir / "context.md"

    @property
    def topics_path(self) -> Path:
        return self.data_dir / "topics.md"

    @property
    def tech_path(self) -> Path:
        return self.data_dir / "tech.md"

    @property
    def process_path(self) -> Path:
        return self.data_dir / "process.md"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "bot.db"


settings = Settings()