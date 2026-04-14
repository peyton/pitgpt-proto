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

PitGPT does not diagnose, treat, cure, or recommend medical actions. It blocks
prescription medication experiments, supplement or ingestible experiments,
disease-management claims, invasive devices, medication stopping experiments,
and anything requiring medical supervision.

The current safe wedge is cosmetic, reversible, non-disease experimentation such
as moisturizer comparisons, haircare routines, and low-risk routine timing.

## Relationship To The PRD

`docs/prd-v1.md` describes the broader product vision. This repository is not
that full product. It is the data pipeline prototype: ingestion, safety
classification, protocol synthesis, analysis, interfaces, and benchmarks.
