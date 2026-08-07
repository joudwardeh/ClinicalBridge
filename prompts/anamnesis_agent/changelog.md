# Anamnesis Agent — Prompt Changelog

## v1 → v2
- **Symptom:** v1 interpreted self-report as fact and editorialized ("the patient is clearly
  developing heart failure") — both a diagnosis and a loss of the self-report distinction.
- **Diagnosis of the cause:** No source typing, no anti-diagnosis rule, prose output.
- **Change:** Added JSON, `reported_by` tagging, source ids, the "symptoms stay symptoms" rule, and
  domain buckets.
- **Result:** Self-report is preserved; symptom→diagnosis translation largely stopped.

## v2 → v3
- **Symptom 1 (the big one):** In Scenario 4 the anamnesis was NOT collected, and v2 **hallucinated
  plausible-sounding symptoms and adherence** to fill the template — exactly the failure this project
  must prevent.
- **Symptom 2:** v2 dropped informative negatives ("patient reports no symptoms").
- **Symptom 3:** v2 had no completeness signal, so the synthesis agent couldn't tell "absent" from
  "not asked".
- **Changes:**
  - Added the explicit **not-collected** handling block and the rule "do NOT fabricate to fill a gap."
  - Added the `extraction_completeness` object (present/absent/not_collected per domain).
  - Added the "negative findings can be relevant" rule and verbatim quoting of concerns.
  - Added a pre-answer self-check.
- **Result:** Scenario 4 now correctly returns empty arrays + `not_collected` + a clear gap note,
  with **zero fabricated** anamnesis. Extraction completeness across scenarios hit the gold targets.
