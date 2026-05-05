# Phase 05: Enhanced Search Engine - Context

**Gathered:** 2026-05-05
**Status:** Ready for planning

<domain>
## Phase Boundary

The user wants to enhance the `job_search_loop` in `main.py` and `src/client/job_client.py` to massively increase the amount of relevant jobs retrieved. Currently, the script only fetches the first 20 jobs (Page 1) for a single hardcoded query ("Angular developer", "Pune") and sorts by Relevance.

This phase will deliver:
1. Multi-query support (looping through a list of keywords and locations).
2. Pagination support (fetching page 1, 2, 3...) during the search loop.
3. Sorting adjustments (ensuring Naukri sorts by Date to get newest jobs first).
</domain>

<decisions>
## Implementation Decisions

### 1. Multi-Query Support
- Instead of a single hardcoded search in `main.py` (`keyword="Angular developer", location="Pune"`), define a configurable list of queries in `main.py` (e.g., a list of dictionaries with `keyword` and `location`).
- The `job_search_loop` should iterate through this list of queries during its cycle.

### 2. Pagination
- Modify `main.py` or `src/client/job_client.py` to handle pagination.
- We should iterate through `page=1`, `page=2`, `page=3`, etc., for each query until we encounter jobs we have already applied for, or until a maximum page limit is reached (e.g., 5 pages).

### 3. Sorting by Date
- Naukri defaults to sorting by Relevance. Modify `src/client/job_client.py`'s `search_jobs` method to include the sorting parameter so the API returns the newest jobs first (usually `sort="date"` or `sort="d"`).

</decisions>

<canonical_refs>
## Canonical References

### Search Workflow
- `main.py` - Contains the `job_search_loop`
- `src/client/job_client.py` - Contains the `search_jobs` method mapping to Naukri's API
</canonical_refs>

---

*Phase: 05-enhanced-search-engine*
*Context gathered: 2026-05-05 via direct conversation context*
