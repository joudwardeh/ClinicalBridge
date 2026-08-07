# EHR Retrieval Agent — Prompt Changelog

## v1 → v2
- **Symptom:** v1 wrote a flowing narrative summary and occasionally **paraphrased a dose**
  ("on a moderate dose of lisinopril") and merged facts without sources — untraceable.
- **Diagnosis of the cause:** No source-id requirement, no verbatim rule, output was prose.
- **Change:** Added JSON structure, mandatory `source_id` per item, the "only items in the record"
  rule, and a per-item relevance reason.
- **Result:** Output became traceable and parseable; invented items disappeared.

## v2 → v3
- **Symptom 1:** v2 silently skipped relevant-but-missing data — e.g., it never noted the absence of
  a recent potassium before an ACE-inhibitor BP alert. The gap was invisible to the synthesis agent.
- **Symptom 2:** v2 occasionally lightly reworded lab values/dates, risking subtle drift.
- **Symptom 3:** v2 sometimes dragged in clearly irrelevant chart items (low precision).
- **Changes:**
  - Added the required `data_gaps` array (negative-space prompting) with examples per metric.
  - Hardened the verbatim-copy rule ("do not round, paraphrase, or correct").
  - Added explicit relevance heuristics per metric and the instruction to leave noise out.
  - Added a pre-answer self-check and "use `[]`, don't omit keys."
- **Result:** Retrieval precision/recall reached the gold sets across scenarios; missing labs
  (e.g., Scenario 3 stale potassium/creatinine, Scenario 1 absent potassium) are now surfaced.
