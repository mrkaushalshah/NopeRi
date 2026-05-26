---
wave: 1
depends_on: []
files_modified:
  - src/utils/dbhandler.py
  - src/client/local_outreach.py
  - src/api/app.py
  - ui/
autonomous: false
---

# Phase 6: Local Company Outreach Engine - Plan

## Goal
Build a reverse job search engine using location-based Google Places search, web scraping for emails, and AI outreach generation, with an Angular/Tailwind UI for manual review and sending.

## Requirements Covered
- Location-Based Search
- Website & Email Scraping (No Hunter.io)
- AI Enrichment (Company Fit Score, Intelligence Card, Email Generation)
- Storage & Tracking (SQLite)
- Frontend Application (Angular + TailwindCSS 3.4.3)

---

## Task 1: SQLite Database Setup & Models
<read_first>
- `d:\Projects\NopeRi\.planning\phases\06-local-company-outreach-engine\06-CONTEXT.md`
- `d:\Projects\NopeRi\src\utils\dbhandler.py` (if exists, or new)
</read_first>
<action>
Create or update `src/utils/dbhandler.py` to initialize an SQLite database for the outreach engine.
Implement a class `OutreachDB` with the following methods:
1. `init_db()`: Executes `CREATE TABLE IF NOT EXISTS companies (id TEXT PRIMARY KEY, name TEXT, location TEXT, website TEXT, google_rating REAL, fit_score INTEGER, intelligence_card_json TEXT, status TEXT, created_at TIMESTAMP)` and `CREATE TABLE IF NOT EXISTS outreach_emails (id TEXT PRIMARY KEY, company_id TEXT, extracted_emails TEXT, email_subject TEXT, email_body TEXT, sent_status TEXT)`.
2. `save_company(company_dict)` and `get_companies()`.
3. `update_company_status(company_id, status)`.
Run `init_db()` upon instantiation.
</action>
<acceptance_criteria>
- `python -c "from src.utils.dbhandler import OutreachDB; db=OutreachDB();"` runs without errors and creates an SQLite DB file.
- SQLite database contains `companies` and `outreach_emails` tables.
</acceptance_criteria>

## Task 2: Google Places & Scraper Integration
<read_first>
- `d:\Projects\NopeRi\src\client\local_outreach.py`
</read_first>
<action>
Create `src/client/local_outreach.py`.
Implement a `LocalOutreachClient` class:
1. `search_companies(location: str, radius: int)`: Calls Google Places Nearby Search API with keyword "IT software company".
2. `extract_website_emails(url: str)`: Uses `requests` and `BeautifulSoup` to fetch the homepage. Looks for `mailto:` links or regex matches for emails (`[\w\.-]+@[\w\.-]+`). Checks up to 1 level deep for `/contact`, `/careers`, or `/jobs` if emails aren't found on the homepage.
</action>
<acceptance_criteria>
- `src/client/local_outreach.py` contains `LocalOutreachClient` with `search_companies` and `extract_website_emails` methods.
- Method `extract_website_emails` uses regex `[\w\.-]+@[\w\.-]+` to find emails.
</acceptance_criteria>

## Task 3: AI Enrichment Integration
<read_first>
- `d:\Projects\NopeRi\src\utils\ai_handler.py`
- `d:\Projects\NopeRi\src\client\local_outreach.py`
</read_first>
<action>
Update `src/client/local_outreach.py` to integrate with `AIHandler`.
Implement `enrich_company_data(company_data, emails)`:
1. Calls `AIHandler` to determine if the company is a legitimate software company (filtering out noise).
2. Generates a `fit_score` based on location, website snippet, and name.
3. If fit score > 50, calls `AIHandler` to draft a highly personalized email subject and body using the user's resume data and the company context.
Returns the enriched data ready for database insertion.
</action>
<acceptance_criteria>
- `src/client/local_outreach.py` contains `enrich_company_data` method.
- The method utilizes `AIHandler` for classification and email drafting.
</acceptance_criteria>

## Task 4: FastAPI Backend Setup
<read_first>
- `d:\Projects\NopeRi\src\api\app.py`
</read_first>
<action>
Create `src/api/app.py` using FastAPI.
1. `GET /api/search`: Accepts `location` and `radius`. Instantiates `LocalOutreachClient`, fetches companies, enriches them, saves to `OutreachDB`, and returns the results.
2. `GET /api/companies`: Returns all stored companies from `OutreachDB`.
3. `PUT /api/companies/{id}/status`: Updates the status of a company (e.g., "Drafted" to "Sent manually").
Configure CORS to allow Angular frontend (localhost:4200).
</action>
<acceptance_criteria>
- `src/api/app.py` exposes `/api/search`, `/api/companies`, and `/api/companies/{id}/status` endpoints.
- FastAPI app can be started using `uvicorn src.api.app:app`.
</acceptance_criteria>

## Task 5: Angular UI Initialization
<read_first>
- `d:\Projects\NopeRi\ui\package.json`
</read_first>
<action>
In the terminal, run `npx @angular/cli new ui --routing=false --style=css --skip-tests --defaults` inside `d:\Projects\NopeRi`.
Navigate to `ui/` and run `npm install -D tailwindcss@3.4.3 postcss autoprefixer`.
Initialize Tailwind using `npx tailwindcss init`.
Configure `tailwind.config.js` to scan `src/**/*.{html,ts}`.
Add Tailwind directives `@tailwind base; @tailwind components; @tailwind utilities;` to `ui/src/styles.css`.
</action>
<acceptance_criteria>
- `ui/tailwind.config.js` exists and includes `content: ["./src/**/*.{html,ts}"]`.
- `ui/src/styles.css` contains Tailwind directives.
</acceptance_criteria>

## Task 6: Angular Components Implementation
<read_first>
- `d:\Projects\NopeRi\ui\src\app\app.component.html`
- `d:\Projects\NopeRi\.planning\phases\06-local-company-outreach-engine\06-UI-SPEC.md`
</read_first>
<action>
Inside `ui/`, use `ng generate component dashboard` and `ng generate component company-card`.
1. **Dashboard (`src/app/dashboard`)**: Implement a search bar (location, radius), an API service call to `GET /api/search`, and display funnel metrics. Iterate over companies to render `<app-company-card>`.
2. **Company Card (`src/app/company-card`)**: Display company name, location, website, fit score, and extracted emails. Include the AI-generated subject and body. Add a "Copy to Clipboard" button (using JavaScript `navigator.clipboard.writeText`) for both fields.
Update `app.component.html` to render `<app-dashboard>`.
</action>
<acceptance_criteria>
- `ui/src/app/dashboard/dashboard.component.ts` and `.html` exist.
- `ui/src/app/company-card/company-card.component.ts` and `.html` exist.
- `company-card.component.html` contains elements with click handlers for copying text.
</acceptance_criteria>

---

## Verification
- Run backend (`uvicorn src.api.app:app`) and frontend (`ng serve`).
- Enter "Baner, Pune" in the UI. Ensure Google Places API returns results.
- Verify the SQLite database populates with scraped emails and AI-generated drafts.
- Ensure clicking "Copy to Clipboard" in the UI copies the respective text.
