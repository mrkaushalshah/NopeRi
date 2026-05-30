import sqlite3
import json
import uuid
from datetime import datetime

#===========================sqlite support for nkparam token ===============
class NkparamDB:
    def __init__(self, db_path="nkparams.db"):
        self.db_path = db_path
        self._init_db()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        conn = self._connect()
        cursor = conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS nkparams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nkparam TEXT UNIQUE,
            is_active INTEGER DEFAULT 1
        )
        """)

        conn.commit()
        conn.close()


    def add_nkparam(self, nkparam):
        conn = self._connect()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "INSERT OR IGNORE INTO nkparams (nkparam, is_active) VALUES (?, 1)",
                (nkparam,)
            )
            conn.commit()
        finally:
            conn.close()


    def get_nkparam(self):
        conn = self._connect()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT id, nkparam 
                FROM nkparams 
                WHERE is_active = 1 
                LIMIT 1
            """)
            row = cursor.fetchone()

            if row:
                nk_id, nkparam = row

                cursor.execute(
                    "UPDATE nkparams SET is_active = 0 WHERE id = ?",
                    (nk_id,)
                )
                conn.commit()

                return nkparam

            return None

        finally:
            conn.close()


#===========================sqlite support for local outreach engine ===============
class OutreachDB:
    def __init__(self, db_path="outreach.db"):
        self.db_path = db_path
        self.init_db()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        conn = self._connect()
        cursor = conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS companies (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            location TEXT,
            address TEXT,
            distance_km REAL,
            website TEXT,
            google_rating REAL,
            google_place_id TEXT,
            fit_score INTEGER DEFAULT 0,
            fit_reasoning TEXT,
            intelligence_card_json TEXT,
            status TEXT DEFAULT 'discovered',
            search_location TEXT,
            search_radius INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS outreach_emails (
            id TEXT PRIMARY KEY,
            company_id TEXT NOT NULL,
            extracted_emails TEXT,
            email_subject TEXT,
            email_body TEXT,
            sent_status TEXT DEFAULT 'drafted',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (company_id) REFERENCES companies(id)
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS email_verifications (
            email TEXT PRIMARY KEY,
            status TEXT,
            score INTEGER,
            verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        conn.commit()
        conn.close()

    def save_company(self, company_dict):
        conn = self._connect()
        cursor = conn.cursor()
        try:
            company_id = company_dict.get("id", str(uuid.uuid4()))
            cursor.execute("""
                INSERT OR REPLACE INTO companies
                (id, name, location, address, distance_km, website, google_rating,
                 google_place_id, fit_score, fit_reasoning, intelligence_card_json,
                 status, search_location, search_radius, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                company_id,
                company_dict.get("name", ""),
                company_dict.get("location", ""),
                company_dict.get("address", ""),
                company_dict.get("distance_km"),
                company_dict.get("website", ""),
                company_dict.get("google_rating"),
                company_dict.get("google_place_id", ""),
                company_dict.get("fit_score", 0),
                company_dict.get("fit_reasoning", ""),
                json.dumps(company_dict.get("intelligence_card", {})),
                company_dict.get("status", "discovered"),
                company_dict.get("search_location", ""),
                company_dict.get("search_radius", 10),
                datetime.now().isoformat()
            ))
            conn.commit()
            return company_id
        finally:
            conn.close()

    def save_outreach_email(self, email_dict):
        conn = self._connect()
        cursor = conn.cursor()
        try:
            email_id = email_dict.get("id", str(uuid.uuid4()))
            cursor.execute("""
                INSERT OR REPLACE INTO outreach_emails
                (id, company_id, extracted_emails, email_subject, email_body, sent_status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                email_id,
                email_dict.get("company_id", ""),
                json.dumps(email_dict.get("extracted_emails", [])),
                email_dict.get("email_subject", ""),
                email_dict.get("email_body", ""),
                email_dict.get("sent_status", "drafted"),
                datetime.now().isoformat()
            ))
            conn.commit()
            return email_id
        finally:
            conn.close()

    def save_email_verification(self, email, status, score):
        conn = self._connect()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO email_verifications
                (email, status, score, verified_at)
                VALUES (?, ?, ?, ?)
            """, (email, status, score, datetime.now().isoformat()))
            conn.commit()
        finally:
            conn.close()

    def get_email_verification(self, email):
        conn = self._connect()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM email_verifications WHERE email = ?", (email,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_all_email_verifications(self):
        conn = self._connect()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM email_verifications")
            rows = cursor.fetchall()
            return {row["email"]: {"status": row["status"], "score": row["score"]} for row in rows}
        finally:
            conn.close()

    def get_companies(self, search_location=None):
        conn = self._connect()
        cursor = conn.cursor()
        try:
            if search_location:
                cursor.execute(
                    "SELECT * FROM companies WHERE search_location = ? ORDER BY fit_score DESC",
                    (search_location,)
                )
            else:
                cursor.execute("SELECT * FROM companies ORDER BY created_at DESC")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def get_company_with_emails(self, company_id):
        conn = self._connect()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM companies WHERE id = ?", (company_id,))
            company = cursor.fetchone()
            if not company:
                return None
            company_dict = dict(company)

            cursor.execute("SELECT * FROM outreach_emails WHERE company_id = ?", (company_id,))
            emails = cursor.fetchall()
            company_dict["outreach_emails"] = [dict(e) for e in emails]
            return company_dict
        finally:
            conn.close()

    def get_all_with_emails(self, search_location=None):
        companies = self.get_companies(search_location)
        conn = self._connect()
        cursor = conn.cursor()
        try:
            for company in companies:
                cursor.execute(
                    "SELECT * FROM outreach_emails WHERE company_id = ?",
                    (company["id"],)
                )
                emails = cursor.fetchall()
                company["outreach_emails"] = [dict(e) for e in emails]
                if company.get("intelligence_card_json"):
                    try:
                        company["intelligence_card"] = json.loads(company["intelligence_card_json"])
                    except (json.JSONDecodeError, TypeError):
                        company["intelligence_card"] = {}
            return companies
        finally:
            conn.close()

    def update_company_status(self, company_id, status):
        conn = self._connect()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE companies SET status = ? WHERE id = ?",
                (status, company_id)
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def delete_company(self, company_id):
        conn = self._connect()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM outreach_emails WHERE company_id = ?", (company_id,))
            cursor.execute("DELETE FROM companies WHERE id = ?", (company_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def update_email_status(self, email_id, sent_status):
        conn = self._connect()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE outreach_emails SET sent_status = ? WHERE id = ?",
                (sent_status, email_id)
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def get_pipeline_stats(self, search_location=None):
        conn = self._connect()
        cursor = conn.cursor()
        try:
            where = "WHERE search_location = ?" if search_location else ""
            params = (search_location,) if search_location else ()

            cursor.execute(f"SELECT COUNT(*) FROM companies {where}", params)
            total = cursor.fetchone()[0]

            cursor.execute(f"SELECT COUNT(*) FROM companies {where} {'AND' if where else 'WHERE'} website IS NOT NULL AND website != ''", params)
            with_website = cursor.fetchone()[0]

            cursor.execute(f"""
                SELECT COUNT(DISTINCT c.id) FROM companies c
                JOIN outreach_emails e ON c.id = e.company_id
                {where}
            """, params)
            with_emails = cursor.fetchone()[0]

            cursor.execute(f"""
                SELECT COUNT(DISTINCT c.id) FROM companies c
                JOIN outreach_emails e ON c.id = e.company_id
                WHERE e.email_subject IS NOT NULL AND e.email_subject != ''
                {'AND c.search_location = ?' if search_location else ''}
            """, params)
            drafted = cursor.fetchone()[0]

            cursor.execute(f"""
                SELECT COUNT(DISTINCT c.id) FROM companies c
                JOIN outreach_emails e ON c.id = e.company_id
                WHERE e.sent_status = 'sent'
                {'AND c.search_location = ?' if search_location else ''}
            """, params)
            sent = cursor.fetchone()[0]

            return {
                "discovered": total,
                "website_found": with_website,
                "email_found": with_emails,
                "drafted": drafted,
                "sent": sent
            }
        finally:
            conn.close()