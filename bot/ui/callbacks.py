"""callback_data klasslari. Hammasi 64 baytdan qisqa: nomlar emas, qisqa ID va kodlar ishlatiladi."""

from aiogram.filters.callback_data import CallbackData


class MenuCb(CallbackData, prefix="m"):
    action: str  # home, noop, speak


class LangCb(CallbackData, prefix="l"):
    action: str  # menu, grammar, writing, today, mistakes, words, progress
    lang: str  # subject.toml dagi code: en, ru


class ModeCb(CallbackData, prefix="md"):
    mode: str  # chat, translate, task, standup, review
    lang: str


class DoneCb(CallbackData, prefix="d"):
    lang: str
    topic: str  # mavzu matnining 8 belgili xeshi


class SubjectCb(CallbackData, prefix="s"):
    id: str  # fan ildiz tugunining ID si


class KnowCb(CallbackData, prefix="k"):
    id: str  # tugun ID si (8 belgi)
    page: int = 0
