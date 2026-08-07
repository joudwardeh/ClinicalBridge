# 02 — Agent Design

Four specialized agents plus an orchestrator. Each agent is **narrow on purpose**: a small job is
easier to prompt, easier to test, and easier to keep safe. Every agent emits **schema-valid JSON**
(see [`/schemas`](../schemas)) so the orchestrator can chain them mechanically.

A shared rule binds all four agents:

> **CITE-OR-OMIT.** If a statement is not supported by a provided source item, it does not go in the
> output. Every clinical claim carries a citation to its source id (e.g. `EHR.med.002`, `RPM.alert`,
> `ANAMNESIS.symptom.1`). The agents never invent values, never diagnose, and always prefer
> "unknown / not in record" over a guess.

---

## Agent 1 — Alert Triage Agent

**Purpose.** Be the front door. Turn a raw RPM alert into a prioritized, validity-checked work order
that tells the rest of the system *how urgent this is* and *what context to go fetch*.

**Input**
- One RPM alert object (`schemas/rpm_alert.schema.json`).
- The patient's RPM baselines + thresholds (for context on how far out-of-range the reading is).

**Output** (`schemas/triage_output.schema.json`)
- `urgency_level`: `routine` | `monitor` | `urgent` | `emergent` (prioritization, **not** diagnosis).
- `urgency_rationale`: short text, tied to numbers.
- `alert_validity`: `likely_valid` | `possible_artifact` | `insufficient_data`.
- `validity_rationale`.
- `retrieval_plan`: what the EHR and Anamnesis agents should look for.
- `missing_data_flags`, `safety_flags`, `confidence`.

**Safety rules**
- Never state or imply a diagnosis. Urgency ≠ diagnosis.
- When in doubt, triage *up*, and say why.
- Mark physiologically implausible readings (e.g., SpO2 = 40% in a talking patient) as
  `possible_artifact` — but **still** retrieve context; never dismiss outright.
- If the alert lacks the data to judge urgency, return `insufficient_data` and say what's missing.

**Prompt-engineering techniques**
- **Role prompting** (a triage nurse persona, explicitly non-diagnostic).
- **Rubric-in-prompt**: the urgency ladder is defined inline so judgments are consistent.
- **Chain-of-thought, then structured output**: reason in a scratch field, then emit clean JSON.
- **Refusal scaffolding**: explicit "if you cannot tell, say insufficient_data" branch.

---

## Agent 2 — EHR Retrieval Agent

**Purpose.** Given the alert + the triage retrieval plan, pull **only the relevant** EHR items.
This is a *relevance and grounding* task, not a summarization-of-everything task.

**Input**
- The full EHR record (`schemas/ehr_record.schema.json`).
- The alert and the triage `retrieval_plan`.

**Output** (`schemas/ehr_retrieval_output.schema.json`)
- `relevant_diagnoses`, `relevant_medications`, `relevant_labs`, `relevant_allergies`,
  `relevant_visit_notes` — each item copied verbatim with its source id and a one-line
  `relevance_reason`.
- `data_gaps`: relevant things that *should* exist but don't (e.g., no recent potassium).
- `retrieval_confidence`.

**Safety rules**
- Copy values **verbatim**; never round, paraphrase a dose, or "correct" a lab.
- Include an item only if you can name why it's relevant to *this* alert.
- Never infer a diagnosis or medication that isn't in the record.
- Explicitly list expected-but-absent data as `data_gaps` instead of silently skipping.

**Prompt-engineering techniques**
- **Grounding constraint** ("every item must carry its source id; do not summarize items not present").
- **Relevance rubric** keyed off the alert metric (e.g., for a BP alert: antihypertensives, renal
  labs, cardiac diagnoses).
- **Negative space prompting**: explicitly ask "what relevant data is *missing*?"
- **Verbatim-copy instruction** to block paraphrase drift.

---

## Agent 3 — Anamnesis Agent

**Purpose.** Extract the patient-reported context relevant to the alert: symptoms, medication
adherence, lifestyle factors, family history, and the patient's own concerns.

**Input**
- The full anamnesis record (`schemas/anamnesis_record.schema.json`).
- The alert and the triage `retrieval_plan`.

**Output** (`schemas/anamnesis_output.schema.json`)
- `relevant_symptoms`, `adherence_findings`, `lifestyle_factors`, `relevant_family_history`,
  `patient_concerns` — each with a source id and relevance reason.
- `extraction_completeness`: which expected anamnesis domains were present vs. absent.
- `data_gaps`.

**Safety rules**
- Distinguish **patient-reported** from **clinically confirmed** — everything here is self-report
  and must be labeled as such.
- Do not translate a symptom into a diagnosis ("chest pain" stays "chest pain", never "angina").
- Preserve the patient's own words for concerns where possible.
- Flag absent domains (e.g., "no adherence information collected") as gaps.

**Prompt-engineering techniques**
- **Source-typing**: forces a `reported_by: patient` tag to prevent over-trusting self-report.
- **Domain checklist** so completeness can be scored.
- **Quote-preservation instruction** for patient concerns.
- **Anti-diagnosis guard** repeated at the symptom level.

---

## Agent 4 — Synthesis Agent

**Purpose.** Merge the three structured outputs into the final **Clinical Context Brief** — the only
artifact a clinician actually reads. This is where conflicts, gaps, and uncertainty are reconciled
and where traceability is enforced.

**Input**
- Triage output + EHR retrieval output + Anamnesis output.
- The original alert.

**Output** (`schemas/clinical_context_brief.schema.json`)
- `alert_summary`, `patient_snapshot`.
- `contextual_findings` — grouped, each citing its source.
- `possible_contributing_factors` — framed as *factors to consider*, each traceable; **never
  diagnoses**.
- `data_conflicts` — explicit contradictions between sources.
- `missing_data_and_uncertainty`.
- `suggested_clinician_considerations` — questions/checks, not orders.
- `urgency_assessment` (carried from triage, may be adjusted with rationale).
- `safety_disclaimer`, `traceability_index`, `overall_confidence`.

**Safety rules**
- **Every** clinical claim must cite a source id present in its inputs. No citation → not in brief.
- Phrase contributing factors as hypotheses to *consider*, with explicit uncertainty; never
  "the patient has X."
- Surface conflicts; do **not** silently pick a winner.
- Always include the missing-data section and the safety disclaimer, even if short.
- If inputs disagree on urgency, keep the *higher* and explain.

**Prompt-engineering techniques**
- **Output contract / strict schema** with a required `traceability_index`.
- **Few-shot exemplar**: a gold brief shows the exact tone and citation style.
- **Self-check step**: the prompt asks the model to verify each claim has a citation before emitting.
- **Constrained framing language** ("factors to consider", "patient-reported", "not a diagnosis").
- **Conflict-first prompting**: explicitly instructs the model to hunt for contradictions.

---

## Shared design conventions

| Convention | Why |
|---|---|
| Source ids like `EHR.lab.003`, `RPM.alert`, `ANAMNESIS.symptom.2` | Makes traceability machine-checkable |
| `confidence` ∈ {low, medium, high} on every agent | Calibrated uncertainty is gradeable |
| `data_gaps` is a required array everywhere | Forces "absence is information" thinking |
| JSON only, no prose outside the object | Lets the orchestrator chain agents mechanically |
| A `notes_for_reviewer` free-text field | Human-in-the-loop transparency without polluting structured fields |
