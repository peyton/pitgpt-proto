# Project Purpose

PitGPT is a data-only prototype for research-driven personal A/B experiments.
It helps an operator turn a low-risk question and optional research notes into a
structured personal experiment, then analyze completed observations with honest
uncertainty.

The prototype exists to answer four practical questions:

1. Can the research ingestion prompt classify safety boundaries reliably?
2. Can model output be shaped into a strict protocol data model?
3. Can deterministic analysis produce useful personal result cards?
4. Can CLI, API, TUI, and benchmark interfaces share one core engine cleanly?

## Safety Contract

PitGPT does not diagnose, prescribe, cure, or replace clinical care. It can help
structure low-risk routines that touch a condition when the routine is
reversible, non-urgent, does not change medications or supplements, and is meant
to help the user learn patterns they can discuss with a clinician.

PitGPT blocks prescription medication dose/timing/start/stop/switch changes,
urgent or rapidly worsening symptoms, diagnosis requests, invasive devices,
high-risk supplement or ingestible changes, and anything requiring medical
supervision.

The current safe wedge is low-risk, reversible personal experimentation such as
cosmetic product comparisons, haircare routines, sleep timing, movement timing,
tracking routines, environmental adjustments, and similar routines.

## Relationship To The PRD

`docs/prd-v1.md` describes the broader product vision. This repository is not
that full product. It is the data pipeline prototype: ingestion, safety
classification, protocol synthesis, analysis, interfaces, and benchmarks.
