# Plan: Questionnaire Solver Implementation

This plan integrates AI reasoning into the Naukri application flow, allowing the bot to answer mandatory questionnaires.

## Waves

### Wave 1: The AI Solver Class
- **Task 1**: Implement `solve_questionnaire` in `AIHandler`.
  - `<action>`: Create a method that takes `job_title`, `job_description`, and a list of `questions` (with options). It uses `gpt-4o-mini` to generate a JSON response mapping question IDs to the best answers based on the user's profile.
  - `<read_first>`: `src/utils/ai_handler.py`.
  - `<acceptance_criteria>`: `solve_questionnaire` returns a dictionary in the format `{ "questionId": "answer" }`.

### Wave 2: Naukri Client Integration
- **Task 2**: Refactor `NaukriJobClient.handle_static_questionnaire_and_apply`.
  - `<action>`: Rename to `handle_ai_questionnaire_and_apply` (or similar). Replace the hardcoded `PROFILE` logic with a call to `AIHandler.solve_questionnaire`.
  - `<read_first>`: `src/client/job_client.py`, `src/utils/ai_handler.py`.
  - `<acceptance_criteria>`: The method successfully sends questionnaire data to the AI and uses the returned answers in the application request.

### Wave 3: Integration & Dry Run
- **Task 3**: Update `main.py` application loop.
  - `<action>`: Ensure that if an application fails with a questionnaire, the new `handle_ai_questionnaire_and_apply` method is called.
  - `<read_first>`: `main.py`.
  - `<acceptance_criteria>`: The application loop no longer skips jobs with "questionnaire required" status.

## Verification
### must_haves
- [ ] AI correctly selects multiple-choice options (indices).
- [ ] AI provides professional text answers for open-ended questions.
- [ ] Application is successfully submitted after AI filling.

## Threat Model
- **Medium**: AI might give incorrect data (e.g., wrong CTC). Mitigated by providing the actual profile as strict context.
- **Low**: API Timeouts. Mitigated by error handling in the application loop.

---
*Phase: 02-questionnaire-solver*
