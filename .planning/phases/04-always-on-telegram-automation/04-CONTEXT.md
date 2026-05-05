# Phase 4: Always-On Telegram Automation - Context

**Gathered:** 2026-05-04
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase transitions the script from a manual, run-once terminal application into a continuous background automation system. It introduces a Telegram bot for asynchronous remote approval and decouples the job searching process from the job application process.
</domain>

<decisions>
## Implementation Decisions

### Execution Environment
- The script will remain running locally on the user's laptop.
- We will NOT use a cloud VPS to avoid Naukri flagging cloud IPs and triggering Recaptchas.

### The Search Loop
- Implement a continuous polling loop that runs the search every 5 to 10 minutes.
- This interval ensures the user is among the first applicants without triggering rate limits or anti-bot defenses.

### The Messaging Layer
- Use **Telegram** instead of Slack.
- Rely on Telegram's "Long Polling" architecture so no local tunnel (ngrok) is required.
- The bot will send a formatted message for each job that passes the AI filter, including the AI's score and reason.
- Include Inline Keyboards with two buttons: `[✅ Apply]` and `[❌ Skip]`.

### Asynchronous Decoupling
- The Job Search loop must NOT wait for the user to respond on Telegram.
- Jobs that pass the filter should be pushed to a queue (e.g., in-memory or lightweight SQLite/JSON).
- A background Thread/Task will handle listening for Telegram button clicks.
- If the user ignores their phone for 24 hours, the jobs will accumulate in the chat. When the user taps `[✅ Apply]`, the bot instantly pulls the job from the queue, applies to it, and updates the Telegram message.
</decisions>
