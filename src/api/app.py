from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
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

# CORS — allow Angular dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200", "http://127.0.0.1:4200"],
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


# ─── ENDPOINTS ──────────────────────────────────────────────────

from fastapi import BackgroundTasks

# Store active searches globally
active_searches = set()

def background_pipeline(client: LocalOutreachClient, location: str, radius: int, db: OutreachDB, mode: str):
    active_searches.add(location)
    try:
        for batch in client.run_pipeline_batched(location, radius, batch_size=3, mode=mode):
            for company in batch:
                company["search_location"] = location
                company["search_radius"] = radius
                company_id = db.save_company(company)

                # Save outreach email if generated
                if company.get("email_data"):
                    db.save_outreach_email({
                        "company_id": company_id,
                        "extracted_emails": company.get("extracted_emails", []),
                        "email_subject": company["email_data"].get("subject", ""),
                        "email_body": company["email_data"].get("body", ""),
                        "sent_status": "drafted"
                    })
                # Save extracted emails even if no AI draft
                elif company.get("extracted_emails"):
                    db.save_outreach_email({
                        "company_id": company_id,
                        "extracted_emails": company.get("extracted_emails", []),
                        "email_subject": "",
                        "email_body": "",
                        "sent_status": "pending"
                    })
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
    return {
        "companies": companies,
        "stats": stats,
        "total": len(companies)
    }


class StatusUpdate(BaseModel):
    status: str

@app.patch("/api/companies/{company_id}/status")
async def update_company_status(company_id: str, update: StatusUpdate):
    """Update the status of a company (e.g. 'sent_manually')."""
    success = db.update_company_status(company_id, update.status)
    if not success:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Also update email status if it's sent
    if update.status == 'sent_manually':
        company = db.get_company_with_emails(company_id)
        if company and company.get("outreach_emails"):
            for email in company["outreach_emails"]:
                db.update_email_status(email["id"], "sent")
                
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
    valid_statuses = ["discovered", "website_found", "email_found", "outreach_ready", "sent_manually", "responded", "skipped"]
    if body.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
    success = db.update_company_status(company_id, body.status)
    if not success:
        raise HTTPException(status_code=404, detail="Company not found")
    return {"status": "updated", "company_id": company_id, "new_status": body.status}


@app.put("/api/emails/{email_id}/status")
async def update_email_status(email_id: str, body: EmailStatusUpdate):
    """Update an outreach email's sent status."""
    valid = ["drafted", "pending", "sent", "replied"]
    if body.sent_status not in valid:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid}")
    success = db.update_email_status(email_id, body.sent_status)
    if not success:
        raise HTTPException(status_code=404, detail="Email record not found")
    return {"status": "updated", "email_id": email_id, "new_status": body.sent_status}


@app.get("/api/stats")
async def get_stats(
    location: Optional[str] = Query(None, description="Filter by search location")
):
    """Get pipeline funnel stats."""
    return db.get_pipeline_stats(location)


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
