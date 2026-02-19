# Ivy House - Meta Weekly MVP

## Overview

This is a Streamlit-based marketing analytics application for Ivy House that processes Meta (Facebook) advertising data and website sales data to generate weekly meeting reports. The system follows a deterministic multi-step pipeline (Steps B→C→D for quick screening, B→C→E→F for final reports) that combines calculated KPIs with LLM-generated insights while ensuring numerical accuracy through strict separation of concerns.

The core principle is that KPI calculations are deterministic (Step B), and all LLM steps (C, D, E, F) only interpret/reference these numbers without recalculating them. All outputs are persisted to a versioned history structure using fingerprinting to avoid duplicate processing.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Pipeline Design (Step-Based Processing)
- **Step B**: Deterministic KPI calculation (`scripts/kpi_calc.py`) - parses Meta Adset CSV, Meta Ads CSV, and website Excel to produce `report_summary.json`
- **Step C**: LLM insights generation (`scripts/llm_insights.py`) - interprets Step B output without recalculating numbers, produces `report_insights.json`
- **Step D**: Draft meeting notes (`scripts/moderator.py`) - generates `meeting_draft.md` for quick screening
- **Step E**: Three consultant analysis (`scripts/consultants.py`) - produces `consultant_notes.json`
- **Step F**: Final meeting document (`scripts/moderator.py`) - generates `meeting.md` and `workflow_state.json`

### Version Control & History
- Primary key: `week_id` (ISO week format like `2025-W49`)
- Version key: `fp` (fingerprint - 8-char hash of input files)
- Structure: `history/{week_id}/meta/versions/fp-{fingerprint}/`
- `latest.json` pointer tracks current version per week
- Pipeline state tracked in `pipeline_state.json` with event log

### Data Integrity
- Input fingerprinting prevents duplicate processing (same files = no new version)
- JSON Schema validation (`schemas/report_summary.v1.json`) enforces output structure
- Schema versioning embedded in all artifacts (e.g., `report_summary.v1`, `inputs_fingerprint.v2`)
- LLM outputs are constrained to reference-only mode for numerical data

### Frontend
- Single Streamlit app (`app.py`) as orchestrator
- File upload for CSV/Excel inputs
- Manual inputs for strategy context (buying type, optimization goal, etc.)
- Force/Auto version controls for handling fingerprint mismatches

## External Dependencies

### LLM Integration
- **OpenRouter API**: Primary LLM gateway (via `OPENROUTER_API_KEY` or `OPENAI_API_KEY`)
- Fallback base URL: `https://openrouter.ai/api/v1`
- Default model: `openai/gpt-4o-mini`
- JSON mode enforced for structured outputs

### CrewAI (Experimental)
- Agent framework setup exists (`hello_crew.py`) but not integrated into main pipeline
- Configured to use OpenRouter as backend

### Data Processing
- **pandas**: CSV/Excel parsing and data manipulation
- **jsonschema**: Output validation against defined schemas
- **requests**: HTTP client for LLM API calls

### Timezone
- Fixed to `Asia/Taipei` using `zoneinfo.ZoneInfo`
- All timestamps in ISO8601 with `+08:00` offset
