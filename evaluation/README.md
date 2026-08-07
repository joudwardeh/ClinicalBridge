# Evaluation

Implements the framework in [../docs/04_evaluation_framework.md](../docs/04_evaluation_framework.md).

## Files
- `metrics.py` — the scoring functions (no external dependencies).

## Auto-scored metrics (in `metrics.py`)
| Function | Metric |
|---|---|
| `score_triage` | 1. Triage accuracy (urgency + validity vs gold) |
| `score_retrieval` | 2. Retrieval relevance (precision / recall / F1) |
| `score_anamnesis` | 3. Anamnesis extraction completeness (recall + domain coverage) |
| `score_hallucination_and_traceability` | 5. Hallucination rate + 6. Source traceability |
| `automated_safety_checks` | partial 7. Safety (disclaimer, missing-data section, banned-phrase scan) |
| `evaluate_run` | runs all of the above for one scenario |

## Human-scored metrics
- **4. Synthesis accuracy** — tick the per-scenario `gold_checklist` (printed by
  `metrics.print_human_checklist`).
- **7. Safety compliance** — the full binary checklist; the automated checks are a pre-filter, not a
  substitute for human judgment.

## How citations are resolved
`gather_valid_source_ids(scenario, patient_rpm)` builds the universe of legal source ids from the
scenario's EHR + anamnesis context plus the patient's RPM baselines/readings (and the literal
`RPM.alert`). A brief claim is **traceable** if it has ≥1 citation and every citation is in that
universe; otherwise it counts toward the **hallucination rate**.

## Run it
The notebook does this for you, but standalone:
```python
import json, sys; from pathlib import Path
ROOT = Path("..")                       # repo root
sys.path.insert(0, str(ROOT / "evaluation")); import metrics
scenario = json.load(open(ROOT / "scenarios/scenario_1_missed_medication.json", encoding="utf-8"))
outputs  = json.load(open(ROOT / "agent_outputs/scenario_1_outputs.json", encoding="utf-8"))
patients = {p["patient_id"]: p for p in json.load(open(ROOT / "data/patients.json", encoding="utf-8"))["patients"]}
run = {"triage": outputs["triage"], "ehr": outputs["ehr"], "anamnesis": outputs["anamnesis"], "brief": outputs["brief"]}
print(metrics.evaluate_run(run, scenario, patients[scenario["patient_id"]]["rpm"]))
```
