import json
import os
import re
import requests

class JobFilterPipeline2:

    # ── your stack — AI scores against this ──────────────────────────────────
    MY_STACK = [
        # ── Frontend ─────────────────────────────────────────────────
        "angular", "vue", "vue.js", "typescript", "javascript", "html5", "css3", "tailwindcss", "bootstrap",

        # ── Core backend ──────────────────────────────────────────────
        "node", "node.js", "nodejs", "python", ".net core", ".net", "c#",

        # ── Frameworks ───────────────────────────────────────────────
        "express", "express.js", "fastapi", "flask",

        # ── Databases ────────────────────────────────────────────────
        "sql server", "mysql", "mongodb", "postgresql", "redis", "supabase", "sequelize",

        # ── Cloud & DevOps ───────────────────────────────────────────
        "aws", "azure", "azure devops", "docker", "ci/cd", "github",

        # ── APIs & Messaging ─────────────────────────────────────────
        "rest", "rest api", "restful",

        # ── Automation & Scraping ────────────────────────────────────
        "selenium", "rpa", "automation",

        # ── AI / LLM ─────────────────────────────────────────────────
        "openai", "llm", "ai", "prompt engineering",

        # ── Tools & Practices ────────────────────────────────────────
        "git", "github", "cypress", "jwt", "windows authentication", "s2s auth",
    ]

    # ── hard veto BEFORE ai — title only, zero ambiguity ────────────────────
    VETO_TITLES = [
        "walk-in", "walkin", "walk in",
        "android developer", "ios developer", "flutter developer",
        "vp of", "head of engineering", "head of technology",
        "founder", "tutor", "trainer",
        "data scientist", "ml engineer", "data engineer", "intern", "internship",
        "engineering manager", "etl engineer", "prompt engineer",
        "analyst", "associate is engineer", "infra engineer",
        "observability engineer", "manager",
        "doctor", "mbbs", "md", "ms", "nurse", "medical", "clinical", "hospital"
    ]

    VETO_COMPANIES = {
    "accenture", "wipro", "infosys", "tcs", "cognizant",
    "capgemini", "hcl", "tech mahindra", "mphasis", "hexaware",
    "ltimindtree", "persistent", "birlasoft",
    }

    # ── red flag sniff on description (cheap, pre-ai) ───────────────────────
    # Only the things AI genuinely can't infer from tags alone
    DESC_RED_FLAGS = {
        "walk-in":      r"walk.?in|walkin",
        "venue listed": r"venue\s*:|interview venue|bring your resume|carry your resume",
    }

    SOFTWARE_KEYWORDS = {
        "software", "developer", "engineer", "engineering",
        "backend", "full stack", "fullstack", "frontend", "front-end", "front end",
        "python", "node", "nodejs", "javascript", "typescript",
        "angular", "vue", "c#", ".net", "dotnet",
        "devops", "cloud", "sre", "platform",
        "api", "microservices", "infrastructure",
        "tech lead", "sde", "swe", "mts", "programmer", "react"
    }

    # if ANY of these appear in title → drop it
    FRONTEND_VETO_KEYWORDS = {
        "android", "ios", "flutter", "mobile", "kotlin", "swift",
        "embedded", "firmware",
        "ml engineer", "data engineer", "data scientist","intern", "internship", "lead","Golang","MLops","devops","mlops", "golang"," Web developer - Java Technologies"
        ," Member of Technical Staff - MTS"
    }

    def __init__(
        self,
        openai_api_key,
        cache_file="score_cache.json",
        daily_apply_limit=50,
        min_apply_score=50,
        ai_score_limit=300,
        batch_size=50,
    ):
        self.api_key           = openai_api_key
        self.url               = "https://api.openai.com/v1/chat/completions"
        self.cache_file        = cache_file
        self.daily_apply_limit = daily_apply_limit
        self.min_apply_score   = min_apply_score
        self.ai_score_limit    = ai_score_limit
        self.batch_size        = batch_size
        self.cache             = self._load_cache()

    # =========================================================
    # MAIN
    # =========================================================
    def run(self, jobs):
        print("\nRAW JOBS:", len(jobs))

        jobs = self.normalize_jobs(jobs)
        print("AFTER NORMALIZE:", len(jobs))

        jobs = self.dedup(jobs)
        print("AFTER DEDUP:", len(jobs))

        jobs = self.hard_veto(jobs)
        print("AFTER HARD VETO:", len(jobs))

        jobs = self.experience_filter(jobs)
        print("AFTER EXP FILTER:", len(jobs))

        jobs = self.desc_red_flag_check(jobs)
        print("AFTER RED FLAG CHECK:", len(jobs))

        jobs=self.title_filter(jobs)
        print("AFTER TITLE FILTER:", len(jobs))

        jobs = self.company_veto(jobs)        # ← add here
        print("AFTER COMPANY VETO:", len(jobs))


        jobs = self.tag_presort(jobs)

        jobs = jobs[:self.ai_score_limit]
        print("AFTER LIMIT:", len(jobs))

        jobs = self.ai_score_batch(jobs)

        jobs = self.rank(jobs)
        print("AFTER RANK:", len(jobs))

        jobs = self.select(jobs)
        print("FINAL SELECTED:", len(jobs))

        for j in jobs:
            print(f"  {j.get('ai_score'):>3}  {j.get('title')} @ {j.get('company')}"
                  f"  |  {j.get('ai_reason', '')}")

        return [j["original_job"] for j in jobs]

    # =========================================================
    # NORMALIZE  — tags are the star, keep them clean
    # =========================================================
    def normalize_jobs(self, jobs):
        normalized = []

        for j in jobs:
            job = j if isinstance(j, dict) else j.__dict__

            # days old
            posted   = (job.get("posted_date") or "").lower()
            days_old = 7
            if "today" in posted or "hour" in posted or "just now" in posted:
                days_old = 0
            elif "yesterday" in posted:
                days_old = 1
            else:
                m = re.search(r"(\d+)\s*day", posted)
                if m:
                    days_old = int(m.group(1))
                else:
                    m = re.search(r"(\d+)\s*week", posted)
                    if m:
                        days_old = int(m.group(1)) * 7

            # experience range
            exp = job.get("experience") or ""
            exp_min, exp_max = 0, 10
            nums = re.findall(r"\d+", exp)
            if len(nums) >= 2:
                exp_min, exp_max = int(nums[0]), int(nums[1])
            elif len(nums) == 1:
                exp_min = exp_max = int(nums[0])

            # tags — normalize once, use everywhere
            raw_tags = job.get("tags") or job.get("skills") or []
            if isinstance(raw_tags, str):
                raw_tags = re.split(r"[,;|]", raw_tags)
            tags = [t.strip().lower() for t in raw_tags if t.strip()]

            normalized.append({
                "original_job":   j,
                "job_id":         job.get("job_id"),
                "title":          (job.get("title")       or "").strip(),
                "company":        (job.get("company")     or "").strip(),
                "location":       (job.get("location")    or "").strip(),
                "description":    (job.get("description") or "").strip(),
                "tags":           tags,
                "mandatory_tags": tags[:2],   # site signals these as primary
                "optional_tags":  tags[2:],
                "days_old":       days_old,
                "experience_min": exp_min,
                "experience_max": exp_max,
            })

        return normalized

    # =========================================================
    # DEDUP
    # =========================================================
    def dedup(self, jobs):
        seen, result = set(), []
        for j in jobs:
            job_id = j.get("job_id")
            if job_id is None:
                result.append(j)  # can't dedup without an id, just keep it
                continue
            if job_id in seen:
                continue
            seen.add(job_id)
            result.append(j)
        return result

    # =========================================================
    # HARD VETO  — title only, no ambiguity allowed
    # =========================================================
    def hard_veto(self, jobs):
        clean = []
        for j in jobs:
            title = (j.get("title") or "").lower()
            if any(kw in title for kw in self.VETO_TITLES):
                print(f"  [VETO] {j.get('title')}")
                continue
            clean.append(j)
        return clean

    # =========================================================
    # EXPERIENCE FILTER
    # =========================================================
    def experience_filter(self, jobs):
        return [
            j for j in jobs
            if j.get("experience_min", 0) <= 4
            and j.get("experience_max", 10) > 0
        ]

    # =========================================================
    # DESC RED FLAG CHECK  — one cheap regex pass, nothing more
    # =========================================================
    def desc_red_flag_check(self, jobs):
        clean = []
        for j in jobs:
            desc = (j.get("description") or "").lower()
            flagged = [
                label for label, pat in self.DESC_RED_FLAGS.items()
                if re.search(pat, desc)
            ]
            if flagged:
                print(f"  [RED FLAG {flagged}] {j.get('title')}")
                continue
            clean.append(j)
        return clean

    # =========================================================
    # TAG PRESORT  — rough stack overlap count, no AI cost
    # Keeps best candidates at the front before we hit the limit
    # =========================================================

    def title_filter(self, jobs):
        result = []
        for j in jobs:
            title = (j.get("title") or "").lower()

            # must have at least one software keyword
            if not any(kw in title for kw in self.SOFTWARE_KEYWORDS):
                print(f"  [TITLE FILTER - not software] {j.get('title')}")
                continue

            # must NOT be frontend/mobile/ml
            if any(kw in title for kw in self.FRONTEND_VETO_KEYWORDS):
                print(f"  [TITLE FILTER - frontend/mobile] {j.get('title')}")
                continue

            result.append(j)
        return result


    def company_veto(self, jobs):
        clean = []
        for j in jobs:
            company = (j.get("company") or "").lower()
            if any(vc in company for vc in self.VETO_COMPANIES):
                print(f"  [COMPANY VETO] {j.get('title')} @ {j.get('company')}")
                continue
            clean.append(j)
        return clean

    def tag_presort(self, jobs):
        my_stack = set(self.MY_STACK)

        def overlap(j):
            tags     = set(j.get("tags", []))
            mandatory_hit = sum(1 for t in j.get("mandatory_tags", []) if t in my_stack)
            total_hit     = len(tags & my_stack)
            recency_bonus = max(0, 7 - j.get("days_old", 7))
            # mandatory tags weighted 3x — they represent the job's core ask
            return mandatory_hit * 3 + total_hit + recency_bonus

        return sorted(jobs, key=overlap, reverse=True)

    # =========================================================
    # AI SCORING  — tags go in, score + reason come out
    # =========================================================
    def ai_score_batch(self, jobs):
        result = []
        for i in range(0, len(jobs), self.batch_size):
            batch  = jobs[i:i + self.batch_size]
            scores = self._call_ai(batch)
            for idx, job in enumerate(batch):
                jid  = str(job.get("job_id") or "")
                data = self.cache.get(jid) if jid else None

                if not data:
                    data = scores.get(str(idx), {"score": 0, "reason": "no response"})
                    if not isinstance(data.get("score"), int):
                        data = {"score": 0, "reason": "parse error"}
                    if jid:
                        self.cache[jid] = data

                job["ai_score"]  = data.get("score", 0)
                job["ai_reason"] = data.get("reason", "")
                result.append(job)

        self._save_cache()
        return result

    def _call_ai(self, jobs):
        job_block = ""
        for i, j in enumerate(jobs):
            mandatory = ", ".join(j.get("mandatory_tags", [])) or "none"
            optional  = ", ".join(j.get("optional_tags",  [])) or "none"
            exp       = f"{j.get('experience_min', 0)}-{j.get('experience_max', 10)} yrs"

            job_block += (
                f"Job {i}:\n"
                f"  Title:     {j.get('title')}\n"
                f"  Company:   {j.get('company')}\n"
                f"  Mandatory: {mandatory}\n"
                f"  Optional:  {optional}\n"
                f"  Exp:       {exp}\n"
                f"  Days old:  {j.get('days_old', 7)}\n"
                f"---\n"
            )
        



        prompt2 = f"""
You are a strict job filter for a Senior Full-Stack Developer. Score each job 0-100.

CANDIDATE:
- 4.5+ years experience, Full-Stack / Angular Frontend / .NET Backend
- Core stack: Angular, Vue.js, .NET Core, C#, Node.js, TypeScript, SQL Server, MySQL, MongoDB
- Also knows: Azure DevOps, AWS, CI/CD, Docker, Selenium, Cypress, OpenAI API, AI automation
- Looking for: Senior Full-Stack, Senior Frontend (Angular), Senior Backend (.NET/Node), or Mid-Senior roles
- Prefers: remote/hybrid, product companies, AI/automation projects
- Will NOT do: pure mobile (Android/iOS), purely ML research, data science, DevOps-only, or medical/non-IT roles

SCORING RUBRIC — use the full range:

80-100 — perfect fit, apply immediately
  Pure Angular Frontend roles OR .NET Core/.NET/C# Backend roles OR Fullstack roles.
  If the job is an "Angular Developer" or "Frontend Developer" requiring Angular, score it 90-100.
  If the job is a ".NET Developer" or "C# Developer", score it 90-100.
  If it requires Angular + .NET Core/Node.js, score it 100.

50-79 — strong fit, apply
  Angular, .NET, or Node present (mandatory or optional) but slightly different tech stack (e.g., Angular + Java, or Vue + .NET).
  Or experience is slightly off (e.g., requires 6-8 years, or 2-3 years).

30-49 — weak, skip unless nothing better
  Familiar tech present but role is vague, or stack is heavily dominated by Java/PHP/Ruby without our core stack.

0-29 — do not apply
  Zero stack overlap (Java+Spring only, PHP only, etc.).
  Pure React or Pure QA/Testing roles with no development.
  Walk-in / venue / intern role / medical / non-IT.

RULES:
- Pure Angular Developer roles are GREAT → 90-100.
- Pure .NET Developer roles are GREAT → 90-100.
- Fullstack with Angular/Node/.NET → 90-100.
- Pure QA/Testing roles → 0-20.
- MEDICAL / DOCTOR / NON-IT → 0 strictly.

Return ONLY valid JSON:
{{
  "0": {{"score": 95, "reason": "Pure Angular frontend developer, perfect match"}},
  "1": {{"score": 0,  "reason": "Pure QA testing role, candidate is a developer"}}
}}

Jobs:
{job_block}
"""
        prompt = prompt2


        try:
            res = requests.post(
                self.url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type":  "application/json",
                },
                json={
                    "model":       "gpt-4o-mini",
                    "messages":    [{"role": "user", "content": prompt2}],
                    "temperature": 0.2,
                },
                timeout=90,
            )

            if res.status_code != 200:
                print("AI HTTP ERROR:", res.status_code, res.text[:200])
                return {}

            content = res.json()["choices"][0]["message"]["content"]
            content = re.sub(r"```json|```", "", content).strip()
            match   = re.search(r"\{.*\}", content, re.S)
            if not match:
                print("AI PARSE ERROR — raw:", content[:300])
                return {}

            data = json.loads(match.group(0))
            return data if isinstance(data, dict) else {}

        except Exception as e:
            print("AI call error:", e)
            return {}

    # =========================================================
    # RANK  — ai score + small recency bump
    # =========================================================
    def rank(self, jobs):
        return sorted(
            jobs,
            key=lambda j: j.get("ai_score", 0) + max(0, 3 - j.get("days_old", 7)),
            reverse=True,
        )

    # =========================================================
    # SELECT
    # =========================================================
    def select(self, jobs):
        apply_list  = [j for j in jobs if j.get("ai_score", 0) >= self.min_apply_score]
        review_list = [j for j in jobs if 10 <= j.get("ai_score", 0) < self.min_apply_score]

        if review_list:
            print(f"\n── REVIEW MANUALLY ({len(review_list)}) ──")
            for j in review_list:
                print(f"  score={j.get('ai_score')}  {j.get('title')} @ {j.get('company')}"
                      f"  |  {j.get('ai_reason', '')}")

        return apply_list[:self.daily_apply_limit]

    # =========================================================
    # CACHE
    # =========================================================
    def _load_cache(self):
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file) as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_cache(self):
        with open(self.cache_file, "w") as f:
            json.dump(self.cache, f, indent=2)