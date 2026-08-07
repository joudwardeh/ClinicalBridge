# 03 — Orchestrator Design

The orchestrator is the **conductor**. It owns the control flow, passes data between agents in the
right order, validates each hand-off against a JSON schema, and assembles the final brief. In this
no-API prototype the orchestrator is a small Python function in the notebook; in a production system
it would be the same logic wrapping real model calls.

## Pipeline (sequential, with one parallel step)

```
                ┌─────────────────────┐
   RPM alert ──▶│  Alert Triage Agent │── triage_output ──┐
                └─────────────────────┘                   │
                                                          ▼
                          retrieval_plan tells the next two agents what to look for
                                          │
                    ┌─────────────────────┴─────────────────────┐
                    ▼                                            ▼
          ┌───────────────────┐                       ┌───────────────────┐
   EHR ──▶│ EHR Retrieval Agt │                       │  Anamnesis Agent  │◀── anamnesis
          └───────────────────┘                       └───────────────────┘
                    │ ehr_retrieval_output                       │ anamnesis_output
                    └─────────────────────┬─────────────────────┘
                                          ▼
                              ┌───────────────────────┐
                              │    Synthesis Agent    │
                              └───────────────────────┘
                                          │
                                          ▼
                              Clinical Context Brief  ──▶  clinician (human review)
```

## Why this order

1. **Triage first** because it decides urgency *and* the retrieval plan — running it first lets the
   two retrieval agents fetch *targeted* context instead of dumping the whole chart.
2. **EHR + Anamnesis in parallel** because they read independent data sources and never depend on
   each other. (In the notebook they run sequentially, but logically they're parallel and could be
   true-parallel with an API.)
3. **Synthesis last** because it needs all three structured outputs to reconcile conflicts and build
   traceability.

## Contract between stages

Each arrow in the diagram is a **typed JSON message** validated against a schema before the next
agent runs. If validation fails, the orchestrator stops and surfaces the error rather than feeding
malformed data downstream.

| Stage | Consumes | Produces | Validated against |
|---|---|---|---|
| Triage | `rpm_alert` + baselines/thresholds | `triage_output` | `triage_output.schema.json` |
| EHR Retrieval | `ehr_record` + alert + `retrieval_plan` | `ehr_retrieval_output` | `ehr_retrieval_output.schema.json` |
| Anamnesis | `anamnesis_record` + alert + `retrieval_plan` | `anamnesis_output` | `anamnesis_output.schema.json` |
| Synthesis | the three outputs + alert | `clinical_context_brief` | `clinical_context_brief.schema.json` |

## Orchestrator responsibilities

1. **Load** patient data + scenario inputs.
2. **Sequence** the agents in the order above.
3. **Validate** every message against its schema (`jsonschema`); halt on failure.
4. **Pass context forward** — e.g., inject `triage_output.retrieval_plan` into the retrieval prompts.
5. **Guard rails**: confirm the final brief contains a non-empty `safety_disclaimer`, a
   `traceability_index`, and a `missing_data_and_uncertainty` section before declaring success.
6. **Escalation hook**: if triage returns `emergent`, the orchestrator tags the brief as
   `FAST-TRACK` (a UI hint), but still runs the full pipeline — context still matters in an emergency.
7. **Audit log**: record which agent produced what, with timestamps, for the report's appendix.

## No-API execution model

Because we are not calling an API, "running an agent" means **loading its pre-generated output** from
`agent_outputs/scenario_N_outputs.json`. The orchestrator code is identical — only the
`run_agent()` function differs:

```python
def run_agent(agent_name, scenario_id):
    # No-API mode: read the stored manual Claude output instead of calling the model.
    outputs = load_json(f"agent_outputs/scenario_{scenario_id}_outputs.json")
    return outputs[agent_name]   # e.g. outputs["triage"]
```

Swapping in a real API later is a one-function change — the orchestration, schemas, validation, and
evaluation all stay exactly the same. That clean seam is a deliberate design choice and a talking
point for the report.

## Failure handling

| Failure | Orchestrator behavior |
|---|---|
| Schema validation fails | Stop, print the offending field + agent, do not continue |
| Agent emits a claim with no citation | Synthesis self-check should catch it; eval flags it as hallucination |
| Triage = `insufficient_data` | Still run retrieval; brief leads with the missing-data section |
| A data source is empty (e.g., no anamnesis) | Agents return empty arrays + a gap flag; pipeline continues |
