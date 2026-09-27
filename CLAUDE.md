# Ustoz bot

Personal Telegram mentor, used only by its owner. It sends a daily English grammar lesson,
runs a practice chat that corrects my English, accepts voice messages, and explains a
Programming knowledge tree (backend, RAG, ML). Russian is planned as a second language.

## Stack
Python 3.12, uv, aiogram 3, APScheduler 3, Anthropic SDK (`messages.parse` with Pydantic
schemas), Groq Whisper through the `openai` client, ffmpeg, Pillow, Docker Compose.

## Commands
- Run locally: `uv run python -m bot.main` (stop Docker first: only one polling instance may run)
- Tests: `uv run pytest`
- Docker: `docker compose up -d --build`, logs: `docker compose logs -f`
- Reload content without restart: send `/reload` to the bot (owner only)

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
- Claude output is always structured (`messages.parse` + Pydantic). Claude writes `**bold**` only;
  HTML is produced by `bot/ui/format.py`.
- System prompt order: `shared/style.md` -> subject `prompt.md` -> `profile.md` (stable, cached) -> mode task.
- Tech explanations never contain code.
- Owner-only (`OWNER_ID`) and private chats only.
- `callback_data` must stay under 64 bytes: use stable node IDs, never names.
- Never edit `.env` or files in `data/`. Never print or log secrets.
- Keep files under ~250 lines. Add or update tests with every logic change.

## Structure
- `bot/content/` — loads `content/` into memory: subjects, grammar blocks, knowledge tree, stable node IDs, `/reload`.
- `bot/services/` — SQLite (`data/bot.db`): progress and today's topic, lesson cache and daily words, answers and mistakes. No aiogram.
- `bot/ai/` — Claude: Pydantic schemas, system prompt builder (style -> subject -> profile -> task), request calls.
- `bot/voice/` — ffmpeg noise filter + Groq Whisper (`stt.py`), Groq TTS (`tts.py`).
- `bot/ui/` — Telegram presentation: HTML formatting, Uzbek texts, keyboards, callback data, lesson card.
- `bot/handlers/` — aiogram routers (start/menu, language, knowledge, chat, voice), scheduled jobs, FSM storage; owner + private filters in `__init__.py`.