# Phase 6: Local Company Outreach Engine - Technical Research

## 1. Domain & Strategy

**Goal:** Implement a local IT company outreach engine using Python (backend) and Angular + TailwindCSS (frontend), powered by Google Places API, web scraping, and OpenAI.

### Key Workflows
1. **Frontend to Backend:** User enters Location (e.g., "Baner, Pune") and Radius.
2. **Backend to Google Places:** Fetch IT companies.
3. **Backend Filter:** LLM scores companies to filter noise (repair shops, etc.).
4. **Scraping Pipeline:** Fetch company websites, crawl for generic emails (`info@`, `careers@`, etc.).
5. **AI Enrichment:** Score fit and draft outreach emails.
6. **Storage:** Save to SQLite.
7. **Frontend Display:** Show dashboard, pipeline status, and provide "Copy to Clipboard" for manual email sending.

## 2. Technical Dependencies & Integration

### Backend (Python)
- **Google Places API:** Use `requests` to call Google Maps Nearby Search API. Need to configure API keys.
- **Web Crawling:** `crawlee` (`crawlee-python`) to handle concurrency, parsing, and anti-bot measures. The crawler will target `mailto:` links and use regex to match emails on contact/career pages.
- **SQLite:** Standard Python `sqlite3` module. Need schema for `companies` and `outreach_pipelines`.
- **OpenAI:** Re-use the existing `AIHandler` from `src/utils/ai_handler.py`.
- **API Framework:** `FastAPI` to expose the backend to the Angular frontend.

### Frontend (Angular + Tailwind)
- **Framework:** Angular (strictly using `ng generate component`).
- **CSS:** TailwindCSS v3.4.3 setup (`npm install -D tailwindcss@3.4.3 postcss autoprefixer`).
- **Components:** Dashboard, CompanyCard, SearchBar.

## 3. Data Model (SQLite)
- **`companies` table:** id, name, location, website, google_rating, fit_score, intelligence_card_json, status, created_at.
- **`outreach_emails` table:** id, company_id, extracted_emails, email_subject, email_body, sent_status.

## 4. API Endpoints Needed
- `GET /api/search?location={loc}&radius={rad}`: Trigger pipeline and stream/poll results.
- `GET /api/companies`: Fetch stored companies.
- `PUT /api/companies/{id}/status`: Update pipeline status (e.g., "Sent manually").

## 5. Security & Validation
- **Validation Architecture:** Unit tests for web scraper (mocking HTML). Unit tests for Google Places parser.
- **Threat Model:** Ensure web scraping avoids SSRF vulnerabilities (e.g. don't parse internal IPs).
- Schema push: SQLite schema migrations or simple `CREATE TABLE IF NOT EXISTS` at startup.

## 6. Known Challenges
- **Web scraping robustness:** Career pages differ wildly. A recursive crawler with a depth of 1 (homepage -> contact/careers) is optimal to avoid long runtimes.
- **Google Places Rate Limits/Costs:** Keep requests localized.

## Validation Architecture (Nyquist)
- Dimensions: Schema verification, API integration, Mocked Scrape, UI render test.
