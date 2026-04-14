# Scope

This document separates the current prototype from the broader product vision.

## Current Prototype

Implemented:

- Research ingestion through an OpenRouter-compatible LLM call
- GREEN/YELLOW/RED safety policy prompt
- Protocol-shaped ingestion output validation
- Document length guards and ingestion metadata
- Deterministic A/B trial analysis with paired-period summaries and Welch sensitivity
- CLI, FastAPI, and Textual TUI interfaces
- React web frontend for local trial setup, protocol lock, randomized schedules,
  check-ins, early stops, import/export, and completed-result history
- Local templates and bundled example analysis without an API key
- Read/demo API endpoints for templates, schedules, and example analysis
- Benchmark runner, scoring, and report commands
- Example protocol, observations, and safe research note
- Web build, browser tests, unit tests, and dependency audit recipes

## Explicitly Not Implemented

- User accounts
- Server-side data persistence
- Calendar scheduling
- Email, push, SMS, or calendar reminder delivery
- Background reminder jobs
- Server-enforced protocol lock enforcement over time
- Photo capture
- Wearable integrations
- Community protocol sharing
- Pooled results across users
- Diagnosis, treatment recommendations, or disease-management guidance

## Safety Boundaries

The ingestion policy blocks prescription medications, supplements and
ingestibles, disease-management claims, invasive devices, medication stopping,
and anything requiring medical supervision. Yellow-tier cases can be allowed
only with warnings and restrictions. Green-tier cases are limited to low-risk,
reversible, non-disease routine or product comparisons.

## Future PRD Work

`docs/prd-v1.md` includes product concepts such as reminders, protocol lock,
personal results dashboards, pooled evidence, and post-MVP community workflows.
Treat those as product direction, not current behavior.
