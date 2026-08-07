# Manual Claude Workflow — Using Claude as the LLM Engine Without an API Key

> **Educational prototype. All data is fictional. This is not a real clinical tool. The system does
> not make diagnoses. Claude's outputs must be reviewed, and clinician review is always required.**

---

## 1. Overview

ClinicalBridge runs **without an API key**. There is no billing, no secret, and no network call in
the default workflow — yet the system is still powered by a real large language model.

- **The prototype runs in no-API / mock mode.** The orchestrator in [`pipeline.py`](pipeline.py)
  loads each agent's output from `agent_outputs/` instead of calling a model over the network.
- **Claude is still the LLM engine — used manually.** You generate each agent's output by hand in the
  Claude application (web or desktop): paste the agent's engineered prompt plus the scenario input,
  and Claude returns the structured JSON the pipeline expects.
- **The notebook/prototype validates Claude's outputs with JSON Schemas.** Every output Claude
  produces is checked against the contracts in [`schemas/`](schemas) before it is used. Malformed
  output is rejected, not silently accepted.
- **This design keeps the project reproducible and safe.** Because outputs are stored as files, the
  exact same brief and the exact same evaluation scores reproduce every run — ideal for a university
  submission, a live demo, and grading. It also separates the graded skill (**prompt engineering**)
  from API plumbing (not the point of the course).

In short: **Claude does the reasoning; the schemas and orchestrator enforce structure and safety; the
stored files make it reproducible.**

---

## 2. Manual Claude Execution Flow

```
  ┌────────────────────┐     ┌──────────────────────┐     ┌─────────────────────┐
  │  Scenario JSON     │     │  Agent Prompt        │     │  Claude (manual)    │
  │  scenarios/*.json  │ ──▶ │  prompts/<agent>/    │ ──▶ │  paste prompt +     │
  │  (alert + context) │     │  v3.md               │     │  input, run         │
  └────────────────────┘     └──────────────────────┘     └─────────┬───────────┘
                                                                     │  JSON only
                                                                     ▼
  ┌────────────────────────────────────────────────────────────────────────────┐
  │  Save Claude's JSON response into the right field of                         │
  │  agent_outputs/scenario_N_outputs.json   ("triage"/"ehr"/"anamnesis"/"brief")│
  └─────────────────────────────────────────┬──────────────────────────────────┘
                                             ▼
  ┌────────────────────┐     ┌──────────────────────┐     ┌─────────────────────┐
  │  Run main.py or    │ ──▶ │  Schema validation   │ ──▶ │  Evaluation         │
  │  the notebook      │     │  (schemas/*.json)     │     │  (metrics + scores) │
  └────────────────────┘     └──────────────────────┘     └─────────────────────┘
```

Same flow in one line:

> **Scenario JSON → Agent Prompt → Claude Response JSON → save to `agent_outputs/` → run `main.py` or the notebook → schema validation → evaluation.**

---

## 3. Step-by-Step Instructions

Do this once per agent, per scenario (four agents per scenario):

1. **Open the scenario.** Pick a file in [`scenarios/`](scenarios), e.g.
   `scenarios/scenario_1_missed_medication.json`. It contains the `rpm_alert`, the full `ehr_context`,
   and the full `anamnesis_context`.
2. **Open the agent's production prompt.** Use `prompts/<agent>/v3.md`, e.g.
   `prompts/alert_triage_agent/v3.md`.
3. **Paste both into Claude.** First the full prompt (the agent's system instructions), then the
   relevant input for that agent (see Section 4 for exactly which fields each agent needs).
4. **Ask Claude to return JSON only.** Add a line such as: *"Return only valid JSON matching the
   schema. Do not include any prose, explanation, or markdown fences."* This keeps the output
   machine-parseable.
5. **Save the output to the correct field.** Open
   `agent_outputs/scenario_N_outputs.json` and paste Claude's JSON under the matching key:
   `triage`, `ehr`, `anamnesis`, or `brief`.
6. **Render the brief.** Run `python main.py --brief N` to print the full 8-section Clinical Context
   Brief for scenario `N`.
7. **Run the evaluation.** Run `python main.py --scorecard` (or open
   `notebook/clinicalbridge_prototype.ipynb` and *Restart & Run All*) to validate the JSON against the
   schemas and score triage accuracy, retrieval relevance, anamnesis completeness, hallucination
   rate, traceability, index coverage, and safety.

> Tip: the order matters. Generate **triage first** (its `retrieval_plan` tells the next two agents
> what to look for), then **EHR** and **Anamnesis**, then **Synthesis** last (it consumes the other
> three outputs).

---

## 4. Full Example: Scenario 1 — Missed Medication

Patient P001 has a home BP reading of **182/104**. We generate all four agent outputs manually and
save them into `agent_outputs/scenario_1_outputs.json`. (This file already ships pre-filled with
gold-quality outputs; the steps below show how you would reproduce or regenerate them.)

### 4.1 Triage Agent
- **Prompt:** `prompts/alert_triage_agent/v3.md`
- **Input pasted into Claude:** the `rpm_alert` object from
  `scenarios/scenario_1_missed_medication.json`, plus the patient's RPM `baselines` and `thresholds`
  from `data/patients.json` (patient `P001` → `rpm`).
- **Ask:** "Return only valid JSON matching the triage_output schema."
- **Save to:** the `"triage"` field of `agent_outputs/scenario_1_outputs.json`.
- **What Claude returns (abridged):**
  ```json
  {
    "alert_id": "ALERT-P001-001",
    "patient_id": "P001",
    "urgency_level": "urgent",
    "alert_validity": "likely_valid",
    "retrieval_plan": {
      "ehr_focus": ["antihypertensive medications with last refill date", "renal labs", "..."],
      "anamnesis_focus": ["medication adherence / missed BP medication", "..."]
    },
    "confidence": "high"
  }
  ```

### 4.2 EHR Retrieval Agent
- **Prompt:** `prompts/ehr_retrieval_agent/v3.md`
- **Input pasted into Claude:** the full `ehr_context` from the scenario file, the `rpm_alert`, and the
  `retrieval_plan` produced by the Triage Agent in step 4.1.
- **Ask:** "Return only valid JSON matching the ehr_retrieval_output schema. Copy values verbatim."
- **Save to:** the `"ehr"` field of `agent_outputs/scenario_1_outputs.json`.
- **Expected behavior:** returns only the relevant items (e.g., `EHR.med.001` lisinopril with its
  refill date, the renal labs, the HTN diagnosis, the prior note) each with a `source_id` and a
  relevance reason, plus a `data_gaps` entry noting no recent potassium is on file.

### 4.3 Anamnesis Agent
- **Prompt:** `prompts/anamnesis_agent/v3.md`
- **Input pasted into Claude:** the full `anamnesis_context` from the scenario file, the `rpm_alert`,
  and the Triage `retrieval_plan`.
- **Ask:** "Return only valid JSON matching the anamnesis_output schema. Tag every item as
  patient-reported and do not convert symptoms into diagnoses."
- **Save to:** the `"anamnesis"` field of `agent_outputs/scenario_1_outputs.json`.
- **Expected behavior:** extracts the patient-reported lapse (`ANAMNESIS.adherence.1` — "ran out of my
  BP pill ~1 week ago"), the headache, and the patient's concern, all tagged `reported_by: patient`.

### 4.4 Synthesis Agent
- **Prompt:** `prompts/synthesis_agent/v3.md`
- **Input pasted into Claude:** the three JSON outputs from steps 4.1–4.3 (`triage`, `ehr`,
  `anamnesis`), plus the original `rpm_alert`.
- **Ask:** "Return only valid JSON matching the clinical_context_brief schema. Every claim must cite a
  source id. Express possibilities only as factors to consider — never a diagnosis."
- **Save to:** the `"brief"` field of `agent_outputs/scenario_1_outputs.json`.
- **Expected behavior:** produces the Clinical Context Brief connecting the EHR refill gap to the
  patient-reported lapse as a *possible contributing factor* (cited to `EHR.med.001` +
  `ANAMNESIS.adherence.1` + the BP readings), flags missing potassium, and includes the safety
  disclaimer and full traceability index.

### 4.5 Run it
```bash
python main.py --brief 1        # prints the 8-section brief for Scenario 1
python main.py --scorecard      # validates the JSON and prints the evaluation scores
```

---

## 5. Why This Is Still a Working Prototype

Running "manually" does not make this a slideshow — the engineering pipeline is real:

- **The orchestrator runs the full pipeline.** `pipeline.run_pipeline()` sequences Triage → EHR ‖
  Anamnesis → Synthesis, passes the retrieval plan forward, and enforces guard rails
  (patient-ID consistency, non-empty disclaimer, traceability index, and missing-data section).
- **Stored outputs simulate the LLM calls.** `run_agent()` loads Claude's saved JSON, which is exactly
  the data a live API call would return — the rest of the system cannot tell the difference.
- **JSON schemas enforce structured output.** Every agent output is validated against `schemas/`;
  malformed or off-contract output is rejected before it can propagate.
- **Evaluation measures real properties.** `evaluation/metrics.py` scores triage accuracy, retrieval
  relevance (precision/recall/F1), anamnesis extraction completeness, hallucination rate, source
  traceability, index coverage, and safety compliance against the gold standards.
- **API integration is a one-function change.** To go live, replace the body of `run_agent()` in
  `pipeline.py` with a Claude API call that sends the same v3 prompt + scenario input and returns the
  model's JSON. **Nothing else changes** — orchestration, schemas, guard rails, and evaluation stay
  identical. That clean seam is a deliberate design choice.

---

## 6. Safety Notes

- **All data is fictional.** Every patient, alert, lab, symptom, and date is invented for this
  educational project. No real patients and no real PHI are involved.
- **This is not a real clinical tool.** ClinicalBridge has not been clinically validated and has no
  regulatory clearance. It must not be used for patient care.
- **Claude's outputs must be reviewed.** Manually generated outputs should be checked for schema
  validity and for adherence to the safety rules before being trusted or saved.
- **The system does not diagnose.** Outputs are framed strictly as *factors to consider*, never as
  diagnoses or treatment decisions.
- **Clinician review is always required.** ClinicalBridge supports clinician judgment; it never
  replaces it. A human remains in the loop at all times.

---

## How This Maps to Future API Mode

The manual workflow above and a future live-API workflow are the **same pipeline** with a different
*provider* (see [`pipeline.py`](pipeline.py)):

| | No-API mode (current) | Future API mode |
|---|---|---|
| Provider | `ManualOutputProvider` (default) | `ClaudeAPIProvider` |
| Where the JSON comes from | you paste prompt + input into Claude and save the result to `agent_outputs/` | the provider sends the same v3 prompt + context to the Claude API and returns the JSON |
| API key needed | no | yes |
| Schemas, guard rails, evaluation, brief | identical | identical |

The orchestrator only ever calls `provider.run_agent(agent_name, scenario_id, context)`. To switch to
a real Claude connection later, implement `ClaudeAPIProvider.run_agent()` and pass
`provider=ClaudeAPIProvider()` to `run_pipeline()` — nothing else changes. In the submitted prototype
`ClaudeAPIProvider` is a safe stub that raises *"Claude API mode is not enabled in this no-API
prototype."* and requires no `anthropic` package, so the project never depends on an API key.

---

## See also
- [`README.md`](README.md) — installation and how to run.
- [`docs/03_orchestrator_design.md`](docs/03_orchestrator_design.md) — the `run_agent()` seam in detail.
- [`docs/05_notebook_plan.md`](docs/05_notebook_plan.md) — the no-API notebook workflow.
- [`reports/prompt_engineering_portfolio.md`](reports/prompt_engineering_portfolio.md) — the agent prompts.
