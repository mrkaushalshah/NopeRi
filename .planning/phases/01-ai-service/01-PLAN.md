# Plan: AI Service & Profile Extraction

This plan implements the AI Foundation for NopeRi, enabling automated profile extraction from the user's resume.

## Waves

### Wave 1: AI Service Implementation
- **Task 1**: Create `src/utils/ai_handler.py`.
  - `<action>`: Implement `AIHandler` class with `__init__` (loading API key/base url from `.env`), `generate_completion` method, and `extract_profile` method.
  - `<read_first>`: `src/utils/ai_handler.py` (to-be-created).
  - `<acceptance_criteria>`: Class exists and has `generate_completion` method.
- **Task 2**: Update `.env` with AI placeholders.
  - `<action>`: Add `AI_API_KEY` and `AI_BASE_URL` to `.env`.
  - `<read_first>`: `.env`.
  - `<acceptance_criteria>`: `.env` contains placeholders for AI keys.

### Wave 2: Profile Extraction Logic
- **Task 3**: Implement Profile Extraction Prompt.
  - `<action>`: In `AIHandler`, implement the logic to read `assests/resume.txt` and send it to the AI with a prompt to extract key professional metrics in JSON format.
  - `<read_first>`: `assests/resume.txt`, `src/utils/ai_handler.py`.
  - `<acceptance_criteria>`: `extract_profile()` returns a valid dictionary.

### Wave 3: Integration & Testing
- **Task 4**: Create a test script `test_ai.py`.
  - `<action>`: Create `test_ai.py` to initialize `AIHandler`, extract the profile, and print the resulting JSON to verify accuracy.
  - `<read_first>`: `src/utils/ai_handler.py`.
  - `<acceptance_criteria>`: `python test_ai.py` successfully prints a structured profile from your resume.

## Verification
### must_haves
- [ ] `AIHandler` can successfully connect to the AI endpoint.
- [ ] Profile is extracted as a structured JSON object.
- [ ] Extracted profile accurately reflects years of experience (4.5+) and location (Pune) from `resume.txt`.

## Threat Model
- **Low**: API Key exposure. Mitigated by using `.env` and `.gitignore`.
- **Low**: Hallucination. Mitigated by strict system prompts and manual verification during the test phase.

---
*Phase: 01-ai-service*
