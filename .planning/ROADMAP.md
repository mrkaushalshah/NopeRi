# Roadmap - NopeRi AI Integration

## Milestone 1: AI Foundation & Intelligence
**Goal**: Establish AI connectivity and resume-based intelligence.

- [x] **Phase 1: AI Service & Profile Extraction**
  - Implement `AIHandler` for OpenAI-compatible API.
  - Implement resume reading and structured profile extraction.
  - Verification: AI returns correct JSON profile from `resume.txt`.

- [x] **Phase 2: Questionnaire Solver Implementation**
  - Update `NaukriJobClient` to handle questionnaires using AI.
  - Implement prompt engineering for accurate HR answers.
  - Verification: Script correctly answers sample questionnaires without skipping.

- [x] **Phase 3: Integration & Production Loop**
  - Integrate AI solver into `main.py` application loop.
  - Add error handling and fallback for complex questions.
  - Verification: 100% application rate for search results.

- [ ] **Phase 4: Always-On Telegram Automation**
  - Implement a continuous background polling loop (every 5-10 minutes).
  - Implement a Telegram Bot using long polling to send job alerts.
  - Implement inline interactive buttons (`[Apply]`, `[Skip]`) decoupled from search.
  - Verification: Bot runs 24/7 without blocking and applies on button tap.

- [ ] **Phase 5: Enhanced Search Engine**
  - Implement multi-query iteration (looping through multiple keywords/locations).
  - Implement pagination handling to fetch all recent jobs instead of just the first 20.
  - Ensure correct sorting logic to retrieve the newest jobs first.
  - Verification: Search loop processes multiple pages across different queries effectively.

- [ ] **Phase 7: Naukri Scraping Modernization**
  - Replace Selenium-based nkparam extraction with Crawlee (PlaywrightCrawler).
  - Implement automated session management, retries, and browser fingerprinting to resist anti-bot systems.
  - Verification: `NaukriLoginClient` authenticates correctly without Selenium, and `main.py` searches/applies successfully under WAF pressure.

## Next Milestones

## Phase Details

### Phase 1: AI Service & Profile Extraction
- Implement `AIHandler` for OpenAI-compatible API.
- Implement resume reading and structured profile extraction.
- Verification: AI returns correct JSON profile from `resume.txt`.

### Phase 2: Questionnaire Solver Implementation
- Update `NaukriJobClient` to handle questionnaires using AI.
- Implement prompt engineering for accurate HR answers.

### Phase 5: Enhanced Search Engine
- Update job search to use a configurable list of keywords and locations.
- Implement multi-page retrieval to get all newly posted jobs instead of top 20.
- Update Naukri API call sorting parameter to fetch newest jobs first.
- Verification: Script correctly answers sample questionnaires without skipping.

### Phase 3: Integration & Production Loop
- Integrate AI solver into `main.py` application loop.
- Add error handling and fallback for complex questions.
- Verification: 100% application rate for search results.

### Phase 4: Always-On Telegram Automation
- Implement a continuous background polling loop (every 5-10 minutes).
- Implement a Telegram Bot using long polling to send job alerts.
- Implement inline interactive buttons (`[Apply]`, `[Skip]`) decoupled from search.
- Verification: Bot runs 24/7 without blocking and applies on button tap.

### Phase 6: Local Company Outreach Engine
- Create an Angular UI (with Tailwind CSS 3.4.3) to enter a location (e.g., Baner, Pune) and radius.
- Use Google Places API to find IT/Software companies and AI classifier to filter out noise.
- Assume all target companies have websites and crawl them (career/contact pages) for any emails (careers, hr, jobs, info). Do not use Hunter.io.
- Generate Company Intelligence Card and Company Fit Score using GPT-4o-mini/GPT-4o.
- Generate custom outreach subject and body. Save to SQLite database with pipeline status tracking.
- Display in the UI for manual review, with "Copy to Clipboard" buttons for the email subject and body. No auto-email functionality.

### Phase 06.1: Outreach Pipeline Optimization (INSERTED)

**Goal:** [Urgent work - to be planned]
**Requirements**: TBD
**Depends on:** Phase 6
**Plans:** 0 plans

Plans:
- [ ] TBD (run /gsd-plan-phase 06.1 to break down)

### Phase 7: Naukri Scraping Modernization
- Complete overhaul of `NaukriLoginClient` and `NaukriJobClient` to use `PlaywrightCrawler` from Crawlee.
- Completely remove Selenium, geckodriver, and `get_Nkparam.py`.
- Introduce Crawlee `SessionPool` to manage IP/Token rotation and WAF challenges automatically.
- Verification: `NaukriLoginClient` authenticates correctly without Selenium, and `main.py` searches/applies successfully under WAF pressure.
