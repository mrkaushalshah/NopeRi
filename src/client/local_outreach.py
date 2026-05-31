import os
import re
import json
import uuid
import asyncio
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from dotenv import load_dotenv

load_dotenv()


class LocalOutreachClient:
    """
    Discovers IT companies near a given location using Google Places API,
    scrapes their websites for contact emails, and enriches them with AI
    scoring and personalized outreach drafts.
    """

    GOOGLE_GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
    GOOGLE_PLACES_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    GOOGLE_PLACE_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"

    SEARCH_QUERIES = [
        "software company",
        "IT services",
        "tech company",
        "software development",
        "IT company",
    ]

    CAREER_PATHS = [
        "/careers", "/career", "/jobs", "/job-openings",
        "/join-us", "/join-our-team", "/work-with-us",
        "/hiring", "/openings", "/contact", "/contact-us",
        "/about/careers", "/about/contact",
    ]

    EMAIL_REGEX = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')

    # Noise emails to filter out (images, CSS, placeholders)
    NOISE_PATTERNS = [
        r'.*\.(png|jpg|jpeg|gif|svg|webp|css|js)$',
        r'^(example|test|noreply|no-reply|mailer-daemon)@',
        r'.*@(example\.com|test\.com|sentry\.io|wixpress\.com)',
    ]

    def __init__(self, api_key=None, ai_handler=None):
        self.api_key = api_key or os.getenv("GOOGLE_MAPS_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_MAPS_API_KEY not found. Set it in .env or pass it directly.")
        self.ai_handler = ai_handler
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

    # ─── GEOCODE ────────────────────────────────────────────────
    def geocode_location(self, location_str: str) -> dict:
        """Convert a location string (e.g. 'Baner, Pune') to lat/lng."""
        res = requests.get(self.GOOGLE_GEOCODE_URL, params={
            "address": location_str,
            "key": self.api_key
        })
        data = res.json()
        if data.get("status") != "OK" or not data.get("results"):
            raise ValueError(f"Geocoding failed for '{location_str}': {data.get('status')}")
        loc = data["results"][0]["geometry"]["location"]
        return {"lat": loc["lat"], "lng": loc["lng"]}

    # ─── GOOGLE PLACES SEARCH ──────────────────────────────────
    def search_companies(self, location: str, radius: int = 10) -> list[dict]:
        """
        Search for IT/Software companies near a location string.
        Returns a list of raw company dicts with name, address, website, rating, etc.
        """
        coords = self.geocode_location(location)
        radius_meters = radius * 1000
        all_places = {}

        for query in self.SEARCH_QUERIES:
            params = {
                "location": f"{coords['lat']},{coords['lng']}",
                "radius": radius_meters,
                "keyword": query,
                "type": "establishment",
                "key": self.api_key,
            }
            res = requests.get(self.GOOGLE_PLACES_URL, params=params)
            data = res.json()

            if data.get("status") not in ("OK", "ZERO_RESULTS"):
                print(f"  [PLACES API] Warning: {data.get('status')} for query '{query}'")
                continue

            for place in data.get("results", []):
                pid = place.get("place_id")
                if pid and pid not in all_places:
                    all_places[pid] = {
                        "id": str(uuid.uuid4()),
                        "name": place.get("name", ""),
                        "address": place.get("vicinity", ""),
                        "location": location,
                        "google_rating": place.get("rating"),
                        "google_place_id": pid,
                        "types": place.get("types", []),
                        "lat": place["geometry"]["location"]["lat"],
                        "lng": place["geometry"]["location"]["lng"],
                    }

            # Handle pagination (next_page_token)
            next_token = data.get("next_page_token")
            if next_token:
                import time
                time.sleep(2)  # Google requires delay before using next_page_token
                params["pagetoken"] = next_token
                del params["keyword"]
                res2 = requests.get(self.GOOGLE_PLACES_URL, params=params)
                data2 = res2.json()
                for place in data2.get("results", []):
                    pid = place.get("place_id")
                    if pid and pid not in all_places:
                        all_places[pid] = {
                            "id": str(uuid.uuid4()),
                            "name": place.get("name", ""),
                            "address": place.get("vicinity", ""),
                            "location": location,
                            "google_rating": place.get("rating"),
                            "google_place_id": pid,
                            "types": place.get("types", []),
                            "lat": place["geometry"]["location"]["lat"],
                            "lng": place["geometry"]["location"]["lng"],
                        }

        companies = list(all_places.values())
        print(f"  [PLACES] Found {len(companies)} unique companies for '{location}'")
        return companies

    def _get_place_details(self, place_id: str) -> dict:
        """Get place details including website."""
        res = requests.get(self.GOOGLE_PLACE_DETAILS_URL, params={
            "place_id": place_id,
            "fields": "website,formatted_phone_number,formatted_address",
            "key": self.api_key,
        })
        data = res.json()
        if data.get("status") == "OK":
            return data.get("result", {})
        return {}

    # ─── EMAIL SCRAPING ─────────────────────────────────────────
    def extract_website_emails(self, url: str) -> list[str]:
        """
        Scrape a company website for email addresses using a lightweight synchronous BFS.
        Strategy:
          1. Scrape homepage for emails.
          2. If none found, discover and enqueue links that look like career/contact pages.
        Returns a deduplicated list of valid emails.
        """
        if not url:
            return []

        if not url.startswith("http"):
            url = "https://" + url

        all_emails = set()
        visited = set()
        queue = [url]
        max_pages = 8

        while queue and len(visited) < max_pages:
            current_url = queue.pop(0)
            if current_url in visited:
                continue
                
            visited.add(current_url)
            
            try:
                res = self.session.get(current_url, timeout=10)
                if not res.ok:
                    continue
            except requests.RequestException:
                continue

            soup = BeautifulSoup(res.text, "html.parser")
            
            # 1. Extract from mailto: links
            for mailto in soup.select('a[href^="mailto:"]'):
                email = mailto["href"].replace("mailto:", "").split("?")[0].strip()
                if self.EMAIL_REGEX.match(email):
                    all_emails.add(email.lower())

            # 2. Extract and decode Cloudflare-obfuscated emails (data attributes and protection links)
            for tag in soup.select('[data-cfemail]'):
                hex_str = tag.get("data-cfemail", "")
                decoded = self._decode_cloudflare_email(hex_str)
                if decoded and self.EMAIL_REGEX.match(decoded):
                    all_emails.add(decoded.lower())

            for link in soup.select('a[href*="/cdn-cgi/l/email-protection"]'):
                href = link.get("href", "")
                parts = href.split("#")
                if len(parts) > 1:
                    hex_str = parts[1]
                    decoded = self._decode_cloudflare_email(hex_str)
                    if decoded and self.EMAIL_REGEX.match(decoded):
                        all_emails.add(decoded.lower())

            # 3. Extract from raw text
            text_emails = self.EMAIL_REGEX.findall(res.text)
            for email in text_emails:
                all_emails.add(email.lower())
                
            # If we don't have enough emails and we are on the homepage, enqueue deeper pages
            is_homepage = current_url.rstrip("/") == url.rstrip("/")
            if len(all_emails) < 3 and is_homepage:
                urls_to_add = []
                
                # 1. Standard blind guesses (High priority, append first)
                for path in self.CAREER_PATHS:
                    urls_to_add.append(urljoin(url, path))

                # 2. Dynamic discovery from homepage links (Lower priority)
                for link in soup.find_all("a", href=True):
                    href = link.get("href", "").lower()
                    text = link.get_text(strip=True).lower()
                    
                    # Skip noise paths that look like agency "hire developers" packages
                    if "service" in href or "packages" in href:
                        continue
                        
                    if any(kw in href or kw in text for kw in ["career", "contact", "job", "hiring", "join", "about", "team"]):
                        full_url = urljoin(current_url, link["href"])
                        if urlparse(full_url).netloc == urlparse(url).netloc:
                            urls_to_add.append(full_url)
                            
                # Preserve order while deduplicating to avoid randomized set shuffling
                seen_to_add = set()
                for u in urls_to_add:
                    if u not in visited and u not in queue and u not in seen_to_add:
                        seen_to_add.add(u)
                        queue.append(u)
                        
        clean = [e for e in all_emails if not self._is_noise_email(e)]
        return sorted(set(clean))

    def _is_noise_email(self, email: str) -> bool:
        """Filter out image filenames, placeholder emails, etc."""
        for pattern in self.NOISE_PATTERNS:
            if re.match(pattern, email, re.IGNORECASE):
                return True
        return False

    def _decode_cloudflare_email(self, hex_str: str) -> str:
        """Decode a Cloudflare email protection hex string."""
        try:
            key = int(hex_str[:2], 16)
            email = ""
            for i in range(2, len(hex_str), 2):
                char_val = int(hex_str[i:i+2], 16) ^ key
                email += chr(char_val)
            return email
        except Exception:
            return ""

    # ─── AI ENRICHMENT ──────────────────────────────────────────
    def enrich_company_data(self, company: dict, emails: list[str]) -> dict:
        """
        Use AI to:
          1. Classify if this is a real software/IT company (filter noise)
          2. Generate a fit score
          3. Draft personalized outreach email
        Returns enriched company dict.
        """
        if not self.ai_handler:
            company["fit_score"] = 50
            company["fit_reasoning"] = "AI handler not available — default score"
            company["status"] = "email_found" if emails else "website_found"
            return company

        # Step 1: Classify + Score
        profile = self.ai_handler.get_profile()
        profile_summary = json.dumps(profile, indent=2) if profile else "No profile available"

        classify_prompt = f"""Analyze this company and determine:
1. Is this a legitimate software/IT company? (Not a repair shop, training institute, or hardware store)
2. How well does it match this candidate's profile?

Company:
- Name: {company.get('name')}
- Address: {company.get('address')}
- Google Rating: {company.get('google_rating')}
- Website: {company.get('website', 'N/A')}
- Google Types: {company.get('types', [])}

Candidate Profile:
{profile_summary}

Return JSON:
{{
  "is_software_company": true/false,
  "fit_score": 0-100,
  "reasoning": "brief explanation",
  "company_type": "product/services/consulting/startup/other"
}}"""

        response = self.ai_handler.generate_completion(
            "You are a tech industry analyst. Classify companies accurately.",
            classify_prompt,
            json_mode=True
        )

        if response:
            try:
                result = json.loads(response)
                company["is_software_company"] = result.get("is_software_company", False)
                company["fit_score"] = result.get("fit_score", 0)
                company["fit_reasoning"] = result.get("reasoning", "")
                company["company_type"] = result.get("company_type", "unknown")
            except (json.JSONDecodeError, TypeError):
                company["fit_score"] = 30
                company["fit_reasoning"] = "AI parse error"
                company["is_software_company"] = True  # Err on the side of inclusion

        # Step 2: Generate outreach email (only for fit companies with emails)
        email_data = None
        if emails and company.get("fit_score", 0) >= 40:
            email_data = self._generate_outreach_email(company, emails, profile)

        # Update status
        if email_data:
            company["status"] = "outreach_ready"
        elif emails:
            company["status"] = "email_found"
        elif company.get("website"):
            company["status"] = "website_found"
        else:
            company["status"] = "discovered"

        # Build intelligence card
        company["intelligence_card"] = {
            "name": company.get("name"),
            "address": company.get("address"),
            "website": company.get("website"),
            "google_rating": company.get("google_rating"),
            "fit_score": company.get("fit_score"),
            "fit_reasoning": company.get("fit_reasoning"),
            "company_type": company.get("company_type", "unknown"),
            "emails": emails,
            "phone": company.get("phone", ""),
        }

        company["email_data"] = email_data
        return company

    def _generate_outreach_email(self, company: dict, emails: list[str], profile: dict) -> dict:
        """Generate a personalized outreach email using AI."""
        if not self.ai_handler:
            return None

        profile_summary = json.dumps(profile, indent=2) if profile else "No profile available"

        prompt = f"""Draft a highly personalized, premium, and compelling cold outreach email to a company's HR/careers team for job opportunities on behalf of Kaushal Shah.

Company Info:
- Name: {company.get('name')}
- Location: {company.get('address')}
- Website: {company.get('website', 'N/A')}
- Company Type: {company.get('company_type', 'IT')}

Candidate Profile:
{profile_summary}

Rules:
- Subject: MUST be exactly "Senior Full-Stack Engineer - Kaushal Shah (Angular 18+ / .NET Core / AI Automation)".
- Body Structure and Tone:
  1. Opening: Start with a professional introduction. Acknowledge {company.get('name')} and state interest in joining as a Senior Full-Stack Developer. Highlight 4.5+ years of experience building robust, scalable applications in secure, complex domains (LegalTech, FinTech, and SaaS).
  2. Value Hook: Incorporate a strong value statement highlighting his "dual-threat" capability: the architectural rigor of a backend engineer coupled with the user-centric design precision of a modern frontend developer.
  3. Skill Highlights Section: You MUST include a section titled exactly "My Core Stack & Expertise:" formatted as a clean, bulleted list. DO NOT use asterisks or any other markdown formatting. Format as follows:
     - Frontend Stack: Angular 18+, Vue.js, TypeScript (focused on modern reactive systems, state management, and high-performance UIs)
     - Backend Stack: .NET Core, C#, Node.js (expert in RESTful APIs, scalable database architectures, and microservices)
     - AI & Automation Edge: Hands-on integration of the OpenAI API and custom workflow automation engines to drive modern features and increase operational efficiency
     - Engineering Delivery: Proven history of leading module development, establishing clean-code standards, and mentoring junior engineers to elevate overall shipping velocity
  4. Closing: Explicitly state that he is based in Pune and fully open to working in-office. Explicitly mention that his resume is attached.
- Important Restrictions:
  1. STRICTLY FORBIDDEN: DO NOT start the email with generic greetings like "I hope this message finds you well", "I hope this email finds you well", or similar opening fluff. Begin directly with the professional introduction after the initial salutation (e.g. "Dear [Company] HR Team," followed by "My name is Kaushal Shah...").
  2. STRICTLY FORBIDDEN: DO NOT use markdown bolding (double asterisks like **Word** or similar) anywhere in the email body or headers. Use standard capitalization or plain text labeling (e.g. "My Core Stack & Expertise:" and "Frontend Stack:").
  3. DO NOT mention Current CTC or Expected CTC under any circumstances.
  4. DO NOT state a preference for remote/hybrid. Explicitly state he is open to in-office roles in Pune.
  5. DO NOT include any placeholders like [Your Contact Information], [Phone Number], or [LinkedIn Link].
  6. There should be no email signature at the very end of the email.

Return JSON:
{{
  "subject": "...",
  "body": "..."
}}"""

        response = self.ai_handler.generate_completion(
            "You are an expert career coach writing high-converting cold outreach emails.",
            prompt,
            json_mode=True
        )

        if response:
            try:
                return json.loads(response)
            except (json.JSONDecodeError, TypeError):
                return None
        return None

    # ─── FULL PIPELINE ──────────────────────────────────────────
    def run_pipeline_batched(self, location: str, radius: int = 10, batch_size: int = 1, mode: str = "production"):
        """
        Yields batches of enriched companies (size=5) for real-time DB updating.
        If mode is 'development', stops after the first batch.
        """
        print(f"\n{'='*60}")
        print(f"  LOCAL OUTREACH PIPELINE: {location} ({radius}km) [Mode: {mode.upper()}]")
        print(f"{'='*60}")

        print("\n[1/4] Searching Google Places...")
        companies = self.search_companies(location, radius)

        if not companies:
            print("  No companies found.")
            return

        print(f"  Found {len(companies)} total companies. Processing in batches of {batch_size}...")

        for i in range(0, len(companies), batch_size):
            batch = companies[i:i+batch_size]
            print(f"\n--- BATCH {i//batch_size + 1} (Companies {i+1} to {min(i+batch_size, len(companies))}) ---")

            print(f"[1.5/4] Fetching place details...")
            for company in batch:
                details = self._get_place_details(company["google_place_id"])
                if details:
                    company["website"] = details.get("website", "")
                    company["phone"] = details.get("formatted_phone_number", "")
                    company["address"] = details.get("formatted_address", company["address"])

            print(f"[2/4] Scraping websites for emails...")
            for j, company in enumerate(batch):
                website = company.get("website", "")
                if website:
                    emails = self.extract_website_emails(website)
                    company["extracted_emails"] = emails
                    status = f"✅ {len(emails)} email(s)" if emails else "❌ No emails"
                    print(f"  [{j+1}/{len(batch)}] {company['name']}: {status}")
                else:
                    company["extracted_emails"] = []
                    print(f"  [{j+1}/{len(batch)}] {company['name']}: ⚠️ No website")

            print(f"[3/4] AI enrichment...")
            enriched = []
            for j, company in enumerate(batch):
                enriched_company = self.enrich_company_data(company, company.get("extracted_emails", []))

                if not enriched_company.get("is_software_company", True):
                    print(f"  [{j+1}] ❌ FILTERED: {company['name']} — not a software company")
                    continue

                enriched.append(enriched_company)
                score = enriched_company.get("fit_score", 0)
                print(f"  [{j+1}] {company['name']}: score={score} | {enriched_company.get('fit_reasoning', '')}")

            print(f"[4/4] Yielding batch to pipeline...")
            yield enriched

            if mode == 'development':
                print(f"  [DEVELOPMENT MODE] Stopping after first batch.")
                break

