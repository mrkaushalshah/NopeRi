# NopeRi AI Integration

> Transform NopeRi into an intelligent job agent using AI-powered questionnaire filling.

## Context
NopeRi is a Naukri job automation tool. While search and application work, many jobs are skipped due to mandatory questionnaires. The user wants to leverage their professional resume and high-volume AI credits (GPT-4o-mini) to automate these responses.

## Core Value
Maximize job application throughput by automatically and intelligently answering HR questionnaires based on the user's actual resume context.

## Stack
- **Languages**: Python 3.x
- **Frameworks**: Existing `requests`/`httpcloak` based client
- **AI**: OpenAI-compatible API (GPT-4o-mini)
- **Data**: `assests/resume.txt`

## Requirements

### Validated
- ✓ Job search by keyword and location (Pune)
- ✓ Job age filtering (1 day)
- ✓ Basic job application (no-questionnaire)

### Active
- [ ] AI Service implementation for profile extraction
- [ ] AI-powered questionnaire solving logic
- [ ] Integration with `NaukriJobClient.apply_job`
- [ ] Resume digestion into structured context
- [ ] Safe application loop with verification

### Out of Scope
- [ ] Multi-platform support (LinkedIn/Indeed)
- [ ] Automated resume editing/generation
- [ ] Voice-based interview prep

## Key Decisions
| Decision | Rationale | Outcome |
|----------|-----------|---------|
| GPT-4o-mini | High token limit (2.5M/day) and low cost; sufficient for text answering. | Pending |
| Resume Context | Sending full resume text with every prompt is easier than building a RAG for short questionnaires. | Pending |

## Evolution
This document evolves at phase transitions.

---
*Last updated: 2026-05-03 after initialization*
