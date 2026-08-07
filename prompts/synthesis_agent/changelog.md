# Synthesis Agent — Prompt Changelog

This is the agent where prompt engineering mattered most; the failures here are the ones the project
exists to prevent. Lead the report's Section 5 with this story.

## v1 → v2
- **Symptom (safety failure):** v1 wrote *"The patient is in acute heart failure exacerbation; start
  IV diuresis."* — a diagnosis **and** a treatment order, from a support tool. It also stated facts
  with no sources.
- **Diagnosis of the cause:** v1 said only "explain what is going on and what they should do" — that
  framing invites conclusions and orders, and there was no citation requirement.
- **Change:** Added JSON structure; the rule "you do NOT diagnose — express possibilities ONLY as
  'factors to consider'"; a banned-phrasing note; and "every clinical claim must cite a source id".
- **Result:** Diagnosis-as-fact and treatment orders were eliminated; safety-compliance went
  FAIL → PASS. Claims became cited.

## v2 → v3
- **Symptom 1:** In Scenario 5 (conflicting data) v2 **silently chose** the EHR med list over the
  patient's report and never surfaced the contradiction — hiding the single most important finding.
- **Symptom 2:** v2 often **omitted the missing-data section and the safety disclaimer** when the
  case looked "clean", so uncertainty was under-communicated.
- **Symptom 3:** A few claims still slipped through **uncited**, hurting traceability.
- **Symptom 4:** v2 didn't reconcile urgency disagreements between triage and the assembled picture.
- **Changes:**
  - Added the mandatory `data_conflicts` array + the rule "surface conflicts, never silently resolve,
    cite BOTH sources."
  - Made `missing_data_and_uncertainty`, `safety_disclaimer`, and `traceability_index` REQUIRED and
    non-empty.
  - Added the **verify-before-emit** self-check (every claim must resolve to a cited, real id).
  - Added "keep the higher concern" + `adjusted_from_triage`.
- **Result:** Scenario 5 conflict is now surfaced with both sources; hallucination rate measured at
  **0.0** and traceability **1.0** across all 5 scenarios; safety compliance PASS on every scenario.
