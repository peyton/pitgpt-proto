# Scope

This document separates the current prototype from the broader product vision.

## Current Prototype

Implemented:

- Research ingestion through an OpenRouter-compatible LLM call
- GREEN/YELLOW/RED safety policy prompt
- Protocol-shaped ingestion output validation
- Deterministic A/B trial analysis
- CLI, FastAPI, and Textual TUI interfaces
- React web frontend for local trial setup and check-ins
- Benchmark runner, scoring, and report commands
- Example protocol, observations, and safe research note

## Explicitly Not Implemented

- User accounts
- Data persistence
- Calendar scheduling
- Daily reminders
- Randomized assignment generation
- Protocol lock enforcement over time
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
