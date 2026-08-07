# 05 — Python / Jupyter Notebook Prototype Plan (No-API)

The prototype demonstrates the full pipeline **without calling any API**. Instead of live model
calls, each agent's output is generated **once, by hand, in the Claude app**, saved as JSON, and the
notebook replays those saved outputs through the real orchestration + validation + evaluation code.

This is a legitimate and common pattern for prompt-engineering coursework: it separates **prompt
design** (the graded skill) from **API plumbing** (not the point), and it makes the demo perfectly
reproducible.

## The no-API workflow (how you actually build outputs)

For each scenario, for each agent:

1. Open `prompts/<agent>/v3.md` — copy the system prompt.
2. Open `scenarios/scenario_N_*.json` — copy the relevant input section.
3. Paste both into Claude (the app), run it.
4. Copy Claude's JSON answer.
5. Save it into `agent_outputs/scenario_N_outputs.json` under the right key
   (`triage` / `ehr` / `anamnesis` / `brief`).

The repo already ships with **pre-filled, gold-quality** `agent_outputs/` so the notebook runs out of
the box; you can regenerate any of them to show iteration.

## Notebook structure (`notebook/clinicalbridge_prototype.ipynb`)

| Cell | Purpose |
|---|---|
| **1. Setup** | `import json, jsonschema`; define `ROOT` paths; helper `load_json()` |
| **2. Load schemas** | Load all 7 schemas into a dict for validation |
| **3. Load data** | Load `data/patients.json` and pick a scenario |
| **4. The no-API agent runner** | `run_agent(name, scenario_id)` reads from `agent_outputs/` |
| **5. Schema validators** | `validate(obj, schema_name)` wraps `jsonschema.validate` |
| **6. Orchestrator** | `run_pipeline(scenario_id)` → triage → ehr+anamnesis → synthesis, validating each step |
| **7. Pretty-print the brief** | Render the Clinical Context Brief as readable Markdown |
| **8. Evaluation** | Import `evaluation/metrics.py`; score the run vs. the gold brief |
| **9. Scorecard** | Build the 5×7 metric table across all scenarios |
| **10. Demo cells** | Run Scenario 1 and Scenario 3 end-to-end with full output (for the live demo) |

## Key functions (pseudocode)

```python
def run_pipeline(scenario_id):
    scenario = load_json(f"scenarios/scenario_{scenario_id}_*.json")
    alert    = scenario["rpm_alert"]

    triage = run_agent("triage", scenario_id)
    validate(triage, "triage_output")

    ehr = run_agent("ehr", scenario_id)
    validate(ehr, "ehr_retrieval_output")

    anam = run_agent("anamnesis", scenario_id)
    validate(anam, "anamnesis_output")

    brief = run_agent("brief", scenario_id)
    validate(brief, "clinical_context_brief")

    assert brief["safety_disclaimer"]            # guard rail
    assert brief["traceability_index"]           # guard rail
    return {"triage": triage, "ehr": ehr, "anamnesis": anam, "brief": brief}
```

```python
def evaluate(scenario_id, run):
    gold = load_json(f"scenarios/scenario_{scenario_id}_*.json")["gold_brief"]
    return {
        "triage_accuracy":     score_triage(run["triage"], gold),
        "retrieval_f1":        score_retrieval(run["ehr"], gold),
        "anamnesis_complete":  score_anamnesis(run["anamnesis"], gold),
        "hallucination_rate":  score_hallucination(run["brief"], run),
        "traceability":        score_traceability(run["brief"], run),
        # synthesis_accuracy + safety_compliance: human checklist, printed for the grader
    }
```

## Dependencies
```
pip install jsonschema
```
That's the only non-standard package. Everything else is the Python standard library + Jupyter.

## What the notebook proves
- The schemas are real and enforced (a malformed output is caught).
- The orchestration is real (agents are chained in the designed order).
- The evaluation is real (numbers come out, comparing to gold).
- The only thing "faked" is the *transport* — the prompts and outputs are genuine.

## Optional stretch (only if time allows)
Add a `USE_API = False` flag. When `True`, `run_agent()` calls the Claude API with the same v3
prompt; when `False`, it reads stored outputs. This makes the "one-function seam" from the
orchestrator design literally true in code and is a strong note for the report — but it is **not
required** for the submission.
