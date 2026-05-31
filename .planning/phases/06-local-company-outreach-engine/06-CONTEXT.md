# Phase 6: Local Company Outreach Engine - Context

**Gathered:** 2026-05-26
**Status:** Ready for planning
**Source:** PRD Express Path (d:\Projects\NopeRi\scratch\phase6-prd.md)

<domain>
## Phase Boundary

Build a reverse job search engine that identifies local IT companies around a specific location (e.g. Baner), extracts their emails from their websites, scores their fit, generates an AI-crafted outreach email, and presents the data in an Angular-based UI for manual sending.
</domain>

<decisions>
## Implementation Decisions

### Core Functionality
- **Location-Based Search (No Pincodes):** Input Location string (e.g. "Baner, Pune") and a radius (e.g. 10km). Fetch local IT/Software companies using Google Places API. Use an AI classifier to score if the Google Places result is actually an IT software product/services company and filter out noise.
- **Website & Email Scraping:** Assume every valid IT company has a website. Crawl the website (specifically looking for `/careers`, `/jobs`, `/contact` or generic homepage links) using Crawlee for Python (`crawlee-python`). Extract ANY email found (e.g., `hr@`, `careers@`, `jobs@`, `info@`, etc.). Strictly DO NOT use Hunter.io or any external email discovery APIs. Rely purely on web scraping the company's own site via Crawlee.
- **AI Enrichment:** Score the company fit. Compile all data into an Intelligence Card. Use AI (GPT-4o/mini) to draft a highly personalized subject and email body referencing the candidate's profile and the company's domain.
- **Storage & Tracking:** Store all data (companies, emails, drafted messages, pipeline status) in an SQLite database (replacing any JSON file approach). Track outreach pipeline status (e.g. Discovered -> Website Found -> Email Found -> Drafted -> Sent manually).
- **Frontend Application:** Framework: Angular (strictly following the Sparqal Systems standard: use `ng generate component` with separate `.ts`, `.html`, `.css` files). Styling: TailwindCSS 3.4.3. Provide a Dashboard displaying the Company Intelligence Cards and pipeline metrics. Provide a "Copy to Clipboard" button for the subject and body for manual sending.

### the agent's Discretion
- Database schema design (SQLite).
- Internal AI prompts for company fit scoring and email generation.
- Specific layout and component breakdown of the Angular dashboard.
- Internal mechanics of the web crawler to extract emails robustly.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Architecture
- `d:\Projects\NopeRi\README.md` — Core project setup and API references.
- `d:\Projects\NopeRi\src\client\jop_classifier.py` — Existing AI filtering pipeline to align the company fit scoring.

</canonical_refs>

<specifics>
## Specific Ideas

- Manual Send Workflow: NO auto-emailing. The system only provides AI-generated drafts.
- Ensure strict compliance with Sparqal Systems standard for Angular (`ng generate component`).

</specifics>

<deferred>
## Deferred Ideas

- Auto-sending emails.
- Pincode-based search.
- LinkedIn scraping for this phase.

</deferred>

---

*Phase: 06-local-company-outreach-engine*
*Context gathered: 2026-05-26 via PRD Express Path*
