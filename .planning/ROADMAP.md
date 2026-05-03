# Roadmap - NopeRi AI Integration

## Milestone 1: AI Foundation & Intelligence
**Goal**: Establish AI connectivity and resume-based intelligence.

- [x] **Phase 1: AI Service & Profile Extraction**
  - Implement `AIHandler` for OpenAI-compatible API.
  - Implement resume reading and structured profile extraction.
  - Verification: AI returns correct JSON profile from `resume.txt`.

- [ ] **Phase 2: Questionnaire Solver Implementation**
  - Update `NaukriJobClient` to handle questionnaires using AI.
  - Implement prompt engineering for accurate HR answers.
  - Verification: Script correctly answers sample questionnaires without skipping.

- [ ] **Phase 3: Integration & Production Loop**
  - Integrate AI solver into `main.py` application loop.
  - Add error handling and fallback for complex questions.
  - Verification: 100% application rate for search results.

## Next Milestones
- Milestone 2: UI Dashboard (Optional)
- Milestone 3: Advanced Behavioral Analysis
