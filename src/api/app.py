from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import json
import os
import sys

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.utils.dbhandler import OutreachDB
from src.utils.ai_handler import AIHandler
from src.client.local_outreach import LocalOutreachClient

app = FastAPI(
    title="NopeRi Local Outreach API",
    description="Discover IT companies near you, scrape emails, and generate outreach drafts.",
    version="1.0.0"
)

# CORS — allow Angular dev server & Tampermonkey Zoho extension
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Singleton instances
db = OutreachDB()


class StatusUpdate(BaseModel):
    status: str


class EmailStatusUpdate(BaseModel):
    sent_status: str


class LatestUpdatePayload(BaseModel):
    latest_update: str


class EmailCreatePayload(BaseModel):
    extracted_emails: List[str] = []
    email_subject: str = ""
    email_body: str = ""
    sent_status: str = "drafted"
    latest_update: str = ""


# ─── ENDPOINTS ──────────────────────────────────────────────────

from fastapi import BackgroundTasks

# Store active searches globally
active_searches = set()

def background_pipeline(client: LocalOutreachClient, location: str, radius: int, db: OutreachDB, mode: str):
    active_searches.add(location)
    try:
        print(f"\n[1/4] Discovering companies concurrently near '{location}'...")
        companies = client.search_companies(location, radius)
        if not companies:
            print("  No companies discovered.")
            return

        # Filter out duplicates that already exist in the database to prevent duplicate scraping
        filtered_companies = []
        duplicate_count = 0
        for company in companies:
            pid = company.get("google_place_id")
            if pid and db.company_exists_by_place_id(pid):
                duplicate_count += 1
            else:
                filtered_companies.append(company)
        
        if duplicate_count > 0:
            print(f"  [DUPLICATE FILTER] Skipped {duplicate_count} companies that are already in the database.")

        if not filtered_companies:
            print("  All discovered companies are already in the database. Nothing to scrape.")
            return

        # If in development mode, limit to 2 companies for fast test iterations
        if mode == "development":
            filtered_companies = filtered_companies[:2]
            print(f"  [DEVELOPMENT MODE] Limited execution queue to 2 companies.")

        from concurrent.futures import ThreadPoolExecutor
        
        def process_single_company(company):
            try:
                # 1. Fetch place details
                details = client._get_place_details(company["google_place_id"])
                if details:
                    company["website"] = details.get("website", "")
                    company["phone"] = details.get("formatted_phone_number", "")
                    company["address"] = details.get("formatted_address", company["address"])

                # 2. Extract website emails
                website = company.get("website", "")
                emails = []
                if website:
                    emails = client.extract_website_emails(website)
                company["extracted_emails"] = emails

                # 3. AI Enrichment (Unified fit score & cold email drafting in one call)
                enriched = client.enrich_company_data(company, emails)
                
                # Check software company filter
                if not enriched.get("is_software_company", True):
                    print(f"  [Pipeline] Filtered out non-software company: {company['name']}")
                    return None

                # 4. Save to Database (thread-safe, with SQLite 30s timeout)
                enriched["search_location"] = location
                enriched["search_radius"] = radius
                company_id = db.save_company(enriched)

                # Save outreach email if generated
                if enriched.get("email_data"):
                    db.save_outreach_email({
                        "company_id": company_id,
                        "extracted_emails": enriched.get("extracted_emails", []),
                        "email_subject": enriched["email_data"].get("subject", ""),
                        "email_body": enriched["email_data"].get("body", ""),
                        "sent_status": "drafted"
                    })
                # Save extracted emails even if no AI draft
                elif enriched.get("extracted_emails"):
                    db.save_outreach_email({
                        "company_id": company_id,
                        "extracted_emails": enriched.get("extracted_emails", []),
                        "email_subject": "",
                        "email_body": "",
                        "sent_status": "pending"
                    })
                print(f"  [Pipeline] Successfully processed and saved: {company['name']}")
                return company
            except Exception as e:
                print(f"  [Pipeline] Error processing company {company.get('name')}: {e}")
                return None

        # Concurrently process companies
        max_workers = 5 if mode == "production" else 2
        print(f"  [Pipeline] Processing {len(filtered_companies)} companies with concurrency limit {max_workers}...")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(process_single_company, c) for c in filtered_companies]
            for future in futures:
                try:
                    future.result()  # blocks until completed, raising exceptions if not handled
                except Exception as ex:
                    print(f"  [Pipeline] Uncaught thread exception: {ex}")
                    
    except Exception as e:
        print(f"Error in background pipeline: {e}")
    finally:
        if location in active_searches:
            active_searches.remove(location)

@app.get("/api/search")
async def search_companies(
    background_tasks: BackgroundTasks,
    location: str = Query(..., description="Location string, e.g. 'Baner, Pune'"),
    radius: int = Query(10, description="Search radius in km", ge=1, le=50),
    mode: str = Query("development", description="Mode: 'development' or 'production'")
):
    """
    Start the full pipeline in the background: search Google Places -> scrape websites -> AI enrich -> store in DB.
    Returns immediately so UI can poll for batches.
    """
    try:
        if location in active_searches:
             return {"status": "already_running", "location": location, "radius": radius, "mode": mode}

        ai = AIHandler()
        ai.extract_profile()
        client = LocalOutreachClient(ai_handler=ai)

        background_tasks.add_task(background_pipeline, client, location, radius, db, mode)

        return {
            "status": "started",
            "location": location,
            "radius": radius,
            "mode": mode
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")

@app.get("/api/search/status")
async def search_status(location: str):
    """Check if a background search is currently running for a location."""
    return {"is_searching": location in active_searches}


@app.get("/api/companies")
async def get_companies(
    location: Optional[str] = Query(None, description="Filter by search location")
):
    """Get all stored companies with their outreach emails."""
    companies = db.get_all_with_emails(location)
    stats = db.get_pipeline_stats(location)
    verifications = db.get_all_email_verifications()
    return {
        "companies": companies,
        "stats": stats,
        "total": len(companies),
        "verifications": verifications
    }


class StatusUpdate(BaseModel):
    status: str

@app.patch("/api/companies/{company_id}/status")
async def update_company_status(company_id: str, update: StatusUpdate):
    """Update the status of a company (e.g. 'sent_manually')."""
    success = db.update_company_status(company_id, update.status)
    if not success:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Also update email status if it's sent or bounced
    if update.status == 'sent_manually':
        company = db.get_company_with_emails(company_id)
        if company and company.get("outreach_emails"):
            for email in company["outreach_emails"]:
                db.update_email_status(email["id"], "sent")
    elif update.status == 'bounced':
        company = db.get_company_with_emails(company_id)
        if company and company.get("outreach_emails"):
            for email in company["outreach_emails"]:
                db.update_email_status(email["id"], "bounced")
                
    return {"status": "updated"}

@app.get("/api/companies/{company_id}")
async def get_company(company_id: str):
    """Get a single company with its outreach details."""
    company = db.get_company_with_emails(company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    if company.get("intelligence_card_json"):
        try:
            company["intelligence_card"] = json.loads(company["intelligence_card_json"])
        except (json.JSONDecodeError, TypeError):
            company["intelligence_card"] = {}
    return company


@app.post("/api/companies/{company_id}/emails")
async def create_outreach_email(company_id: str, body: EmailCreatePayload):
    """Create a new outreach email record for a company."""
    email_dict = {
        "company_id": company_id,
        "extracted_emails": body.extracted_emails,
        "email_subject": body.email_subject,
        "email_body": body.email_body,
        "sent_status": body.sent_status,
        "latest_update": body.latest_update
    }
    email_id = db.save_outreach_email(email_dict)
    return {"status": "created", "email_id": email_id}


@app.delete("/api/companies/{company_id}")
async def delete_company(company_id: str):
    """Delete a company and its emails."""
    success = db.delete_company(company_id)
    if not success:
        raise HTTPException(status_code=404, detail="Company not found")
    return {"status": "deleted", "company_id": company_id}


@app.put("/api/companies/{company_id}/status")
async def update_company_status(company_id: str, body: StatusUpdate):
    """Update a company's pipeline status (e.g. 'sent_manually')."""
    valid_statuses = ["discovered", "website_found", "email_found", "outreach_ready", "sent_manually", "responded", "skipped", "bounced"]
    if body.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
    success = db.update_company_status(company_id, body.status)
    if not success:
        raise HTTPException(status_code=404, detail="Company not found")
    return {"status": "updated", "company_id": company_id, "new_status": body.status}


@app.put("/api/emails/{email_id}/status")
async def update_email_status(email_id: str, body: EmailStatusUpdate):
    """Update an outreach email's sent status."""
    valid = ["drafted", "pending", "sent", "replied", "bounced"]
    if body.sent_status not in valid:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid}")
    success = db.update_email_status(email_id, body.sent_status)
    if not success:
        raise HTTPException(status_code=404, detail="Email record not found")
    return {"status": "updated", "email_id": email_id, "new_status": body.sent_status}


@app.put("/api/emails/{email_id}/latest-update")
async def update_email_latest_update(email_id: str, body: LatestUpdatePayload):
    """Update the latest status update note/comment of an outreach email."""
    success = db.update_email_latest_update(email_id, body.latest_update)
    if not success:
        raise HTTPException(status_code=404, detail="Email record not found")
    return {"status": "updated", "email_id": email_id, "latest_update": body.latest_update}


@app.get("/api/stats")
async def get_stats(
    location: Optional[str] = Query(None, description="Filter by search location")
):
    """Get pipeline funnel stats."""
    return db.get_pipeline_stats(location)


@app.get("/api/verify-email")
async def verify_email(email: str = Query(..., description="Email to verify")):
    """Verify email using Hunter.io API"""
    existing = db.get_email_verification(email)
    if existing:
        return {"status": existing["status"], "score": existing["score"]}

    from dotenv import load_dotenv
    load_dotenv()
    
    api_key = os.environ.get("HUNTER_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="HUNTER_API_KEY not configured in .env")
    
    url = f"https://api.hunter.io/v2/email-verifier?email={email}&api_key={api_key}"
    try:
        import requests
        response = requests.get(url)
        data = response.json()
        
        status = "unknown"
        score = 0
        
        if "data" in data and "status" in data["data"]:
            status = data["data"]["status"]
            score = data["data"].get("score", 0)
        elif "data" in data and "result" in data["data"]: # sometimes it's result
            status = data["data"]["result"]
            score = data["data"].get("score", 0)
        else:
            return {"status": "unknown", "error": data.get("errors", "Unknown error")}
            
        db.save_email_verification(email, status, score)
        return {"status": status, "score": score}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/locations")
async def get_locations():
    """Get all unique search locations that have been queried."""
    db_conn = db._connect()
    try:
        cursor = db_conn.cursor()
        cursor.execute("SELECT DISTINCT search_location FROM companies WHERE search_location IS NOT NULL ORDER BY search_location")
        rows = cursor.fetchall()
        return {"locations": [dict(row)["search_location"] for row in rows]}
    finally:
        db_conn.close()


@app.get("/api/outreach/pending")
async def get_pending_outreach():
    """Get all unsent outreach email drafts."""
    db_conn = db._connect()
    try:
        cursor = db_conn.cursor()
        cursor.execute("""
            SELECT c.id as company_id, c.name as company_name, c.website,
                   e.id as email_id, e.extracted_emails, e.email_subject, e.email_body, e.sent_status
            FROM companies c
            JOIN outreach_emails e ON c.id = e.company_id
            WHERE e.sent_status = 'drafted'
            ORDER BY c.created_at ASC
        """)
        rows = cursor.fetchall()
        
        pending = []
        for row in rows:
            r = dict(row)
            try:
                r["extracted_emails"] = json.loads(r["extracted_emails"])
            except:
                r["extracted_emails"] = []
            pending.append(r)
            
        return pending
    finally:
        db_conn.close()


from fastapi.responses import FileResponse

@app.get("/api/userscript/zoho-assistant.user.js")
async def get_zoho_userscript():
    """Serve the Tampermonkey Userscript file directly for instant installation."""
    script_path = os.path.join(os.path.dirname(__file__), "..", "..", "scratch", "zoho_outreach_assistant.user.js")
    if os.path.exists(script_path):
        return FileResponse(script_path, media_type="application/javascript", filename="zoho_outreach_assistant.user.js")
    raise HTTPException(status_code=404, detail="Userscript file not found")

