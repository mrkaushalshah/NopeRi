---
phase: "07"
plan: "07-PLAN.md"
subsystem: "Scraping"
tags: ["crawlee", "playwright", "naukri", "refactor", "windows", "bugfix"]
requires: []
provides: ["naukri_client", "job_client", "main_loop"]
affects: ["main.py", "naukri_client.py", "job_client.py"]
tech-stack.added: ["crawlee", "playwright"]
patterns: ["Playwright RequestContext", "Async/Await", "Windows ProactorEventLoop", "UTF-8 reconfiguration"]
key-files.modified: ["src/client/naukri_client.py", "src/client/job_client.py", "main.py"]
key-files.created: []
requirements-completed: []
duration: "45m"
completed: "2026-06-01"
---

# Phase 07 Plan 07-PLAN.md: Naukri Scraping Modernization Summary

## 1. What Was Completed
- **Cleaned Up Dependencies:** Removed `get_Nkparam.py`, `selenium`, and `webdriver-manager`. Added `crawlee` and `playwright`.
- **Refactored NaukriLoginClient:** Updated `NaukriLoginClient` to use Crawlee's `PlaywrightCrawler` to perform the login steps, successfully bypassing Akamai WAF. Once logged in, the `storage_state` and `nauk_at` cookies are extracted, and a persistent `BrowserContext` is initialized natively for subsequent API workflows.
- **Refactored NaukriJobClient:** Updated `NaukriJobClient` to use the authenticated Playwright `APIRequestContext` for all requests, eliminating the need to manually harvest and inject `nkparam`.
- **Streamlined main.py:** Removed `session_heartbeat()` as Playwright maintains the session inherently. Transitioned the synchronous codebase calls to asynchronous (`await`).

## 2. Key Decisions & Technical Choices
- **Crawlee PlaywrightCrawler for Login, Raw Playwright for Context:** While Crawlee handles WAF bypass brilliantly on the HTML login page, it closes browser contexts after the crawler completes. To share the authenticated session with the job client without re-authenticating constantly, we run a single Crawlee login request, extract the authenticated `storage_state`, and initialize a persistent raw Playwright context.
- **Windows Event Loop Adaptations:** Playwright spawns subprocesses, which requires the `WindowsProactorEventLoopPolicy` on Windows. We updated the event loop policy in `main.py` accordingly.
- **Console UTF-8 Encoding:** To prevent Windows cp1252 charmap encoding crashes when printing emojis or complex unicode job details to the console, we programmatically reconfigured `sys.stdout` and `sys.stderr` to use UTF-8 at startup.

## 3. Unexpected Findings or Challenges
- **Crawlee Import Structure:** In the latest Crawlee for Python, the modules are loaded under `crawlee.crawlers` rather than direct namespace shortcuts.
- **REST URL vs HTML page:** Bypassing WAF via Playwright requires navigating to the HTML login page (`https://www.naukri.com/nlogin/login`) rather than targeting the REST backend URL directly.

## 4. Next Steps
- Verify the bot's autonomous behavior under long run sessions.
