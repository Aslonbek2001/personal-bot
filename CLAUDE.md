# Ustoz bot

Personal Telegram mentor, used only by its owner.
- English: daily grammar lesson (card + grammar + story + 20 words), practice chat with
  mistake correction, writing modes (translate, work writing, stand-up, review),
  mistakes list, daily words, voice messages and TTS.
- Russian: the same language menu and modes, vocabulary focus (A2), everyday writing and
  speaking situations, no TTS.
- Scheduled jobs (only for `scheduled = true` languages, i.e. English): morning lesson,
  evening summary, weekly review.
- Programming: a knowledge tree (backend, RAG, ML) explained by Claude without code.
- Russian is planned as a second language.

## Stack
Python 3.12, uv, aiogram 3, APScheduler 3, SQLite (`data/bot.db`), Anthropic SDK
(`messages.parse` with Pydantic schemas), Groq Whisper and Groq TTS through the `openai`
client, ffmpeg, Pillow, Docker Compose.

## Commands
- Run locally: `uv run python -m bot.main` (stop Docker first: only one polling instance may run)
- Tests: `uv run pytest`
- Docker: `docker compose up -d --build`, logs: `docker compose logs -f`
- Reload content without restart: send `/reload` to the bot (owner only)
- Back up the database: `sqlite3 data/bot.db ".backup data/bot.db.bak"`

## Layout
- `content/` — all learning content and prompts. Git-tracked, edited by hand, mounted read-only.
- `data/` — runtime state only (`bot.db`: progress, lessons, words, mistakes, FSM). Never committed, never edited by code changes.
- `bot/` — code. See "Structure" below.
- `tests/` — pytest tests for logic that runs without AI.
- `docs/ROADMAP.md` — future ideas. Implement only when explicitly asked.

## Rules
- Layers: handlers -> services / content / ai / voice. Only `bot/handlers/` and `bot/ui/` import aiogram.
- New topics, directions or subjects are added in `content/`, never in code.
- The bot's name is "Ustoz". All user-facing text is Uzbek and lives in `bot/ui/texts.py`.
- Claude output is always structured (`messages.parse` + Pydantic). Claude uses only the markup
  defined in the prompts (**bold**, *italic*, `code`); HTML is produced only by `bot/ui/format.py`.
- System prompt order: `shared/style.md` -> subject `prompt.md` -> `profile.md` (stable, cached) -> mode task.
- Tech explanations never contain code.
- Owner-only (`OWNER_ID`) and private chats only.
- `callback_data` must stay under 64 bytes: use stable node IDs, never names.
- Database schema changes are additive and go through a migration; never drop or rename
  columns that hold existing progress. Tell me to back up `bot.db` before any schema change.
- Never edit `.env` or files in `data/`. Never print or log secrets.
- Keep files under ~250 lines (`bot/ui/texts.py` is the exception). Add or update tests with every logic change.

## Structure
- `bot/content/` — loads `content/` into memory: subjects, grammar blocks, knowledge tree, stable node IDs, `/reload`.
- `bot/services/` — SQLite (`data/bot.db`): progress and today's topic, lesson cache and daily words, answers and mistakes. No aiogram.
- `bot/ai/` — Claude: Pydantic schemas, system prompt builder (style -> subject -> profile -> task), request calls.
- `bot/voice/` — ffmpeg noise filter + Groq Whisper (`stt.py`), Groq TTS (`tts.py`).
- `bot/ui/` — Telegram presentation: HTML formatting, Uzbek texts, keyboards, callback data, lesson card.
- `bot/handlers/` — aiogram routers (start/menu, language, practice, knowledge, chat, voice), scheduled jobs, FSM storage; owner + private filters in `__init__.py`.