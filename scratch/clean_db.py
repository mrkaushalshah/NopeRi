import sqlite3

def clean_database():
    db_path = "outreach.db"
    print(f"Connecting to database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 1. Fetch counts before
        cursor.execute("SELECT COUNT(*) FROM companies")
        before_companies = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM outreach_emails")
        before_emails = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM email_verifications")
        before_verifications = cursor.fetchone()[0]

        print("\n--- BEFORE CLEANUP ---")
        print(f"Total Companies: {before_companies}")
        print(f"Total Outreach Emails: {before_emails}")
        print(f"Total Email Verifications: {before_verifications}")

        # 2. Delete unsent emails
        cursor.execute("DELETE FROM outreach_emails WHERE sent_status != 'sent'")
        deleted_emails = cursor.rowcount

        # 3. Delete unsent companies (not associated with a sent email AND status != 'sent_manually')
        cursor.execute("""
            DELETE FROM companies 
            WHERE id NOT IN (
                SELECT DISTINCT company_id FROM outreach_emails WHERE sent_status = 'sent'
            ) AND status != 'sent_manually'
        """)
        deleted_companies = cursor.rowcount

        # 4. Cleanup unused email verifications (keep only those that are verified and part of a sent email)
        # First, let's extract all emails from the sent outreach emails to keep their verifications
        cursor.execute("SELECT extracted_emails FROM outreach_emails WHERE sent_status = 'sent'")
        sent_emails_json = cursor.fetchall()
        
        sent_emails_set = set()
        import json
        for row in sent_emails_json:
            try:
                emails_list = json.loads(row[0])
                for email in emails_list:
                    sent_emails_set.add(email.lower())
            except Exception:
                pass
        
        # Also include any raw emails parsed from standard locations if needed, but sent_emails_set has them
        # Let's delete verifications not in this set
        cursor.execute("SELECT email FROM email_verifications")
        all_verified = cursor.fetchall()
        deleted_verifications = 0
        for row in all_verified:
            email = row[0].lower()
            if email not in sent_emails_set:
                cursor.execute("DELETE FROM email_verifications WHERE LOWER(email) = ?", (email,))
                deleted_verifications += cursor.rowcount

        # 5. Commit changes
        conn.commit()

        # 6. Reclaim space using VACUUM
        print("\nVacuuming database to reclaim space...")
        cursor.execute("VACUUM")

        # 7. Fetch counts after
        cursor.execute("SELECT COUNT(*) FROM companies")
        after_companies = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM outreach_emails")
        after_emails = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM email_verifications")
        after_verifications = cursor.fetchone()[0]

        print("\n--- AFTER CLEANUP ---")
        print(f"Remaining Companies: {after_companies} (Deleted: {deleted_companies})")
        print(f"Remaining Outreach Emails: {after_emails} (Deleted: {deleted_emails})")
        print(f"Remaining Email Verifications: {after_verifications} (Deleted: {deleted_verifications})")
        print("\nCleanup completed successfully!")

    except Exception as e:
        conn.rollback()
        print(f"\n[ERROR] Transaction failed, rolled back changes. Details: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    clean_database()
