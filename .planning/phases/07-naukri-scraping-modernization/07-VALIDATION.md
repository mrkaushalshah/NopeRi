# Phase 7: Naukri Scraping Modernization - Validation Strategy

## 1. Acceptance Criteria Verification
- [ ] `get_Nkparam.py` is deleted.
- [ ] `selenium` and `webdriver-manager` are removed from `requirements.txt`.
- [ ] `NaukriLoginClient` authenticates using Crawlee Playwright instead of manual `requests` POST.
- [ ] WAF resilience: `main.py` can fetch 5 pages of job searches concurrently without throwing a 403 Forbidden.
- [ ] `session_heartbeat()` is removed from `main.py` and session expiry is handled naturally.

## 2. Testing Constraints
- Tests should be run using `python main.py` directly.
- Monitor console logs for Crawlee `SessionPool` rotation if a block occurs.
