# Phase 1: AI Service & Profile Extraction - AI Design Contract

## 1. System Classification
- **Type**: Information Extraction & Structured Profile Generation
- **Primary Model**: `gpt-4o-mini` (2.5M token/day daily limit)
- **Framework**: Standard OpenAI SDK (Python)

## 2. Framework Selection
- **Selected**: `openai` (Python)
- **Rationale**: The user has access to an OpenAI-compatible API. The standard SDK is the most stable and lightweight choice for simple completion and extraction tasks.
- **Alternatives Considered**: `LangChain` (too heavy for this simple extraction), `PydanticAI` (excellent but may add unnecessary complexity for a script-based project).

## 3. Implementation Guidance
- **Pattern**: Use a system prompt to define the "Professional DNA" of the user.
- **Extraction**: Use JSON mode to ensure the output is a valid dictionary.
- **Retry Logic**: Implement basic exponential backoff for API rate limits.

## 4. Domain Context
- **Vertical**: IT Recruitment / Job Automation
- **Success Criteria**: 
  - Accuracy: Must correctly identify 4.5+ years of experience.
  - Granularity: Must separate Skills into Categories (Frontend, Backend, AI).
  - Normalization: CTC values should be extracted as numbers/strings that can be compared.

## 5. Evaluation Strategy
- **Dimension 1: Accuracy**: Compare extracted JSON against `resume.txt` manually for the first run.
- **Dimension 2: Formatting**: Ensure the AI always returns valid JSON.
- **Dimension 3: Cost**: Monitor token usage to ensure it stays within the 2.5M daily budget.

---
*Created: 2026-05-03*
