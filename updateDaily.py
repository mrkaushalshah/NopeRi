import requests
import json
import os
import random
import re
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ================== CONFIG (GLOBAL) ==================
username = os.environ.get("NAUKRI_USERNAME", "")
password = os.environ.get("NAUKRI_PASSWORD", "")

# Professional headlines generated from resume.txt
HEADLINES = [
    'Senior Full-Stack Developer | Angular 18+ | .NET Core | Node.js | AI Automation',
    'Senior Software Developer | Expert in Angular, .NET Core & Node.js | 4.5+ Yrs Exp',
    'Full-Stack Architect | AI Automation Products | Angular & .NET Core Expert',
    'Senior Software Engineer | Specialized in FinTech & LegalTech SaaS | Full-Stack',
    'Founder & Senior Developer | Building AI-driven Web Solutions | Angular & Node.js',
    'Senior Full-Stack Developer | .NET Core & Angular Specialist | Pune, India',
    'AI Automation Engineer | Senior Full-Stack Developer | Node.js & Angular',
    'Senior Software Developer (4.5+ Years) | Angular, C#, Node.js & AI Specialist',
    'Full-Stack Developer | Building Enterprise SaaS with .NET Core & Angular',
    'Senior Developer | Angular 18, .NET Core & AI-powered Automations',
    'Sr. Full-Stack Developer | SaaS & Fintech Expert | Angular / .NET / Node',
    'Senior Software Developer | Cloud Architecture | AI Workflows | Full-Stack'
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
def continuous_runner():
    import time
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
            if result.get("success"):
                print(f"SUCCESS: {result['message']} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                print(f"FAILED: {result.get('error')}")
        except Exception as e:
            print(f"Error during update: {e}")
            
        # Random sleep between 15 to 45 minutes to simulate natural behavior
        sleep_time = random.randint(900, 2700) 
        print(f"Next update in {sleep_time // 60}m {sleep_time % 60}s\n")
        time.sleep(sleep_time)


# ================== EXECUTION ==================
if __name__ == "__main__":
    # If run directly from the terminal, start the continuous loop
    continuous_runner()
