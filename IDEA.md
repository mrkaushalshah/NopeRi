# AI Integration for NopeRi

## Goal
Transform the Naukri automation tool into an intelligent job agent using AI (GPT-4o-mini) and the user's resume (`assests/resume.txt`).

## Key Features
- **Resume Digestion**: Extract structured profile data from `resume.txt`.
- **AI Solver**: Automatically fill job questionnaires using context from the job description and the user's profile.
- **Dynamic Prompting**: Use AI to generate professional and matching answers for HR questions.
- **Automation Loop**: Integrate the AI solver into the existing `apply_job` workflow in `main.py`.

## Constraints
- Use OpenAI-compatible API (user has 2.5M gpt-4o-mini tokens/day).
- Maintain existing session and search logic.
- Target Pune-based jobs (already implemented).
