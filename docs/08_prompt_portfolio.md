# 08 — Prompt Engineering Portfolio

This is the graded core of a Prompt Engineering course: not just the final prompts, but the
**iteration story**. For each of the four agents we keep three versions and a changelog explaining
*why* each change was made and *what it fixed*.

## Folder layout

```
prompts/
├── alert_triage_agent/
│   ├── v1.md          <- naive first attempt (the "initial system prompt")
│   ├── v2.md          <- adds structure + safety
│   ├── v3.md          <- production version (use this in the demo)
│   └── changelog.md   <- what changed v1→v2→v3 and why
├── ehr_retrieval_agent/   (same four files)
├── anamnesis_agent/       (same four files)
└── synthesis_agent/       (same four files)
```

## The iteration philosophy (applies to every agent)

| Version | Theme | Typical problems it fixes |
|---|---|---|
| **v1** | *Make it work* — a plain role + task description | Vague, prose output, no schema, occasionally diagnoses, no citations |
| **v2** | *Make it safe & structured* — add JSON schema, safety rules, cite-or-omit | Output now parseable; diagnoses suppressed; but uncertainty/conflicts still weak |
| **v3** | *Make it robust* — few-shot exemplar, self-check step, calibrated confidence, negative-space prompting | Handles edge cases, surfaces gaps/conflicts, traceability ~1.0 |

## What to document per agent (in `changelog.md`)

For each version bump, record:
1. **Symptom** — the concrete failure observed (quote the bad output).
2. **Diagnosis** — why the prompt produced it.
3. **Change** — the exact prompt edit (show the added/changed lines).
4. **Result** — what improved, ideally with a metric delta.

### Example entry (Synthesis Agent, v1→v2)
> **Symptom:** v1 brief said *"The patient is in acute heart failure."* — a diagnosis, forbidden.
> **Diagnosis:** v1 only said "summarize the findings" with no framing constraint, so the model
> defaulted to clinical conclusions.
> **Change:** Added the rule *"Express possibilities ONLY as 'factors to consider', never as
> conclusions. You must not state or imply a diagnosis."* plus a banned-phrasing list.
> **Result:** Diagnosis language eliminated across all 5 scenarios; safety-compliance went FAIL→PASS.

## Cross-agent techniques catalogue (cite these in the report)

| Technique | Where used | Purpose |
|---|---|---|
| Role / persona prompting | all agents | Scope behavior, set non-diagnostic stance |
| Rubric-in-prompt | triage (urgency ladder), eval | Consistent, reproducible judgments |
| Cite-or-omit grounding | ehr, anamnesis, synthesis | Kill hallucination; force traceability |
| Verbatim-copy instruction | ehr | Prevent dose/lab paraphrase drift |
| Source-typing (`reported_by`) | anamnesis | Stop over-trusting self-report |
| Negative-space prompting | all (data_gaps) | Make "absence is information" explicit |
| Few-shot exemplar | synthesis | Lock tone, citation style, structure |
| Self-check / verify-before-emit | synthesis | Catch uncited claims pre-output |
| Constrained framing vocabulary | synthesis | "factors to consider", never diagnoses |
| Chain-of-thought then JSON | triage, synthesis | Reason first, emit clean structured output |
| Strict output contract (schema) | all | Machine-checkable, chainable hand-offs |

## How this maps to the grade
- The **report's Section 5** is built directly from these changelogs.
- The **evaluation scorecard** quantifies the improvement (e.g., hallucination rate v1 vs v3).
- Keeping v1 around (even though it's "worse") is the evidence of method — don't delete it.
