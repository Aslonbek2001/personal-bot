"""Router'lar: faqat egasi (OWNER_ID) va faqat shaxsiy chat."""

from aiogram import F, Router

from bot.config import settings
from bot.handlers import chat, knowledge, language, practice, start, voice


def build_router() -> Router:
    """Bitta ildiz router: filtrlar ichidagi barcha router'larga ham ishlaydi. Bir marta chaqiriladi."""
    root = Router(name="owner")
    root.message.filter(F.from_user.id == settings.owner_id, F.chat.type == "private")
    root.callback_query.filter(F.from_user.id == settings.owner_id, F.message.chat.type == "private")
    root.include_routers(
        start.router, language.router, practice.router, knowledge.router, voice.router, chat.router, start.fallback,
    )
    return root
