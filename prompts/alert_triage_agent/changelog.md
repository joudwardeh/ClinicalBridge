# Alert Triage Agent — Prompt Changelog

## v1 → v2
- **Symptom:** v1 returned free-form prose ("This looks pretty serious, probably high blood
  pressure issues...") — unparseable and it *named a likely cause* (a soft diagnosis).
- **Diagnosis of the cause:** No output contract and no anti-diagnosis rule; the model defaulted to
  speculating about disease.
- **Change:** Added a strict JSON output contract, an explicit urgency rubric, and the rule
  "you do NOT diagnose; urgency is prioritization only." Added "when in doubt, triage up."
- **Result:** Output became machine-parseable; overt diagnosis language dropped sharply.

## v2 → v3
- **Symptom 1:** On a physiologically odd reading (SpO2 40% in a talking patient) v2 sometimes set
  `routine` and stopped — effectively dismissing a possible artifact without gathering context.
- **Symptom 2:** v2 had no way to say "I can't tell" and would force an urgency guess on thin input.
- **Symptom 3:** v2 was anchored by the device `severity_raw`, under-triaging a `medium`-rated but
  clinically important weight trend (Scenario 3).
- **Changes:**
  - Added `possible_artifact` + `insufficient_data` validity options and the rule that an artifact
    still requires a retrieval plan.
  - Added the explicit instruction to ignore `severity_raw` as a clinical judgment.
  - Added `reasoning_scratch` (reason first), `missing_data_flags`, `safety_flags`, and `citations`.
  - Added a pre-answer self-check.
- **Result:** Correctly escalated Scenario 3 to `urgent` despite the `medium` device rating; stopped
  dismissing odd readings; triage accuracy across the 5 scenarios reached the gold targets.
