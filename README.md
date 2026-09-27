# Ustoz

Personal Telegram mentor for one owner (`OWNER_ID`), private chat only.

- **English**: a daily lesson at `LESSON_HOUR` (image card, grammar, mini story, 20 words),
  practice chat with corrections, translation, work writing, stand-up (voice), mistakes review,
  daily words, progress, pronunciation, evening summary and weekly review.
- **Programming**: a knowledge tree (backend, ML, RAG). Pick a subsection to get a
  6-part explanation without code, then chat about it in English.

## Run

```bash
cp .env.example .env            # fill BOT_TOKEN, OWNER_ID, ANTHROPIC_API_KEY, GROQ_API_KEY
uv run python -m bot.main       # local (stop Docker first: one polling instance per token)
docker compose up -d --build    # server, see DEPLOY.md
uv run pytest                   # tests, offline
```

## Folders

- `content/` — everything the bot teaches and every prompt. Edited by hand, tracked in git,
  mounted read-only into the container.
- `data/` — runtime state only (`bot.db`: progress, lessons, words, mistakes, chat state). Not in git.
- `bot/` — code. `tests/` — pytest. `tools/` — one-time content converter.

After editing `content/`, send `/reload` to the bot. No restart and no code change needed.
If the new content has an error, the bot keeps the old version and shows the error.

## Content rules

- A `NN_` prefix on a file or folder sets its order and is never shown. Files and folders
  without a prefix come after the numbered ones, sorted by name.
- Button IDs come from the path without prefixes, so renumbering files is safe.
  Renaming a file, folder or line gives it a new ID: old buttons for it just say the list changed.
- A folder's title comes from `_index.md` (`# Title`). Without it the folder name is used,
  title-cased and without the prefix (`01_react` -> `React`).

### Add a grammar topic

Add a `- topic` line to a file in `content/english/grammar/`. Topics are taught in file order,
then line order. Do not rename a topic after it is done: progress is saved by the exact text.

A new block is a new file, for example `06_meetings.md`:

```markdown
# Meetings

- Agreeing and disagreeing politely - discussing a design in a meeting
```

### Add a knowledge topic or subsection

One file is one topic; each `- ` line is a subsection:

```
content/programming/frontend/01_react/01_hooks.md
```
```markdown
# Hooks

- useState and re-rendering
- useEffect and cleanup
```

Folders are groups and can be nested to any depth. The folder that holds a topic file is the
"section" Claude sees (above: `React`). Lists longer than 8 items get ◀️ ▶️ pages.

### Add a direction

A direction is a folder inside a knowledge subject, for example `content/programming/frontend/`.
Add `_index.md` with `# Frontend` if the folder name is not the title you want.

### Add a subject

Create `content/<name>/subject.toml` and `content/<name>/prompt.md`:

```toml
title = "System design"
icon = "🏗"
type = "knowledge"      # knowledge: a tree like Programming
order = 3               # position in the main menu
```

A `knowledge` subject shows up in the main menu with its tree. The system prompt is always
`shared/style.md` -> the subject's `prompt.md` -> `profile.md` -> the current task.
The daily lesson uses the `type = "language"` subject with `scheduled = true` and its
`grammar/` folder (English today). A second language subject needs code changes, see `docs/ROADMAP.md`.
