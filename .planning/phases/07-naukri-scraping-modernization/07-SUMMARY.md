---
phase: "07"
plan: "07-PLAN.md"
subsystem: "Scraping"
tags: ["crawlee", "playwright", "naukri", "refactor"]
requires: []
provides: ["naukri_client", "job_client", "main_loop"]
affects: ["main.py", "naukri_client.py", "job_client.py"]
tech-stack.added: ["crawlee", "playwright"]
patterns: ["Playwright RequestContext", "Async/Await"]
key-files.modified: ["src/client/naukri_client.py", "src/client/job_client.py", "main.py"]
key-files.created: []
requirements-completed: []
duration: "30m"
completed: "2026-06-01"
---

# Phase 07 Plan 07-PLAN.md: Naukri Scraping Modernization Summary

## 1. What Was Completed
- **Cleaned Up Dependencies:** Removed `get_Nkparam.py`, `selenium`, and `webdriver-manager`. Added `crawlee` and `playwright`.
- **Refactored NaukriLoginClient:** Updated `NaukriLoginClient` to use async Playwright to log in natively, extract `nauk_at`, and persist the `BrowserContext`.
- **Refactored NaukriJobClient:** Updated `NaukriJobClient` to use the authenticated Playwright `APIRequestContext` for all requests, eliminating the need to manually harvest and inject `nkparam`.
- **Streamlined main.py:** Removed `session_heartbeat()` as Playwright maintains the session inherently. Transitioned the synchronous codebase calls to asynchronous (`await`).

## 2. Key Decisions & Technical Choices
- **Raw Playwright vs Crawlee PlaywrightCrawler:** While the original plan requested `PlaywrightCrawler`, Crawlee inherently closes its contexts after crawling, making it ill-suited to serve as an ongoing HTTP client API wrapper for `NaukriJobClient`. A raw Playwright `BrowserContext` was initialized to keep the context persistent, satisfying the goal of bypassing WAF natively.
- **Asynchronous Main Loop:** Refactoring the internal API calls to rely on Playwright meant pushing `async/await` up the call stack, naturally converting `main.py` into a fully asynchronous Python script.

## 3. Unexpected Findings or Challenges
- **Synchronous to Asynchronous cascading:** Modifying `job_client.py` required converting almost all functions in the call stack to `async def`, leading to larger refactoring than expected.

## 4. Next Steps
- Verify the newly async Playwright bot in production to see if WAF blocks appear.
- The `ai_handler` might also benefit from fully async operations if it currently performs blocking network calls.
