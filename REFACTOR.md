# Refactor plan

Decision (confirmed by owner): keep every current feature (SQLite `data/bot.db`, all practice
modes, mistakes, words, TTS, evening summary, weekly review). Only the structure changes.

1. `tools/convert_content.py`: `data/context.md|topics.md|tech.md` -> `content/` (profile, shared style, subjects), verify counts 32 / 6 / 47 / 188.
2. `bot/content/`: `models.py` + `loader.py` — subjects from `subject.toml`, grammar blocks, knowledge tree of any depth, stable 8-char node IDs, `/reload`.
3. `bot/services/`: `db.py` (SQLite), `progress.py` (done topics, today's topic), `lessons.py` (lesson cache, daily words), `journal.py` (answers, mistakes, stats). No aiogram.
4. `bot/ai/`: `schemas.py` (Pydantic), `prompts.py` (style -> subject prompt -> profile, cached -> mode task), `client.py` (calls).
5. `bot/voice/`: `stt.py` (ffmpeg + Whisper), `tts.py` (speech).
6. `bot/ui/`: `format.py`, `texts.py` (all Uzbek strings, name "Ustoz"), `callbacks.py`, `keyboards.py`, `card.py`.
7. `bot/handlers/`: `start` (main menu from subjects, /reload), `language`, `knowledge` (tree, breadcrumb, 8 per page), `chat`, `voice`, `scheduled`, plus FSM storage; owner + private filters on every router.
8. Tests: format, split_text, progress, mark_done once per day, loader, callback_data < 64 bytes; offline smoke test with a fake Telegram session.
9. Docker: `ustoz-bot`, `content/` mounted read-only; `.env.example`, README, CLAUDE.md "Structure".
10. Delete `data/*.md` sources only after the conversion is verified; final report.
