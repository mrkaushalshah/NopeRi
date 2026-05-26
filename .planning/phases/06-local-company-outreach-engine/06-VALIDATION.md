---
phase: 6
slug: local-company-outreach-engine
date: 2026-05-26
---

# Phase 6 Validation Strategy

## Objective
Ensure the Local Company Outreach Engine accurately finds IT companies via Google Places, scrapes their websites for emails, scores them with AI, and stores them in SQLite while presenting a responsive Angular UI for manual email review.

## Dimensions of Validation

### Dimension 1: Schema & Data Integrity
- **Criteria**: SQLite database tables (`companies`, `outreach_emails`) must be created on startup with correct column types.
- **Verification**: Query SQLite schema via CLI. Data insertion must not trigger constraint errors.

### Dimension 2: API & Integration
- **Criteria**: Google Places API must be called correctly with location and radius.
- **Verification**: Use mock responses in tests to verify API payload construction.

### Dimension 3: Web Scraping Robustness
- **Criteria**: The crawler must find generic emails (`info@`, `careers@`) from standard HTML structures.
- **Verification**: Provide mock HTML pages with hidden and visible emails. Crawler must extract them.

### Dimension 4: AI Enrichment Accuracy
- **Criteria**: The AI classifier must correctly filter non-IT companies. Email generation must utilize profile and company domain context.
- **Verification**: Feed the AI known IT and non-IT company profiles and assert the scores.

### Dimension 5: Frontend Component Architecture
- **Criteria**: Angular components must follow the standard `ng generate component` structure. Tailwind CSS 3.4.3 must be used.
- **Verification**: Code review of `.ts`, `.html`, and `.css` files. Verify Tailwind classes are applied and UI renders properly.

### Dimension 6: End-to-End Workflow
- **Criteria**: Entering a location in the UI triggers the backend pipeline, updates the SQLite database, and displays the drafted email with a functioning "Copy to Clipboard" button.
- **Verification**: Run the full stack locally and test the entire flow manually.
