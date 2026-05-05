---
phase: "05"
plan: "05"
subsystem: "automation"
tags:
  - search
  - jobs
  - crawler
requires:
  - Phase 4
provides:
  - Enhanced Search Engine
affects:
  - main.py
  - src/client/job_client.py
tech-stack.added:
  - []
key-files.modified:
  - main.py
  - src/client/job_client.py
requirements-completed:
  - []
---

# Phase 05 Plan 05: Enhanced Search Engine

<threat_model>
This phase modifies the search loop and API request payloads. 
Threats to consider:
1. Rate Limiting / IP Ban: Making too many sequential page requests could trigger Naukri's anti-bot protection or rate limit the IP.
Mitigation: Introduce small artificial delays `asyncio.sleep()` between page requests during multi-query polling.
</threat_model>

### 1. Update `job_client.py` for Date Sorting
**Autonomous:** true
**Wave:** 1
**Depends On:** []
```xml
<task>
<read_first>
- src/client/job_client.py
</read_first>
<action>
In `src/client/job_client.py`, update the `search_jobs` method to support sorting by date:
1. Add an optional parameter `sort_by: str = "date"` to the `search_jobs` method signature.
2. In the `params` dictionary within `search_jobs`, map this to Naukri's sorting parameter. Based on Naukri API behavior, the sorting parameter is typically passed as `sortType="date"` or `sortBy="date"` or simply `sort="d"`. Let's add `sortType="date"` to the params dictionary. 
</action>
<acceptance_criteria>
- `src/client/job_client.py` contains `sort_by: str = "date"` in the `search_jobs` signature.
- `src/client/job_client.py` contains `sortType` or equivalent in the `params` dictionary for `search_jobs`.
</acceptance_criteria>
</task>
```

### 2. Update `main.py` Search Loop for Multi-Query and Pagination
**Autonomous:** true
**Wave:** 2
**Depends On:** [1]
```xml
<task>
<read_first>
- main.py
</read_first>
<action>
In `main.py`, rewrite the `job_search_loop(app: ApplicationBuilder)` to support multiple queries and pagination:
1. Define a list of queries inside the function:
   `queries = [{"keyword": "Angular developer", "location": "Pune"}, {"keyword": "Frontend developer", "location": "Pune"}]`
2. Wrap the search logic in a `for query in queries:` loop.
3. For each query, wrap the page fetch in a `for page in range(1, 4):` loop (max 3 pages to avoid rate limits).
4. Introduce a `await asyncio.sleep(2)` between page fetches.
5. If `raw_jobs` returns empty for a page, `break` the pagination loop and move to the next query.
6. Check if jobs have already been applied before sending to AI filter to save OpenAI API costs (move the `logger.is_applied()` check up if possible, or filter `raw_jobs` before AI).
</action>
<acceptance_criteria>
- `main.py` contains `for query in queries:` inside `job_search_loop`.
- `main.py` contains a pagination loop like `for page in range`.
- `main.py` contains `await asyncio.sleep` between page fetches.
</acceptance_criteria>
</task>
```

## Verification
- Run `python main.py`. 
- Observe logs to ensure it loops through multiple queries and fetches `page=1`, `page=2`, etc.
- Verify jobs retrieved are more recent (sorted by date).
