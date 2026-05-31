# Phase 7: Naukri Scraping Modernization - Research

## Context
Naukri uses strict Cloudflare/WAF anti-bot mechanisms. It specifically fingerprints the browser and tracks IP history.
Currently, `NaukriLoginClient` utilizes a brittle architecture:
1. It relies on extracting manual keys (`formKey2`, `nkparam`).
2. It historically used a separate `get_Nkparam.py` script that spun up Selenium just to get the `nkparam` and `appid` headers for authentication.
3. It then tries to use Python's `requests` library to make raw API calls.

This results in a disconnect: the bot solves Cloudflare/JS challenges in Selenium but makes requests in `requests`, making it incredibly easy for the WAF to detect and drop the session, leading to the complex `session_heartbeat()` retry logic in `main.py`.

## Proposed Architecture with Crawlee
Crawlee's `PlaywrightCrawler` (or `StagehandCrawler` if we use AI automation) is the perfect replacement.

1. **Unified Context**: Playwright natively manages the `BrowserContext`, cookies, and LocalStorage. Instead of manually extracting headers and tokens to pass to `requests`, we can just let `PlaywrightCrawler` load Naukri, log in natively via the UI (or API), and then issue all subsequent requests from within the same browser context.
2. **Fingerprint Stealth**: Crawlee's `fingerprint_suite` automatically spoofs canvas, WebGL, user-agent, and screen dimensions, preventing Cloudflare from detecting it as a bot.
3. **Automated Interception**: We can use Playwright's `page.route()` to intercept the `nkparam` and bearer tokens if we still want to make headless API calls, OR we can simply drive the UI (e.g. `page.click('button[name="Apply"]')`).
4. **SessionPool**: Crawlee can manage a pool of authenticated sessions. If a session is blocked or expires, Crawlee natively retires it, spins up a fresh fingerprint, and logs back in.

## Impact on `main.py`
`main.py` currently relies on a `job_search_loop` that yields to `asyncio.sleep()`. 
Since Crawlee natively integrates with `asyncio`, we can replace the custom polling loop with a Crawlee `RequestQueue`. 
Instead of tracking `pending_jobs` in a dictionary and checking pages manually, we can enqueue Naukri search URLs (`https://www.naukri.com/software-developer-jobs-in-pune?page=1`) into Crawlee. The crawler will process them concurrently, extract jobs, check the AI filter, and then handle applications all within the same managed crawler lifecycle.

## Implementation Steps for Planning
1. **Remove Legacy Code**: Delete `get_Nkparam.py` and strip Selenium out of `requirements.txt`.
2. **Refactor NaukriLoginClient**: Replace the `requests.Session` with a Crawlee `PlaywrightCrawler` instance or `BrowserContext` manager.
3. **Refactor NaukriJobClient**: Update `search_jobs` and `apply_job` to operate inside the `PlaywrightCrawler` request handler context, utilizing `context.page` or `context.send_request()` instead of raw `requests`.
4. **Update main.py**: Remove the manual `session_heartbeat()` since Crawlee's `SessionPool` handles rotation automatically.
