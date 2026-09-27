"""callback_data klasslari. Hammasi 64 baytdan qisqa: nomlar emas, qisqa ID lar ishlatiladi."""

from aiogram.filters.callback_data import CallbackData


class MenuCb(CallbackData, prefix="m"):
    action: str  # home, lang, today, done, progress, mistakes, words, speak, noop


class ModeCb(CallbackData, prefix="mode"):
    mode: str  # chat, translate, task, standup, review


class SubjectCb(CallbackData, prefix="s"):
    id: str  # fan ildiz tugunining ID si


class KnowCb(CallbackData, prefix="k"):
    id: str  # tugun ID si (8 belgi)
    page: int = 0
