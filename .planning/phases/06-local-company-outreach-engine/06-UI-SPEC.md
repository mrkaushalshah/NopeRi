# Phase 6: Local Company Outreach Engine - UI Design Contract

## 1. Design Language & Framework
- **Framework:** Angular. Component structure must be `ng generate component` standard (separate `.ts`, `.html`, `.css`).
- **Styling:** TailwindCSS 3.4.3.
- **Brand Context:** Consistent with existing Sparqal Systems standards (sleek, professional, modern).

## 2. Core Screens & Components

### 2.1 Outreach Dashboard (Main View)
- **Search Bar Section:**
  - Input: Location text field (e.g. "Baner, Pune").
  - Input: Radius dropdown/number field (e.g. 5km, 10km, 20km).
  - Button: "Find & Analyze Companies" (Trigger API).
  
- **Pipeline Metric Cards (Top row):**
  - Displays funnel metrics (Discovered → Websites Found → Emails Scraped → Outreach Ready).

- **Company Intelligence List:**
  - A scrollable list/grid of `CompanyCard` components.

### 2.2 Company Card Component (`<app-company-card>`)
- **Header:** Company Name, Location (Distance), Google Rating.
- **Sub-header:** Website link, Extracted Emails list, Fit Score (Color-coded: >80 Green, 50-79 Yellow, <50 Red).
- **Outreach Section:**
  - AI Subject Line with "Copy to Clipboard" button.
  - AI Email Body with "Copy to Clipboard" button.
- **Footer:** Status tracking dropdown or toggle (e.g. "Drafted" -> "Sent manually").

## 3. Visual Specifications (Tailwind 3.4.3)
- **Colors:** Slate/Gray backgrounds (`bg-slate-50`), crisp white cards (`bg-white`), Indigo/Blue primary actions (`text-indigo-600`, `bg-blue-600`).
- **Typography:** Inter or system-sans fonts.
- **Interactions:** Hover states on buttons and cards (`hover:shadow-lg`).

## 4. Angular Architecture constraints
- Separate UI concerns into smart and dumb components (e.g., Dashboard is the smart container; Company Card is dumb presentational).
- Utilize Angular Services for all API calls to the Python backend.
