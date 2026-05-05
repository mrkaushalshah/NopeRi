---
wave: 1
depends_on: []
files_modified:
  - requirements.txt
  - .env
  - main.py
autonomous: true
---

# Phase 4: Always-On Telegram Automation - Plan

## 1. Setup Dependencies and Environment
**Description:** Add the `python-telegram-bot` dependency and update the environment file to include Telegram tokens.
**Action:**
- Add `python-telegram-bot` to `requirements.txt`.
- Add placeholders for `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` to the `.env` format (you can just modify the instructions or let the user add them to their local `.env`).

<read_first>
- requirements.txt
- .env
</read_first>

<acceptance_criteria>
- `requirements.txt` contains `python-telegram-bot`
- The system gracefully handles missing Telegram tokens by warning the user.
</acceptance_criteria>

## 2. Refactor main.py to asyncio Architecture
**Description:** Convert the core execution loop in `main.py` into an `async` application to allow Telegram long polling to run concurrently with the job search loop.
**Action:**
- Import `asyncio` and `python-telegram-bot` components (`ApplicationBuilder`, `CommandHandler`, `CallbackQueryHandler`).
- Create an asynchronous function `job_search_loop()` that contains the logic from the current `main.py` execution block.
- Enclose the `jc.search_jobs` and `filter_pipeline.run` calls in a `while True:` loop inside `job_search_loop()` with an `await asyncio.sleep(600)` (10 minutes) at the end of the loop.
- Extract the setup logic (Login, AIHandler initialization, JobClient initialization) into a setup block that runs before the loops.

<read_first>
- main.py
</read_first>

<acceptance_criteria>
- `main.py` uses `asyncio` to run the search loop.
- The search loop delays for 10 minutes between iterations using `await asyncio.sleep(600)`.
</acceptance_criteria>

## 3. Implement the Telegram Bot and Job Queue
**Description:** Create a Telegram bot application that runs concurrently with the search loop and handles user interactions.
**Action:**
- Define a global in-memory dictionary `pending_jobs = {}` to store jobs that passed the AI filter.
- In `job_search_loop()`, instead of printing to the terminal and asking for `(y/n)`, add the successful jobs to `pending_jobs`.
- After adding a job to `pending_jobs`, use the Telegram bot instance to send a message to `TELEGRAM_CHAT_ID` containing:
  - Title, Company, Salary, Experience, Location.
  - AI Score and AI Reason.
  - An `InlineKeyboardMarkup` with two buttons: `[✅ Apply]` (callback data: `apply:{job_id}`) and `[❌ Skip]` (callback data: `skip:{job_id}`).
- Define a `button_callback(update, context)` async function that handles `CallbackQueryHandler`.
- If callback data starts with `apply:`, retrieve the job from `pending_jobs`, run the existing apply logic (including the AI questionnaire solver), and edit the message to `✅ Applied!`.
- If callback data starts with `skip:`, edit the message to `❌ Skipped`.
- Remove the job from `pending_jobs` in both cases.

<read_first>
- main.py
</read_first>

<acceptance_criteria>
- `pending_jobs` dictionary is used to decouple searching from applying.
- Telegram message contains `InlineKeyboardMarkup` with Apply/Skip buttons.
- `button_callback` edits the message to reflect the user's choice.
- Clicking apply triggers `jc.apply_job()` or `handle_ai_questionnaire_and_apply()`.
</acceptance_criteria>
