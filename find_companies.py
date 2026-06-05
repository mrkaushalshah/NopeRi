import argparse
import os
import sys
import json
import requests
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

from src.utils.dbhandler import OutreachDB
from src.utils.ai_handler import AIHandler
from src.client.local_outreach import LocalOutreachClient

load_dotenv()

# Telegram Config
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

def send_telegram_message(text):
    """Sends a Telegram notification to the user."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "HTML"
        }
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        print(f"Error sending Telegram notification: {e}")

def main():
    parser = argparse.ArgumentParser(description="NopeRi Company Email Finder CLI")
    parser.add_argument("--location", required=True, help="Location, e.g. 'Baner, Pune'")
    parser.add_argument("--radius", type=int, default=10, help="Search radius in km")
    parser.add_argument("--mode", default="production", choices=["development", "production"], help="Mode")
    args = parser.parse_args()

    db = OutreachDB()
    ai = AIHandler()
    
    msg = f"🏢 <b>Company Email Finding Started</b>\n📍 <b>Location:</b> {args.location}\n📏 <b>Radius:</b> {args.radius} km\n⚙️ <b>Mode:</b> {args.mode.upper()}"
    send_telegram_message(msg)
    print(msg.replace("<b>", "").replace("</b>", ""))

    try:
        ai.extract_profile()
        client = LocalOutreachClient(ai_handler=ai, db=db)
        
        # We process in batches of 5 to align with standard behavior
        generator = client.run_pipeline_batched(
            location=args.location,
            radius=args.radius,
            batch_size=5,
            mode=args.mode
        )
        
        total_discovered = 0
        total_enriched = 0
        
        for batch in generator:
            for company in batch:
                pid = company.get("google_place_id")
                # Double check if company exists in DB to prevent duplicates
                if pid and db.company_exists_by_place_id(pid):
                    print(f"  [Duplicate Filter] Company {company['name']} already exists in database, skipping.")
                    continue
                
                # Enforce search parameters on company dict
                company["search_location"] = args.location
                company["search_radius"] = args.radius
                
                # Save to database
                company_id = db.save_company(company)
                total_discovered += 1
                
                # Save email draft or pending outreach
                if company.get("email_data"):
                    db.save_outreach_email({
                        "company_id": company_id,
                        "extracted_emails": company.get("extracted_emails", []),
                        "email_subject": company["email_data"].get("subject", ""),
                        "email_body": company["email_data"].get("body", ""),
                        "sent_status": "drafted"
                    })
                    total_enriched += 1
                    
                    # Notify user of new high-quality lead
                    lead_msg = (
                        f"✨ <b>New Lead Found!</b>\n"
                        f"🏢 <b>Company:</b> {company['name']}\n"
                        f"⭐ <b>Google Rating:</b> {company.get('google_rating') or 'N/A'}\n"
                        f"🌐 <b>Website:</b> {company.get('website') or 'N/A'}\n"
                        f"🤖 <b>AI Fit Score:</b> {company.get('fit_score')}/100\n"
                        f"📬 <b>Emails:</b> {', '.join(company.get('extracted_emails', []))}\n"
                        f"📝 <b>Reasoning:</b> {company.get('fit_reasoning')}"
                    )
                    send_telegram_message(lead_msg)
                elif company.get("extracted_emails"):
                    db.save_outreach_email({
                        "company_id": company_id,
                        "extracted_emails": company.get("extracted_emails", []),
                        "email_subject": "",
                        "email_body": "",
                        "sent_status": "pending"
                    })
                    total_enriched += 1
                    
                print(f"Successfully processed: {company['name']}")
                
        final_msg = f"✅ <b>Company Email Finding Completed</b>\n📍 <b>Location:</b> {args.location}\n📊 <b>Processed:</b> {total_discovered} companies\n📨 <b>Outreach Ready:</b> {total_enriched} companies"
        send_telegram_message(final_msg)
        print(final_msg.replace("<b>", "").replace("</b>", ""))
        
    except Exception as e:
        err_msg = f"❌ <b>Error in Company Email Finding:</b>\n<code>{str(e)}</code>"
        send_telegram_message(err_msg)
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
