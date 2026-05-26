import logging
from datetime import datetime
from src.models.models import Job
from src.client.naukri_client import NaukriLoginClient
from src.exceptions.exceptions import NaukriAuthError, NaukriParseError
from src.utils.request_helper import with_exponential_retry
import json
from src.utils.nkparam_generator import generate_nkparam
from src.config.constants import RECOMMENDED_JOBS_URL,JOB_SEARCH_URL,APPLY_JOB_URL
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
_handler = logging.StreamHandler()
_handler.setFormatter(logging.Formatter("%(asctime)s  %(levelname)-8s  %(message)s", datefmt="%H:%M:%S"))
logger.addHandler(_handler)

APPLY_SRC_MAP = {
    "recommended": ("drecomm_apply", "--drecomm_apply-1-F-0-1--{sid}-"),
    "search":      ("srp",           "--srp-1-F-0-1--{sid}-"),
}






# ---------------------------------------------------------------------------
# NaukriJobClient
#
# Thin client over Naukri internal APIs using an authenticated session from
# NaukriLoginClient. Handles search, recommendations, and apply workflows.
#
# Responsibilities:
#   - Build correct headers (auth / non-auth)
#   - Generate SEO keys for search endpoint
#   - Attach required nkparam header
#   - Parse raw API responses into Job model
#   - Normalize inconsistent fields (placeholders, tags, etc.)
#   - Handle common failure cases (403, 406, bad JSON)
#
#
# ---------------------------------------------------------------------------
# nkparam (required for /jobapi/v3/search)
#
# `nkparam` is a request header expected by Naukri search API. It is generated
# in their frontend JS (obfuscated) and validated server-side. If invalid or
# missing → API returns 403.
#
# It is NOT tied to login session directly, but to how frontend signs requests.
#
#
# ---------------------------------------------------------------------------
# Supported modes
#
# 1) Generator mode (default),
#    - Uses: generate_nkparam("srp")
#    - Generates fresh token per request
#    - Preferred if generator logic is correct
#
# 2) Pool mode (optional)
#    - Uses pre-captured tokens (self.pool)
#    - Rotates via pool_idx
#    - Useful when generator breaks or for fallback
#
# Toggle via:
#    NaukriJobClient(login_client, use_pool=True)
#
#
# ---------------------------------------------------------------------------
# Token pool notes (original reference)
#
# Naukri's job-search endpoint (/jobapi/v3/search) requires a signed
# request header called `nkparam`. This token is generated inside
# Naukri's obfuscated JS bundle and changes every browser session.
# Without a valid token the API returns 403 Forbidden.
#
# HOW TO HARVEST TOKENS:
#   1. Run: (it uses selenium)
#         python get_Nkparam.py
#      Opens Chrome, captures nkparam from network logs,
#      appends tokens to nkPool.txt
#
#   2. Stop after collecting enough tokens:
#         ~100 for light usage
#         ~1000 for heavy usage
#
# HOW TO USE:
#   self.pool = open("nkPool.txt").read().splitlines()
#
# TOKEN EXPIRY:
#   Tokens usually work for a few hours.
#   On 403 → rotate token
#   If all fail → regenerate pool
#
# NOTE:
#   Do not commit tokens. Add nkPool.txt to .gitignore.
#
#
# ---------------------------------------------------------------------------
# Design notes
#
# - Helpers are kept inside class (no globals)
# - _get_nkparam() abstracts token source
# - search path depends on correct nkparam only
# - rest of client is standard request/parse layer
#
# ---------------------------------------------------------------------------




class NaukriJobClient:

    def __init__(self, login_client: NaukriLoginClient, ai_handler=None, use_pool: bool = False):
        if not login_client.session:
            raise NaukriAuthError("Login required")

        self._session = login_client.session
        # self._session = login_client.session if login_client else None
        self._client = login_client
        self.ai_handler = ai_handler

        self.pool_idx = 0
        self.use_pool = use_pool

        self.pool = [
            "sa9chfJkrXEpn3Zt7rAPaAOb6gAWNSFzzmPQEc6tLSMzytUGPxrGDqiKJyjvBAHGIYPhbDRBDHMad071ZRZlZA=="
        ]

    # ---------------------------------------------------------------------------
    # Helpers (moved inside class)
    # ---------------------------------------------------------------------------

    def _parse_job(self, raw: dict) -> Job:
        # Check if v2 or v3
        if "post" in raw and "companyName" in raw: # v2
            exp = f"{raw.get('minExp', '0')} - {raw.get('maxExp', '0')} years"
            sal = f"{raw.get('minSal', '0')} - {raw.get('maxSal', '0')} {raw.get('currencySal', 'INR')}"
            tags = [t.strip() for t in raw.get("keywords", "").split(",")] if raw.get("keywords") else []
            return Job(
                job_id=str(raw.get("jobId", "")),
                title=raw.get("post", "N/A"),
                company=raw.get("companyName", "N/A"),
                location=raw.get("city", "N/A"),
                experience=exp,
                salary=sal,
                posted_date=raw.get("addDate", "N/A"),
                apply_link=raw.get("urlStr", ""),
                description=raw.get("jobDesc", ""),
                tags=tags
            )
        
        # v3 fallback
        return Job(
            job_id=str(raw.get("jobId") or raw.get("id") or ""),
            title=raw.get("title") or raw.get("jobTitle") or "N/A",
            company=raw.get("companyName") or raw.get("company") or "N/A",
            location=next((p["label"] for p in raw.get("placeholders", []) if p.get("type") == "location"), "N/A"),
            experience=raw.get("experienceText") or raw.get("experience") or "N/A",
            salary=raw.get("salaryDetail") or raw.get("salary") or "Not disclosed",
            posted_date=raw.get("footerPlaceholderLabel") or raw.get("postedDate") or "N/A",
            apply_link=raw.get("jdURL") or f"https://www.naukri.com/job-listings-{raw.get('jobId', '')}",
            description=raw.get("jobDescription") or "",
            tags=[t.strip() for t in raw.get("tagsAndSkills", "").split(",")] if raw.get("tagsAndSkills") else [],
        )

    def _cluster_dates(self) -> dict:
        now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
        return {
            "apply": now,
            "preference": now,
            "profile": now,
            "similar_jobs": now,
        }

    def _headers(self):
        return self._client._build_headers(auth=True)

    def _build_seo_key(self, keyword: str, location: str, page: int) -> str:
        kw_slug = (
            keyword.strip().lower()
            .replace(".", "-dot-")
            .replace(" ", "-")
            .replace("+", "-")
        )
        kw_slug = kw_slug.strip("-")

        if location.strip():
            loc_slug = location.strip().lower().replace(" ", "-")
            return f"{kw_slug}-jobs-in-{loc_slug}-{page}"
        else:
            return f"{kw_slug}-jobs-{page}"

    def format_jobs(self, raw_jobs):
        formatted = []

        for job in raw_jobs:
            exp = sal = loc = ""

            for item in job.get("placeholders", []):
                if item.get("type") == "experience":
                    exp = item.get("label")
                elif item.get("type") == "salary":
                    sal = item.get("label")
                elif item.get("type") == "location":
                    loc = item.get("label")

            formatted.append({
                "title": job.get("title"),
                "company": job.get("companyName"),
                "experience": exp,
                "location": loc,
                "salary": sal,
                "skills": job.get("tagsAndSkills", "").split(","),
                "job_url": "https://www.naukri.com" + job.get("jdURL", ""),
                "posted": job.get("footerPlaceholderLabel")
            })

        return formatted

    def _get_nkparam(self, page_type: str = "srp", app_id: str = "121"):
        if self.use_pool:
            token = self.pool[self.pool_idx % len(self.pool)]
            self.pool_idx += 1
            return token
        return generate_nkparam(page_type, app_id)

    def _search_headers(self):
        headers = self._client._build_headers(auth=True)
        headers.update({
            "authority":        "www.naukri.com",
            "accept":           "application/json",
            "accept-encoding":  "gzip, deflate, br, zstd",
            "accept-language":  "en-US,en;q=0.9",
            "appid":            "121",
            "gid":              "LOCATION,INDUSTRY,EDUCATION,FAREA_ROLE",
            "nkparam":          self._get_nkparam("srp", "121"),

            "referer":          "https://www.naukri.com/",
            "sec-ch-ua":        '"Google Chrome";v="123", "Not:A-Brand";v="8", "Chromium";v="123"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest":   "empty",
            "sec-fetch-mode":   "cors",
            "sec-fetch-site":   "same-origin",
            "x-requested-with": "XMLHttpRequest"
        })
        return headers

    # ------------------------------------------------------------------
    # Apply Job
    # ------------------------------------------------------------------


    # ------------------------------------------------------------------
# Get Job Details
# ------------------------------------------------------------------
    def get_job_details(self, job_id: str, sid: str = ""):
        if not job_id:
            raise ValueError("job_id is required")

        if not sid:
            sid = datetime.utcnow().strftime("%Y%m%d%H%M%S") + "0000000"

        url = f"https://www.naukri.com/jobapi/v1/job/{job_id}"

        params = {
            "microsite": "y",
            "src": "jobsearchDesk",
            "sid": sid,
            "xp": "1",
            "px": "1",
        }

        headers = self._client._build_headers(auth=True)
        headers.update({
            "appid": "121",
            "systemid": "Naukri",
            "clientid": "d3skt0p",
            "accept": "application/json",
            "nkparam": self._get_nkparam("jd", "121"),
            "referer": "https://www.naukri.com/",
            "sec-fetch-site": "same-origin",
            "sec-fetch-mode": "cors",
            "sec-fetch-dest": "empty",
        })
        logger.debug("Fetching job details for job_id=%s sid=%s", job_id, sid)

        res = self._session.get(url, headers=headers, params=params)

        if res.status_code in (401, 403):
            try:
                msg = res.json().get("message", "Auth failed")
            except Exception:
                msg = res.text
            raise NaukriAuthError(msg)

        if not res.ok:
            raise NaukriParseError(f"Job details fetch failed: {res.status_code} — {res.text}")

        try:
            return res.json()
        except Exception:
            raise NaukriParseError(f"Invalid JSON response: {res.text}")

    def apply_job(
        self,
        job: Job,
        mandatory_skills: list[str] = None,
        optional_skills:  list[str] = None,
        sid:    str = "",
        source: str = "recommended",   # "recommended" | "search"
    ):
        url = APPLY_JOB_URL #"https://www.naukri.com/cloudgateway-workflow/workflow-services/apply-workflow/v1/apply"

        if not job.job_id:
            raise ValueError("Invalid job_id")

        if not sid:
            sid = datetime.utcnow().strftime("%Y%m%d%H%M%S") + "0000000"

        apply_src, logstr_template = APPLY_SRC_MAP.get(source, APPLY_SRC_MAP["recommended"])
        logstr = logstr_template.format(sid=sid)


        payload = {
        "strJobsarr":       [job.job_id],
        "logstr":           logstr,
        "flowtype":         "show",
        "crossdomain":      True,
        "jquery":           1,
        "rdxMsgId":         "",
        "chatBotSDK":       True,
        "mandatory_skills": mandatory_skills or [],
        "optional_skills":  optional_skills or [],
        "applyTypeId":      "107",
        "closebtn":         "y",
        "applySrc":         apply_src,
        "sid":              sid,
        "mid":              "",
    }
        headers = self._client._build_headers(auth=True)
        headers.update({
            "appid":     "121",           # different from search (109) — apply uses 121
            "systemid":  "jobseeker",
            "clientid":  "d3skt0p",
            "accept":    "application/json",
        })

        logger.debug("Applying to job_id=%s sid=%s", job.job_id, sid)

        res = self._session.post(url, headers=headers, json=payload)

        if res.status_code in (401, 403):
            try:
                msg = res.json().get("message", "Auth failed")
            except Exception:
                msg = res.text
            raise NaukriAuthError(msg)

        if not res.ok:
            raise NaukriParseError(f"Apply failed: {res.status_code} — {res.text}")

        try:
            data = res.json()
        except Exception:
            raise NaukriParseError(f"Invalid JSON response: {res.text}")

       # logger.debug("Apply response: %s", data)
        return data

        # ------------------------------------------------------------------
    # Recommended jobs
    # ------------------------------------------------------------------

    def get_recommended_jobs(self) -> list[Job]:
        url = RECOMMENDED_JOBS_URL
        res = self._session.post(
            url,
            headers=self._headers(),
            json={
                "clusterId": None,
                "src": "recommClusterApi",
                "clusterSplitDate": self._cluster_dates(),
            },
        )

        if not res.ok:
            raise NaukriParseError(f"Recommended jobs fetch failed: {res.status_code}")

        data = res.json()
        raw_jobs = data.get("jobDetails") or []

        print(raw_jobs[:5])
        return [self._parse_job(j) for j in raw_jobs]

    # ------------------------------------------------------------------
    # Search jobs
    # ------------------------------------------------------------------
    


    def handle_ai_questionnaire_and_apply(
        self,
        job,
        questionnaire,
        sid,
        mandatory_skills=None,
        optional_skills=None,
        source="recommended"
    ):
        """Uses AI to solve the questionnaire and then applies for the job."""
        if not self.ai_handler:
            logger.error("AIHandler not provided to NaukriJobClient. Cannot solve questionnaire.")
            return {"success": False, "error": "AIHandler missing"}

        # Get job details for better context (JD)
        job_details = self.get_job_details(job.job_id, sid)
        jd = job_details.get("jobDetails", {}).get("jobDescription", "")
        
        # Solve using AI
        answers = self.ai_handler.solve_questionnaire(
            job_title=job.title,
            job_description=jd,
            questionnaire=questionnaire
        )

        if not answers:
            logger.warning("AI failed to generate answers for job %s", job.job_id)

        # Sanitize answers to prevent Akamai WAF from blocking HTML tags as XSS
        import re
        clean_answers = {}
        for k, v in answers.items():
            if isinstance(v, str):
                clean_answers[k] = re.sub(r'<[^>]+>', '', v).strip()
            else:
                clean_answers[k] = v

        logger.debug("AI Generated answers: %s", clean_answers)

        # ---------------- FINAL APPLY ----------------
        apply_src, logstr_template = APPLY_SRC_MAP.get(source, APPLY_SRC_MAP["recommended"])
        logstr = logstr_template.format(sid=sid)

        payload = {
            "strJobsarr": [job.job_id],
            "logstr": logstr,
            "flowtype": "show",
            "crossdomain": True,
            "jquery": 1,
            "rdxMsgId": "",
            "chatBotSDK": True,
            "mandatory_skills": mandatory_skills or [],
            "optional_skills":  optional_skills or [],
            "applyTypeId":      "107",
            "closebtn":         "y",
            "applySrc":         apply_src,
            "sid":              sid,
            "mid":              "",
            "applyData": {
                job.job_id: {
                    "answers": clean_answers
                }
            }
        }

        headers = self._client._build_headers(auth=True)
        res = self._session.post(APPLY_JOB_URL, headers=headers, json=payload)

        if not res.ok:
            logger.debug("Apply failed: %s", res.text)
            return {"success": False, "error": res.text}

        try:
            res_json = res.json()
            res_json["ai_answers"] = clean_answers
            res_json["questionnaire"] = questionnaire
            return res_json
        except Exception:
            return {"success": False, "error": "Invalid JSON response", "ai_answers": clean_answers, "questionnaire": questionnaire}
    


    def search_jobs(
        self,
        keyword: str,
        location: str = "",
        page: int = 1,
        job_age: int = 1,
        experience: int = 2,
        results_per_page: int = 20,
        lat_long: str = "",
        sort_by: str = "date"
    ) -> list[Job]:

        url = JOB_SEARCH_URL
        seo_key = self._build_seo_key(keyword, location, page)

        params = {
            "noOfResults":      results_per_page,
            "urlType":          "search_by_keyword",
            "searchType":       "adv",
            "keyword":          keyword,
            "k":                keyword,
            "pageNo":           page,
            "experience":       experience,
            "jobAge":           job_age,
            "location":         location,
            "l":                location,
            "sortType":         sort_by,

            "nignbevent_src":   "jobsearchDeskGNB",
            "seoKey":           seo_key,
            "src":              "jobsearchDesk",
            "latLong":          lat_long,
        }

        res = self._session.get(url, headers=self._search_headers(), params=params)

        if res.status_code == 403:
            raise NaukriAuthError("403 Forbidden — nkparam token likely expired")

        if res.status_code == 406:
            logger.debug("406 Validation error: %s", res.text)
            return []

        if not res.ok:
            raise NaukriParseError(f"Search failed: {res.status_code} — {res.text}")

        data = res.json()
        raw_jobs = data.get("jobDetails") or data.get("jobs") or data.get("list") or []

        oc_list = self.format_jobs(raw_jobs)

        if not raw_jobs:
            logger.debug("No jobs returned for keyword=%r page=%d", keyword, page)
            return []

        return [self._parse_job(j) for j in raw_jobs]