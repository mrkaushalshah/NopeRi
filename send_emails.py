import os
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
import time
import json
import sqlite3
import random
import argparse
import mimetypes
import requests
from datetime import datetime
from dotenv import load_dotenv
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import re
import imaplib
import email

load_dotenv()

# Add project root to path for imports if needed
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ================== CONFIGURATION ==================
DB_PATH = "outreach.db"

# SMTP Config
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.zoho.in") # Default to Zoho India
SMTP_PORT = int(os.environ.get("SMTP_PORT", "465"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")  # Zoho App Password

# Resume Config
RESUME_PATH = os.environ.get("RESUME_PATH", "assests/resume.pdf")

# Telegram Config
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# Standardized Signature to append to all emails
# Update this with your actual LinkedIn/Github links if you want
SIGNATURE_HTML = """
<br><br>
Best regards,<br>
<b>Kaushal Shah</b><br>
Senior Full-Stack Developer<br>
+91 99744 42525<br>
<a href="https://www.linkedin.com/in/mrkaushalshah/">LinkedIn</a> | 
<a href="https://www.mrkaushalshah.com/">Portfolio</a>
"""

# Delay settings to prevent spam classification
MIN_DELAY_SECONDS = 60
MAX_DELAY_SECONDS = 120

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

def select_best_email(email_list):
    """Prioritizes HR/Career emails and filters out sales/support/billing emails and junk syntax."""
    if not email_list:
        return None
        
    # Standardize to lowercase and strictly validate email format
    # This prevents scraping bugs like "+@domain.com" from being selected
    valid_emails = []
    for e in email_list:
        e_lower = e.lower().strip()
        # Must start with letter/number, can contain . _ -, and must have valid domain
        if re.match(r'^[a-z0-9][a-z0-9._-]*@[a-z0-9.-]+\.[a-z]{2,}$', e_lower):
            valid_emails.append(e_lower)
            
    if not valid_emails:
        return None
    
    # Priority 1: Direct HR and Hiring (Highest success rate)
    for e in valid_emails:
        if any(keyword in e for keyword in ['hr@', 'career', 'jobs@', 'recruitment', 'talent', 'hiring', 'people']):
            return e
            
    # Priority 2: Founders, Management, or general Info
    for e in valid_emails:
        if any(keyword in e for keyword in ['ceo@', 'founder@', 'director@', 'admin@', 'info@', 'contact@', 'hello@', 'hi@', 'team@']):
            return e
            
    # Priority 3: Fallback, but strictly avoid negative departments
    negatives = ['sales@', 'support@', 'billing@', 'noreply@', 'no-reply@', 'marketing@', 'press@', 'media@', 'help@']
    for e in valid_emails:
        if not any(neg in e for neg in negatives):
            return e
            
    # If all extracted emails are in the negative list, skip sending.
    return None

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=15.0)
    conn.row_factory = sqlite3.Row
    return conn

def check_verification_status(email_addr):
    """Checks database for Hunter.io email verification status."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT status, score FROM email_verifications WHERE email = ?", (email_addr,))
        row = cursor.fetchone()
        if row:
            return row["status"], row["score"]
        return "unverified", 0
    except Exception as e:
        print(f"Error checking email verification: {e}")
        return "error", 0
    finally:
        conn.close()

def update_sent_status(company_id, email_id):
    """Updates database status for company and email to match UI standard."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        # 1. Update email status to 'sent'
        cursor.execute(
            "UPDATE outreach_emails SET sent_status = 'sent' WHERE id = ?",
            (email_id,)
        )
        # 2. Update company status to 'sent_manually' (UI uses this to show checklist checkmark)
        cursor.execute(
            "UPDATE companies SET status = 'sent_manually' WHERE id = ?",
            (company_id,)
        )
        conn.commit()
        print(f"Updated DB status for Company: {company_id}, Email: {email_id}")
    except Exception as e:
        print(f"Database update failed: {e}")
    finally:
        conn.close()

def send_email_via_smtp(recipient, subject, body_text):
    """Logs into Zoho/SMTP and sends the email with resume attachment."""
    if not SMTP_USER or not SMTP_PASSWORD:
        raise ValueError("SMTP_USER and SMTP_PASSWORD must be configured in .env")

    # Clean the AI body of any accidental signatures
    # We strip out common sign-offs and everything after them so we can append our own clean signature
    clean_body = re.split(r'(?i)\b(Best regards|Sincerely|Kind regards|Warm regards|Regards|Cheers|Best,|Thanks,|Thank you,)(?:,|\b|\n)', body_text)[0].strip()

    # Create MIMEMultipart message
    msg = MIMEMultipart()
    msg['From'] = SMTP_USER
    msg['To'] = recipient
    msg['Subject'] = subject

    # Attach the HTML-like formatting or plain text body
    # Zoho/Gmail works best with HTML body, replace newlines with breaks
    formatted_body = clean_body.replace(chr(10), '<br>')
    final_html_body = f"<html><body>{formatted_body}{SIGNATURE_HTML}</body></html>"
    msg.attach(MIMEText(final_html_body, 'html'))

    # Attach resume if configured and exists
    if RESUME_PATH and os.path.exists(RESUME_PATH):
        try:
            filename = os.path.basename(RESUME_PATH)
            ctype, encoding = mimetypes.guess_type(RESUME_PATH)
            if ctype is None or encoding is not None:
                ctype = 'application/octet-stream'
            maintype, subtype = ctype.split('/', 1)
            
            with open(RESUME_PATH, 'rb') as f:
                attachment = MIMEBase(maintype, subtype)
                attachment.set_payload(f.read())
                encoders.encode_base64(attachment)
                attachment.add_header(
                    'Content-Disposition',
                    'attachment',
                    filename=filename
                )
                msg.attach(attachment)
                print(f"Attached resume: {filename}")
        except Exception as e:
            print(f"Error attaching resume file: {e}")
            send_telegram_message(f"⚠️ <b>Warning:</b> Could not attach resume {RESUME_PATH} to email to {recipient}: {e}")
    else:
        print(f"Warning: Resume not found or path not specified: '{RESUME_PATH}'")
        # Notify user so they know they are sending applications without resumes
        send_telegram_message(f"⚠️ <b>Warning:</b> Resume PDF not found at <code>{RESUME_PATH}</code>. Sending email to {recipient} without attachment.")

    # SMTP Connection
    print(f"Connecting to SMTP server {SMTP_HOST}:{SMTP_PORT}...")
    if SMTP_PORT == 465:
        # SSL Connection
        server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=30)
    else:
        # TLS/STARTTLS Connection
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30)
        server.ehlo()
        server.starttls()
        server.ehlo()

    try:
        server.login(SMTP_USER, SMTP_PASSWORD)
        print("SMTP Login successful.")
        server.sendmail(SMTP_USER, recipient, msg.as_string())
        print(f"Email sent successfully to: {recipient}")
        return True
    finally:
        try:
            server.quit()
        except:
            pass

def check_bounces():
    """Connects to Gmail via IMAP, finds bounced emails, updates DB, and notifies Telegram."""
    if not SMTP_USER or not SMTP_PASSWORD:
        return
        
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Checking inbox for new bounced emails...")
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(SMTP_USER, SMTP_PASSWORD)
        mail.select("inbox")
        
        # Search for failure notifications
        status, messages = mail.search(None, '(OR FROM "mailer-daemon@googlemail.com" SUBJECT "Delivery Status Notification (Failure)")')
        if status != "OK":
            return
            
        email_ids = messages[0].split()
        if not email_ids:
            return
            
        bounced_count = 0
        conn = get_db_connection()
        cursor = conn.cursor()
        
        for e_id in email_ids:
            res, msg_data = mail.fetch(e_id, '(RFC822)')
            if res != "OK": continue
            
            body = ""
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                try:
                                    body = part.get_payload(decode=True).decode()
                                    break
                                except: pass
                    else:
                        try:
                            body = msg.get_payload(decode=True).decode()
                        except: pass
            
            # Extract emails from body
            found_emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', body)
            bounced_addresses = [e for e in found_emails if e.lower() != SMTP_USER.lower() and 'mailer-daemon' not in e.lower() and 'google.com' not in e.lower()]
            
            if bounced_addresses:
                # The first extracted non-Google email is usually the one that failed
                bounced_addr = bounced_addresses[0]
                
                # Check if we sent an email to this address recently
                cursor.execute("""
                    SELECT c.id as company_id, e.id as email_id, c.name 
                    FROM outreach_emails e
                    JOIN companies c ON c.id = e.company_id
                    WHERE e.extracted_emails LIKE ? AND e.sent_status = 'sent'
                """, (f'%{bounced_addr}%',))
                
                row = cursor.fetchone()
                if row:
                    cursor.execute("UPDATE outreach_emails SET sent_status = 'bounced' WHERE id = ?", (row['email_id'],))
                    cursor.execute("UPDATE companies SET status = 'bounced' WHERE id = ?", (row['company_id'],))
                    conn.commit()
                    bounced_count += 1
                    
                    send_telegram_message(f"🚨 <b>Bounced Email Detected</b>\n🏢 <b>Company:</b> {row['name']}\n📬 <b>Failed Address:</b> {bounced_addr}")
                    
                # Move the bounce notification to Trash so we don't process it again
                mail.store(e_id, '+FLAGS', '\\Deleted')
                
        if bounced_count > 0:
            print(f"Processed {bounced_count} bounced emails. Database updated.")
            
        mail.expunge()
        mail.close()
        mail.logout()
    except Exception as e:
        print(f"Error tracking bounced emails: {e}")

def process_pending_emails(test_email=None, run_bounces=True, run_sends=True):
    """Fetches drafted emails. If test_email is provided, sends a preview of the FIRST draft and exits."""
    
    # Check for bounces first before sending new ones
    if run_bounces and not test_email:
        check_bounces()
        
    if not run_sends:
        return
        
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Checking for drafted outreach emails...")
    
    if not os.path.exists(DB_PATH):
        print(f"Error: Database file '{DB_PATH}' not found. Run local outreach pipeline first.")
        return

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT c.id as company_id, c.name as company_name, c.website,
                   e.id as email_id, e.extracted_emails, e.email_subject, e.email_body, e.sent_status
            FROM companies c
            JOIN outreach_emails e ON c.id = e.company_id
            WHERE e.sent_status = 'drafted'
            ORDER BY c.created_at ASC
        """)
        rows = cursor.fetchall()
        drafted_emails = [dict(row) for row in rows]
    finally:
        conn.close()

    if not drafted_emails:
        print("No pending drafted emails to send.")
        return

    print(f"Found {len(drafted_emails)} drafted email(s) waiting to be sent.")
    
    # Check SMTP credentials before starting the loop
    if not SMTP_USER or not SMTP_PASSWORD:
        print("Error: SMTP_USER or SMTP_PASSWORD not set in .env. Cannot send emails.")
        send_telegram_message("❌ <b>Email Automation Error:</b> SMTP_USER or SMTP_PASSWORD is not configured in your <code>.env</code> file. Automation is paused.")
        return

    # Check resume PDF existence
    if not os.path.exists(RESUME_PATH):
        print(f"CRITICAL WARNING: Resume PDF does not exist at '{RESUME_PATH}'!")
        send_telegram_message(f"⚠️ <b>Email Automation Alert:</b> Resume PDF not found at <code>{RESUME_PATH}</code>. Please upload your resume to that path so it gets attached to outreach emails.")

    sent_count = 0
    for idx, draft in enumerate(drafted_emails):
        company_name = draft["company_name"]
        email_id = draft["email_id"]
        company_id = draft["company_id"]
        subject = draft["email_subject"]
        body = draft["email_body"]
        
        try:
            emails = json.loads(draft["extracted_emails"])
        except Exception:
            emails = []

        if not emails:
            print(f"[{idx+1}/{len(drafted_emails)}] Skipped {company_name} - No email addresses found.")
            update_sent_status(company_id, email_id)
            continue

        recipient = select_best_email(emails)
        
        if not recipient:
            print(f"[{idx+1}/{len(drafted_emails)}] Skipped {company_name} - Filtered out bad emails (only sales/support found).")
            # Update DB so it doesn't get stuck in the queue
            update_sent_status(company_id, email_id)
            continue
        
        # --- TEST MODE OVERRIDE ---
        if test_email:
            print(f"\n🧪 TEST MODE ENABLED: Redirecting email meant for {recipient} to your test address: {test_email}")
            recipient = test_email
            
        # Check Hunter Verification to protect domain reputation (Skip if in test mode)
        if not test_email:
            verify_status, verify_score = check_verification_status(recipient)
            if verify_status == "undeliverable":
                print(f"[{idx+1}/{len(drafted_emails)}] Skipped {company_name} ({recipient}) - Verified as UNDELIVERABLE (Hunter.io score: {verify_score}).")
                send_telegram_message(f"⏭️ <b>Skipped undeliverable email</b> for <b>{company_name}</b> ({recipient}) to protect your domain reputation.")
                update_sent_status(company_id, email_id)
                continue
            
        print(f"\n[{idx+1}/{len(drafted_emails)}] Sending to {company_name} ({recipient})...")
        
        try:
            success = send_email_via_smtp(recipient, subject, body)
            if success:
                if test_email:
                    print(f"✅ Test email sent to {test_email}. Database was NOT updated. Exiting test mode.")
                    return # Exit after sending one test email
                    
                # Update database
                update_sent_status(company_id, email_id)
                sent_count += 1
                
                # Send telegram notification
                success_msg = (
                    f"📧 <b>Outreach Sent!</b>\n"
                    f"🏢 <b>Company:</b> {company_name}\n"
                    f"📬 <b>To:</b> {recipient}\n"
                    f"📝 <b>Subject:</b> {subject}"
                )
                send_telegram_message(success_msg)
                
                # Randomized sleep between emails to mimic human behavior and bypass filters
                if idx < len(drafted_emails) - 1:
                    delay = random.randint(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS)
                    print(f"Sleeping for {delay} seconds before next email to protect sender reputation...")
                    time.sleep(delay)
        except Exception as e:
            err_msg = f"❌ Error sending email to {company_name} ({recipient}): {e}"
            print(err_msg)
            send_telegram_message(f"❌ <b>Failed to send email</b> to <b>{company_name}</b> ({recipient}):\n<code>{str(e)}</code>")
            # We don't mark as sent, so it can be retried later
            time.sleep(10) # Quick sleep on error

    print(f"\nFinished processing. Sent {sent_count} email(s) successfully.")

def continuous_runner(loop_interval_minutes, run_bounces=True, run_sends=True):
    mode_text = "Email Sender & Bounce Checking"
    if run_bounces and not run_sends:
        mode_text = "Bounce Checking Only"
    elif run_sends and not run_bounces:
        mode_text = "Email Sender Only"
        
    print(f"Starting continuous {mode_text} (checking database every {loop_interval_minutes} minutes)...")
    send_telegram_message(f"🤖 <b>{mode_text} Active</b>\nChecking <code>outreach.db</code> every {loop_interval_minutes} minutes.")
    
    while True:
        try:
            process_pending_emails(run_bounces=run_bounces, run_sends=run_sends)
        except Exception as e:
            print(f"Error in automation loop: {e}")
        
        print(f"Sleeping for {loop_interval_minutes} minutes...")
        time.sleep(loop_interval_minutes * 60)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NopeRi Zoho SMTP Email Outreach Automation")
    parser.add_argument("--loop", action="store_true", help="Run continuously in a loop")
    parser.add_argument("--interval", type=int, default=15, help="Loop check interval in minutes (default: 15)")
    parser.add_argument("--bounce-only", action="store_true", help="Only run bounce checking")
    parser.add_argument("--send-only", action="store_true", help="Only run email sending")
    parser.add_argument("--test", type=str, metavar="EMAIL", help="Run in test mode: Sends the first drafted email to the specified EMAIL address and does not update the database.")
    args = parser.parse_args()

    run_bounces = True
    run_sends = True
    if args.bounce_only: run_sends = False
    if args.send_only: run_bounces = False

    if args.test:
        print(f"Starting in TEST MODE. Target: {args.test}")
        process_pending_emails(test_email=args.test, run_bounces=run_bounces, run_sends=run_sends)
    elif args.loop:
        continuous_runner(args.interval, run_bounces=run_bounces, run_sends=run_sends)
    else:
        process_pending_emails(run_bounces=run_bounces, run_sends=run_sends)
