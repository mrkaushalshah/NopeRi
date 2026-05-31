---
wave: 1
depends_on: []
files_modified:
  - requirements.txt
  - src/client/naukri_client.py
  - src/client/job_client.py
  - main.py
autonomous: false
---

# Phase 7: Naukri Scraping Modernization - Plan

## Goal
Modernize the Naukri scraping architecture by replacing brittle Selenium/Requests logic with Crawlee for Python (`PlaywrightCrawler`), improving WAF resistance and eliminating manual session management hacks.

## Task 1: Clean Up Legacy Dependencies
<read_first>
- `requirements.txt`
- `d:\Projects\NopeRi\src\utils\get_Nkparam.py`
</read_first>
<action>
1. Delete the file `src/utils/get_Nkparam.py` entirely, as its Selenium-based functionality is obsolete.
2. Remove `selenium`, `webdriver-manager`, and any associated legacy browser driver dependencies from `requirements.txt`.
3. Ensure `crawlee` and `playwright` are present in `requirements.txt`.
</action>
<acceptance_criteria>
- `src/utils/get_Nkparam.py` does not exist in the repository.
- `requirements.txt` no longer contains `selenium` or `webdriver-manager`.
- `requirements.txt` contains `crawlee`.
</acceptance_criteria>

## Task 2: Refactor NaukriLoginClient
<read_first>
- `d:\Projects\NopeRi\src\client\naukri_client.py`
</read_first>
<action>
Refactor `NaukriLoginClient` in `src/client/naukri_client.py` to use `PlaywrightCrawler` from Crawlee.
1. Remove references to `get_Nkparam.py`, `formKey2`, and manual header extraction logic (`extract_form_key2`).
2. Replace `_login_request` with a Crawlee automation script that launches a `PlaywrightCrawler`, navigates to the Naukri login page natively, fills in the username and password using `page.fill()`, and clicks the login button.
3. Automatically intercept the authentication tokens (`nauk_at` cookies and `Bearer` tokens) from the `BrowserContext` after a successful login.
4. Store the resulting authenticated `BrowserContext` or Crawlee `Session` in `self.naukri_session` for reuse by the job client.
</action>
<acceptance_criteria>
- `NaukriLoginClient` no longer calls functions from `get_Nkparam.py`.
- `login()` successfully utilizes Crawlee Playwright to authenticate and obtain the `nauk_at` cookie.
- Code avoids manual `requests.post(LOGIN_URL)` in favor of driving the browser context.
</acceptance_criteria>

## Task 3: Refactor NaukriJobClient
<read_first>
- `d:\Projects\NopeRi\src\client\job_client.py`
- `d:\Projects\NopeRi\src\client\naukri_client.py`
</read_first>
<action>
Refactor `NaukriJobClient` in `src/client/job_client.py` to execute its API calls through the authenticated Crawlee context.
1. Modify `search_jobs` to use the Crawlee context (`page.request.get` or `context.send_request`) to fetch job listings, carrying over the authenticated browser fingerprints and cookies natively.
2. Modify `apply_job` and questionnaire logic to do the same.
3. Ensure that if a `403` or WAF challenge is encountered, the client raises an appropriate error to trigger Crawlee's native Session retry mechanics (if applicable) or handles the exception cleanly.
</action>
<acceptance_criteria>
- `NaukriJobClient` executes API requests (`search_jobs`, `apply_job`) through the Playwright request context instead of a raw `requests` session.
- Headers are managed by Crawlee's context natively, avoiding manual `nkparam` injection.
</acceptance_criteria>

## Task 4: Streamline Main Event Loop
<read_first>
- `d:\Projects\NopeRi\main.py`
</read_first>
<action>
Update `main.py` to fully embrace the new Crawlee-driven lifecycle.
1. Remove the `session_heartbeat()` function completely. Crawlee's context handles session validity and rotation, so manual "touching" of the API is unnecessary.
2. Remove the `asyncio.create_task(session_heartbeat())` startup line.
3. Simplify the `try/except NaukriAuthError` blocks inside `button_callback` and `job_search_loop`. Let the Crawlee context handle automatic retries where possible, or just rely on a single clean re-login hook provided by the refactored `NaukriLoginClient`.
</action>
<acceptance_criteria>
- `main.py` no longer contains the `session_heartbeat()` function.
- The job search loop runs without manual 10-minute heartbeat polling.
- The script initializes `NaukriLoginClient` using Crawlee gracefully at startup.
</acceptance_criteria>
