# Phase 1: AI Service & Profile Extraction - Context

**Gathered**: 2026-05-03
**Status**: Ready for planning

## Phase Boundary
This phase focuses on building the "Brain" of the Intelligent Job Agent. We will implement a service that connects to your AI credits and "reads" your resume to create a reusable professional profile.

## Implementation Decisions

### AI Connectivity
- **Service**: Create `src/utils/ai_handler.py`.
- **API**: Use OpenAI-compatible endpoint.
- **Model**: Default to `gpt-4o-mini`.

### Profile Extraction
- **Input**: `assests/resume.txt`.
- **Output**: A structured JSON file or object stored in memory for the session.
- **Content**: Must include Years of Experience, Technical Skills, Current Location (Pune), Preferred Salary, and Notice Period.

### the agent's Discretion
- Choice of JSON schema for the profile.
- Exact prompt engineering for the extraction.
- Structure of the `AIHandler` class.

## Canonical References
- `assests/resume.txt` — Source of truth for profile data.
- `.env` — Will store `AI_API_KEY` and `AI_BASE_URL`.

## Specific Ideas
- Initialize the `AIHandler` in `main.py` before the job search starts.
- Add a "Thinking..." or "Analyzing Resume..." status message to the terminal.

---
*Phase: 01-ai-service*
