# 01 — Project Objective

## The problem in one sentence

When a remote-monitoring device alerts a care team, the alert arrives as a **bare number with no
story**, and the clinician must manually reconstruct the patient's context from three disconnected
systems before they can act safely.

## The "Clinical Context Gap"

A modern care team receives data from three silos that rarely talk to each other:

1. **RPM (Remote Patient Monitoring)** — live device readings: blood pressure, glucose, heart rate,
   SpO2, weight, plus the thresholds and baselines that turn a reading into an *alert*.
2. **EHR (Electronic Health Record)** — the formal medical record: diagnoses, medications, labs,
   allergies, and visit notes.
3. **Anamnesis** — the patient's own account: current symptoms, history, how well they're taking
   their medications, lifestyle, family history, and what *they* are worried about.

A glucose alert of `58 mg/dL` means something completely different for a newly-diagnosed diabetic
who skipped lunch than for an insulin-dependent patient who doubled their dose. **The number is the
same; the context is everything.** Today, assembling that context is slow manual work, and important
signals (a missed refill, a quietly worsening trend, a contradiction between systems) are easy to miss.

## What ClinicalBridge does

ClinicalBridge is a **multi-agent assistant** that automatically:

1. **Triages** the incoming RPM alert — how urgent is it, is it even a real signal, and what context
   do we need to understand it?
2. **Retrieves** only the *relevant* slice of the EHR (not the whole chart).
3. **Extracts** the *relevant* slice of the anamnesis.
4. **Synthesizes** all of it into one **Clinical Context Brief** that a clinician can scan in under a
   minute, with every claim traceable to a source.

## What success looks like

A clinician opens the brief and immediately sees:

- **What fired and how bad** (the alert + urgency).
- **The patient in one snapshot** (age, key conditions, key meds).
- **The likely story** — *factors to consider*, each tied to a citation (e.g., "BP elevated;
  patient reports running out of lisinopril 6 days ago [ANAMNESIS] and last refill was 47 days ago
  for a 30-day supply [EHR.med.002]").
- **What's missing or uncertain** (e.g., "No potassium level on file in last 90 days").
- **What's contradictory** (e.g., "EHR lists metformin as active; patient states they stopped it").
- **Suggested considerations** — questions and checks for the clinician, never orders or diagnoses.
- **A safety disclaimer** restating that this is decision *support*.

## Explicit non-goals (scope guardrails)

| The system will... | The system will NOT... |
|---|---|
| Summarize and cite existing data | Diagnose, or rank diagnoses |
| Flag urgency for prioritization | Decide treatment or write orders |
| Surface missing data and conflicts | Fill gaps with assumptions |
| Use only fictional data | Touch real PHI / real patients |
| Keep a human in the loop | Auto-act on any patient |

## Why this is a good Prompt Engineering project

The hard part is **not** the code — the notebook is thin. The hard part is **prompt design under
safety constraints**: getting four specialized agents to stay in their lane, refuse to hallucinate,
cite everything, express calibrated uncertainty, and hand structured JSON to each other. That is
exactly the skill set COP-3442 is assessing, and the [prompt portfolio](08_prompt_portfolio.md)
documents three iterations of that design work per agent.

## Connection to course concepts

- **Role prompting & system prompts** — each agent has a tightly scoped persona.
- **Structured output / JSON-mode discipline** — every agent emits schema-valid JSON.
- **Decomposition** — one hard task split into four narrow, testable sub-tasks.
- **Grounding / anti-hallucination** — "cite or omit" rules and source IDs.
- **Few-shot & format exemplars** — gold briefs act as exemplars.
- **Evaluation** — a measurable rubric (see [04_evaluation_framework.md](04_evaluation_framework.md)).
