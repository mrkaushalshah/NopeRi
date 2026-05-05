# Phase 4: Always-On Telegram Automation - Research

## Technical Approach

To implement a continuous background polling loop with a Telegram bot for asynchronous interaction, we need to restructure `main.py`.

### 1. The Async Architecture
Currently, `main.py` runs top-to-bottom. To support Telegram Long Polling AND a job search loop concurrently, we have two main architectural choices:
- **Threaded approach:** Use Python's `threading` module to run the Naukri search loop in one thread, and the Telegram bot in another.
- **Asyncio approach:** Use `asyncio` to run both concurrently. Since `python-telegram-bot` v20+ is heavily asyncio-based, this is the most robust approach.

**Recommendation:** Use `python-telegram-bot` and `asyncio`. The job search will run as an `asyncio.sleep` loop.

### 2. Telegram Bot Implementation
- **Library:** `python-telegram-bot` is the standard, actively maintained wrapper.
- **Long Polling:** `ApplicationBuilder().token("YOUR_TOKEN").build().run_polling()`
- **Inline Keyboards:** Use `InlineKeyboardMarkup` and `InlineKeyboardButton` for the `[Apply]` and `[Skip]` buttons.
- **Callback Queries:** Use a `CallbackQueryHandler` to listen for button taps. When a user taps a button, the callback payload will include `apply:JOB_ID` or `skip:JOB_ID`.

### 3. State Management & Decoupling
- We need a thread-safe or async-safe way to store jobs that passed the AI filter so the Telegram bot can access them when the user taps "Apply".
- A simple in-memory Python `dict` (`pending_jobs = {job_id: job_object}`) is sufficient since the script is long-running. If the script crashes, the queue is lost, but the next search loop will pick them up again (since they won't be in `applied_jobs.json`).

### 4. Rate Limiting and Anti-Bot Safeties
- **Naukri API Limits:** Searching every 10 minutes means 144 searches a day. This is generally safe if the user-agent and headers are properly formed.
- To prevent searching the exact same jobs and running them through the AI repeatedly, we must maintain a "seen jobs" cache or ensure we only process jobs that aren't in `applied_jobs.json` AND aren't currently in `pending_jobs`.

## Validation Architecture

1. **Bot Registration:** The user must provide a `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in `.env`.
2. **Loop Validation:** The search loop must not block the Telegram polling.
3. **Application Validation:** Tapping the `[Apply]` button must correctly retrieve the job from memory, call `jc.apply_job()`, and edit the Telegram message to display the result.

## RESEARCH COMPLETE
