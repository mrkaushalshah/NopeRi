# Product Requirements Document: Phase 6 - Local Company Outreach Engine

## Objective
Build a reverse job search engine that identifies local IT companies around a specific location (e.g. Baner), extracts their emails from their websites, scores their fit, generates an AI-crafted outreach email, and presents the data in an Angular-based UI for manual sending.

## Key Features
1. **Location-Based Search (No Pincodes)**
   - Input: Location string (e.g. "Baner, Pune") and a radius (e.g. 10km).
   - Fetch local IT/Software companies using Google Places API.
   - Use an AI classifier to score if the Google Places result is actually an IT software product/services company and filter out noise (repair shops, institutes, etc.).

2. **Website & Email Scraping**
   - Assume every valid IT company has a website.
   - Crawl the website (specifically looking for `/careers`, `/jobs`, `/contact` or generic homepage links).
   - Extract ANY email found (e.g., `hr@`, `careers@`, `jobs@`, `info@`, etc.). 
   - **CONSTRAINT:** Strictly DO NOT use Hunter.io or any external email discovery APIs. Rely purely on web scraping the company's own site.

3. **AI Enrichment**
   - **Company Fit Score:** Score the company based on stack match, product vs services, and quality signals.
   - **Intelligence Card:** Compile all data (Name, Location, Website, Extracted Emails, Fit Score, Google Rating) into a unified profile.
   - **Email Generation:** Use AI (GPT-4o) to draft a highly personalized subject and email body referencing the candidate's profile and the company's domain.

4. **Storage & Tracking**
   - Store all data (companies, emails, drafted messages, pipeline status) in an **SQLite** database (replacing any JSON file approach).
   - Track outreach pipeline status (e.g. Discovered -> Website Found -> Email Found -> Drafted -> Sent manually).

5. **Frontend Application**
   - Framework: **Angular** (strictly following the Sparqal Systems standard: use `ng generate component` with separate `.ts`, `.html`, `.css` files).
   - Styling: **TailwindCSS 3.4.3**.
   - Functionality:
     - Search bar for Location and Radius.
     - Dashboard displaying the Company Intelligence Cards and pipeline metrics.
     - Display the AI-generated subject and body for each company.
     - **Manual Send Workflow:** NO auto-emailing. Provide a "Copy to Clipboard" button for the subject and body so the user can paste it into their own email client and send manually.

## Out of Scope
- Auto-sending emails.
- Hunter.io or external contact APIs.
- Pincode-based search (replaced with location string).
- LinkedIn scraping for this phase.

## Technical Stack constraints
- Python backend (integrating with the existing `NopeRi` project).
- SQLite Database.
- Angular + TailwindCSS 3.4.3 Frontend.
