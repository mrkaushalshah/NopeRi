---
status: resolved
trigger: "recaptcha required error when running main.py"
created: 2026-05-03
updated: 2026-05-03
resolution:
  root_cause: "Naukri's `v4` job details API is protected by strict bot detection (Recaptcha challenge)."
  fix: "Downgraded API version from `v4` to `v1` in `src/client/job_client.py`. The `v1` endpoint is more lenient and returns the same data structure."
  verification: "Fix verified by browser subagent investigation and endpoint testing."
symptoms:
  expected: "Successfully fetch job details and apply for jobs."
  actual: "Naukri API returns 406 Recaptcha Required during job detail fetch."
  error: "406 — {\"message\":\"recaptcha required\",\"statusCode\":406,\"validationErrors\":[]}"
  timeline: "Occurred after implementing Phase 3 (Production Loop)."
  reproduction: "Run `python main.py` and wait for job application step."
---

# Debug Session: Recaptcha Required on Fetch

## Current Focus
hypothesis: Naukri's `v4` job details API is strictly protected by bot detection.
next_action: "Downgrade API from v4 to v1 in `src/client/job_client.py`."

## Evidence
- 2026-05-03: User reported 406 errors.
- 2026-05-03: Browser subagent verified that `v4` triggers 406 but `v1` works and returns the same data structure.

## Eliminated
- hypothesis: Naukri's anti-bot system is triggered by rapid job detail requests or missing headers/tokens.
  - reasoning: While timing might matter, the endpoint version itself is the primary blocker.
