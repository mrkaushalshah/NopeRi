import logging
from datetime import datetime
from src.models.models import Job
from src.client.naukri_client import NaukriLoginClient
from src.exceptions.exceptions import NaukriAuthError, NaukriParseError
import json
from src.config.constants import RECOMMENDED_JOBS_URL, JOB_SEARCH_URL, APPLY_JOB_URL
import re

logger = logging.getLogger(__name__)

APPLY_SRC_MAP = {
    "recommended": ("drecomm_apply", "--drecomm_apply-1-F-0-1--{sid}-"),
    "search":      ("srp",           "--srp-1-F-0-1--{sid}-"),
}

class NaukriJobClient:
    def __init__(self, login_client: NaukriLoginClient, ai_handler=None, use_pool: bool = False):
        if not login_client.naukri_session:
            raise NaukriAuthError("Login required")

        self._client = login_client
        self.context = login_client.naukri_session.context # Playwright BrowserContext
        self.request = self.context.request # Playwright APIRequestContext
        self.ai_handler = ai_handler

    def _parse_job(self, raw: dict) -> Job:
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

    def _build_seo_key(self, keyword: str, location: str, page: int) -> str:
        kw_slug = keyword.strip().lower().replace(".", "-dot-").replace(" ", "-").replace("+", "-").strip("-")
        if location.strip():
            loc_slug = location.strip().lower().replace(" ", "-")
            return f"{kw_slug}-jobs-in-{loc_slug}-{page}"
        return f"{kw_slug}-jobs-{page}"

    def format_jobs(self, raw_jobs):
        formatted = []
        for job in raw_jobs:
            exp = sal = loc = ""
            for item in job.get("placeholders", []):
                if item.get("type") == "experience": exp = item.get("label")
                elif item.get("type") == "salary": sal = item.get("label")
                elif item.get("type") == "location": loc = item.get("label")
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

    async def get_job_details(self, job_id: str, sid: str = ""):
        if not job_id: raise ValueError("job_id is required")
        if not sid: sid = datetime.utcnow().strftime("%Y%m%d%H%M%S") + "0000000"
        
        url = f"https://www.naukri.com/jobapi/v1/job/{job_id}"
        params = {"microsite": "y", "src": "jobsearchDesk", "sid": sid, "xp": "1", "px": "1"}
        
        headers = self._client._build_headers(auth=True)
        headers.update({
            "appid": "121",
            "systemid": "Naukri",
            "clientid": "d3skt0p",
            "accept": "application/json",
            "referer": "https://www.naukri.com/",
            "sec-fetch-site": "same-origin",
            "sec-fetch-mode": "cors",
            "sec-fetch-dest": "empty",
        })
        
        res = await self.request.get(url, headers=headers, params=params)
        
        if res.status in (401, 403):
            data = await res.json()
            msg = data.get("message", "Auth failed") if data else await res.text()
            raise NaukriAuthError(msg)
            
        if not res.ok:
            raise NaukriParseError(f"Job details fetch failed: {res.status} — {await res.text()}")
            
        return await res.json()

    async def apply_job(self, job: Job, mandatory_skills: list[str] = None, optional_skills: list[str] = None, sid: str = "", source: str = "recommended"):
        if not job.job_id: raise ValueError("Invalid job_id")
        if not sid: sid = datetime.utcnow().strftime("%Y%m%d%H%M%S") + "0000000"

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
        }
        
        headers = self._client._build_headers(auth=True)
        headers.update({
            "appid": "121",
            "systemid": "jobseeker",
            "clientid": "d3skt0p",
            "accept": "application/json",
        })

        res = await self.request.post(APPLY_JOB_URL, headers=headers, data=payload)
        
        if res.status in (401, 403):
            try:
                data = await res.json()
                msg = data.get("message", "Auth failed")
            except:
                msg = await res.text()
            raise NaukriAuthError(msg)
            
        if not res.ok:
            raise NaukriParseError(f"Apply failed: {res.status} — {await res.text()}")
            
        return await res.json()

    async def handle_ai_questionnaire_and_apply(self, job, questionnaire, sid, mandatory_skills=None, optional_skills=None, source="recommended"):
        if not self.ai_handler:
            return {"success": False, "error": "AIHandler missing"}

        job_details = await self.get_job_details(job.job_id, sid)
        jd = job_details.get("jobDetails", {}).get("jobDescription", "")
        
        answers = self.ai_handler.solve_questionnaire(job_title=job.title, job_description=jd, questionnaire=questionnaire)
        clean_answers = {}
        if answers:
            for k, v in answers.items():
                clean_answers[k] = re.sub(r'<[^>]+>', '', str(v)).strip()

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
            "applyData": { job.job_id: { "answers": clean_answers } }
        }

        headers = self._client._build_headers(auth=True)
        res = await self.request.post(APPLY_JOB_URL, headers=headers, data=payload)
        
        if not res.ok:
            return {"success": False, "error": await res.text()}
            
        try:
            res_json = await res.json()
            res_json["ai_answers"] = clean_answers
            res_json["questionnaire"] = questionnaire
            return res_json
        except Exception:
            return {"success": False, "error": "Invalid JSON response"}

    async def search_jobs(self, keyword: str, location: str = "", page: int = 1, job_age: int = 1, experience: int = 2, results_per_page: int = 20, lat_long: str = "", sort_by: str = "date") -> list[Job]:
        url = JOB_SEARCH_URL
        seo_key = self._build_seo_key(keyword, location, page)

        params = {
            "noOfResults":      str(results_per_page),
            "urlType":          "search_by_keyword",
            "searchType":       "adv",
            "keyword":          keyword,
            "k":                keyword,
            "pageNo":           str(page),
            "experience":       str(experience),
            "jobAge":           str(job_age),
            "location":         location,
            "l":                location,
            "sortType":         sort_by,
            "nignbevent_src":   "jobsearchDeskGNB",
            "seoKey":           seo_key,
            "src":              "jobsearchDesk",
            "latLong":          lat_long,
        }

        headers = self._client._build_headers(auth=True)
        headers.update({
            "authority":        "www.naukri.com",
            "accept":           "application/json",
            "appid":            "121",
            "referer":          "https://www.naukri.com/",
        })

        # Notice we are no longer sending `nkparam` header at all. Playwright/Crawlee context handles it inherently, 
        # or the WAF tokens just pass through without manual JS evaluation.
        res = await self.request.get(url, headers=headers, params=params)

        if res.status == 403:
            raise NaukriAuthError("403 Forbidden — Playwright context failed to bypass WAF")
        if res.status == 406:
            return []
        if not res.ok:
            raise NaukriParseError(f"Search failed: {res.status} — {await res.text()}")

        data = await res.json()
        raw_jobs = data.get("jobDetails") or data.get("jobs") or data.get("list") or []

        if not raw_jobs:
            return []

        return [self._parse_job(j) for j in raw_jobs]