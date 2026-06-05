import requests
import json
import os
import random
import re
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# ================== CONFIG (GLOBAL) ==================
username = os.environ.get("NAUKRI_USERNAME", "")
password = os.environ.get("NAUKRI_PASSWORD", "")

# Professional headlines generated from resume.txt
HEADLINES = [
    'Senior Full-Stack Developer | Angular (14-19) | .NET Core | Node.js | Immediate Joiner',
    'Senior Full-Stack Developer | Expert in Angular, .NET Core & Node.js | 4.5+ Yrs Exp',
    'Senior Full-Stack Engineer | Enterprise SaaS & Cloud Architecture | Active Seeker',
    'Senior Software Engineer | Specialized in FinTech & LegalTech SaaS | Full-Stack',
    'Senior Full-Stack Developer | Angular, C#, Node.js & Azure DevOps | Immediate Joiner',
    'Senior Full-Stack Developer | .NET Core & Angular Specialist | Pune / Remote',
    'Senior Software Engineer | Building AI-Driven SaaS & Web Solutions | Full-Stack',
    'Senior Software Developer (4.5+ Years) | Angular, C#, Node.js & Microservices',
    'Senior Full-Stack Engineer | Building Enterprise Applications with .NET Core & Angular',
    'Senior Developer | Angular 19, .NET Core & High-Performance Web Systems',
    'Sr. Full-Stack Developer | SaaS & Fintech Expert | Angular / .NET / Node.js',
    'Senior Software Developer | Cloud Infrastructure | CI/CD Pipelines | Full-Stack'
]

def get_mutated_headline():
    """ Picks a headline and applies slight variations to keep it unique. """
    base = random.choice(HEADLINES)
    
    seps = [' | ', ' - ', ' / ', ' | ', ' * ']
    new_sep = random.choice(seps)
    
    parts = re.split(r' \| | / | - | \* ', base)
    
    title = parts[0]
    skills = [p.strip() for p in parts[1:] if p.strip()]
    random.shuffle(skills)
    
    if 'Senior' in title and random.random() > 0.5:
        title = title.replace('Senior', 'Sr.')
    elif 'Sr.' in title and random.random() > 0.5:
        title = title.replace('Sr.', 'Senior')
        
    mutated = new_sep.join([title] + skills)
    return mutated[:249].strip()


# ================== LOGIN CLIENT ==================
class NaukriLoginClient:
    LOGIN_URL = "https://www.naukri.com/central-login-services/v1/login"

    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.session = requests.Session()

    def _get_headers(self):
        return {
            "accept": "application/json",
            "appid": "105",
            "clientid": "d3skt0p",
            "content-type": "application/json",
            "referer": "https://www.naukri.com/nlogin/login",
            "systemid": "jobseeker",
            "user-agent": "Mozilla/5.0",
            "x-requested-with": "XMLHttpRequest",
        }

    def _get_payload(self):
        return {
            "username": self.username,
            "password": self.password
        }

    def login(self):
        response = self.session.post(
            self.LOGIN_URL,
            headers=self._get_headers(),
            json=self._get_payload()
        )
        response.raise_for_status()
        print("Login status:", response.status_code)
        return response

    def get_cookies(self):
        return self.session.cookies.get_dict()

    def get_bearer_token(self):
        return self.get_cookies().get("nauk_at")

    def fetch_profile_id(self):
        resp = self.session.get(
            "https://www.naukri.com/cloudgateway-mynaukri/resman-aggregator-services/v0/users/self/dashboard",
            headers={
                "accept": "application/json",
                "appid": "105",
                "clientid": "d3skt0p",
                "systemid": "Naukri",
                "user-agent": "Mozilla/5.0",
                "authorization": f"Bearer {self.get_bearer_token()}",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        profile_id = data.get("dashBoard", {}).get("profileId") or data.get("profileId")
        if not profile_id:
            raise Exception("Profile ID not found")
        print("Profile ID:", profile_id)
        return profile_id


# ================== MAIN ==================
def update_headline(client, profile_id, token) -> dict:
    """
    Updates the Naukri Profile Headline to bump profile visibility.
    Assumes the client is already logged in.
    """
    headline = get_mutated_headline()
    print(f'Updating headline to: "{headline}"')

    profile_update_url = 'https://www.naukri.com/cloudgateway-mynaukri/resman-aggregator-services/v1/users/self/fullprofiles'
    
    headers = {
        'Content-Type': 'application/json',
        'appid': '105',
        'clientid': 'd3skt0p',
        'systemid': '105',
        'x-requested-with': 'XMLHttpRequest',
        'referer': 'https://www.naukri.com/mnjuser/profile?id=&altresid',
        'Accept': 'application/json',
        'User-Agent': 'Mozilla/5.0',
        'x-http-method-override': 'PUT',
        'origin': 'https://www.naukri.com',
        'authorization': f'Bearer {token}'
    }

    payload = {
        "profile": {"resumeHeadline": headline},
        "profileId": profile_id
    }

    try:
        resp = client.session.post(
            profile_update_url,
            headers=headers,
            json=payload
        )
        resp.raise_for_status()
    except Exception as e:
        return {"success": False, "error": f"Profile update failed: {e}"}

    return {
        "success": True,
        "message": f"Headline updated to: {headline}"
    }


# ================== HANDLER (Single Run) ==================
def handler(event, context):
    print("Cron job started (Single Run)")
    
    if not username or not password:
        return {"status": {"success": False, "error": "Username/password missing"}}
        
    client = NaukriLoginClient(username, password)
    try:
        client.login()
    except Exception as e:
        return {"status": {"success": False, "error": f"Login failed: {e}"}}

    token = client.get_bearer_token()
    if not token:
        return {"status": {"success": False, "error": "Bearer token missing"}}

    profile_id = client.fetch_profile_id()
    
    return {
        "status": update_headline(client, profile_id, token),
        "message": "Cron executed successfully"
    }


# ================== CONTINUOUS RUNNER ==================
def sleep_until_next_window():
    """ Sleeps until the next optimal recruiter sourcing window in India. """
    now = datetime.now()
    # Windows in hours/minutes (9:30 AM, 2:00 PM, 5:30 PM IST)
    windows = [(9, 30), (14, 0), (17, 30)]
    
    next_run = None
    for h, m in windows:
        candidate = now.replace(hour=h, minute=m, second=0, microsecond=0)
        if candidate > now:
            next_run = candidate
            break
            
    if not next_run:
        # If all windows passed today, schedule for 9:30 AM tomorrow
        next_run = now.replace(hour=9, minute=30, second=0, microsecond=0) + timedelta(days=1)
        
    sleep_seconds = (next_run - now).total_seconds()
    # Add a random jitter of +/- 10 minutes (600 seconds) to make the schedule look completely natural
    jitter = random.randint(-600, 600)
    sleep_seconds = max(60, sleep_seconds + jitter)
    
    print(f"Next update scheduled at: {next_run.strftime('%Y-%m-%d %H:%M:%S')} (in {sleep_seconds // 3600:.0f}h {(sleep_seconds % 3600) // 60:.0f}m)")
    time.sleep(sleep_seconds)

def continuous_runner():
    print("Starting continuous profile updater...")
    
    if not username or not password:
        print("Error: Username/password missing in .env")
        return
        
    # Login once
    client = NaukriLoginClient(username, password)
    try:
        client.login()
    except Exception as e:
        print(f"Login failed: {e}")
        return

    token = client.get_bearer_token()
    if not token:
        print("Error: Bearer token missing")
        return

    profile_id = client.fetch_profile_id()
    print(f"Successfully connected! Profile ID: {profile_id}")
    
    while True:
        try:
            result = update_headline(client, profile_id, token)
            if not result.get("success") and ("401" in result.get("error", "") or "Unauthorized" in result.get("error", "")):
                print("Session expired or token invalid (401). Re-authenticating...")
                client = NaukriLoginClient(username, password)
                client.login()
                token = client.get_bearer_token()
                profile_id = client.fetch_profile_id()
                # Retry the headline update with fresh credentials
                result = update_headline(client, profile_id, token)

            if result.get("success"):
                print(f"SUCCESS: {result['message']} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                print(f"FAILED: {result.get('error')}")
        except Exception as e:
            print(f"Error during update: {e}")
            
        # Sleep until the next recruiter peak activity window instead of rapid-fire updates
        sleep_until_next_window()


# ================== EXECUTION ==================
if __name__ == "__main__":
    # If run directly from the terminal, start the continuous loop
    continuous_runner()
