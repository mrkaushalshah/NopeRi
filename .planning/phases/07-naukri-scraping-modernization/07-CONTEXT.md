# Phase 7: Naukri Scraping Modernization - Context

**Status:** Ready for planning

<domain>
## Phase Boundary
This phase modernizes the Naukri scraping and authentication pipeline by completely removing Selenium, geckodriver, and `get_Nkparam.py`. It integrates Crawlee for Python (`PlaywrightCrawler`) directly into `NaukriLoginClient` and `NaukriJobClient` to handle WAF resistance, session generation, and automated proxy/retry rotation.
</domain>

<decisions>
## Implementation Decisions

### 1. Remove Selenium Dependency
- Completely delete `get_Nkparam.py`.
- Remove Selenium and webdriver-manager from `requirements.txt`.
- Refactor `NaukriLoginClient` to authenticate and fetch `nkparam`, `appid`, and `systemid` using Crawlee's Playwright backend instead of a manual Selenium hack.

### 2. Crawlee Session Management
- Replace the current raw `requests` session in `NaukriJobClient` with Crawlee `PlaywrightCrawler` or `HttpCrawler` depending on JavaScript execution needs.
- Use Crawlee's `SessionPool` to automatically rotate sessions if Naukri returns a `403 Forbidden` or CAPTCHA challenge.

### 3. Asynchronous Modernization
- Convert any necessary blocking I/O calls related to job search and application inside `NaukriJobClient` to leverage Crawlee's native `async` functionality.
- Integrate seamlessly with the existing `main.py` asyncio event loop.
</decisions>

<canonical_refs>
## Canonical References
- `d:\Projects\NopeRi\src\client\naukri_client.py` - Core login logic.
- `d:\Projects\NopeRi\src\client\job_client.py` - Job search and apply logic.
- `d:\Projects\NopeRi\src\utils\get_Nkparam.py` - To be deleted.
- `d:\Projects\NopeRi\main.py` - Main loop.
</canonical_refs>
