# 06 — Final Report Outline

Target length: ~12–18 pages plus appendices. Tune to your course rubric. Each section lists what to
write and which repo artifact to pull from.

## Title page
- ClinicalBridge: Bridging the Clinical Context Gap
- Course: COP-3442 Prompt Engineering — Final Project
- University: Bahçeşehir University
- Department: Artificial Intelligence Engineering Department
- Professor: Binnur Kurt
- Group Members: Kenan Eliyan (2286181), Rama Tamimi (2285460), Joud Wardeh (2282493)
- Date, "Educational prototype — fictional data only" banner.

## Abstract (½ page)
One paragraph: the clinical context gap, the multi-agent solution, that it is a no-API prototype on
synthetic data, and the headline result (e.g., "0 hallucinated claims across 5 scenarios,
traceability 1.0").

## 1. Introduction & Problem Statement
- The clinical context gap (from [01_project_objective.md](01_project_objective.md)).
- Why RPM alerts without context are dangerous and slow.
- Scope and the hard ethical guardrails (no diagnosis, no real data, human-in-loop).

## 2. Background & Related Concepts
- Clinical decision *support* vs. decision *making*.
- Multi-agent decomposition as a prompt-engineering strategy.
- The three data domains (EHR / RPM / Anamnesis).
- Brief note on why LLMs hallucinate and why that's the central risk here.

## 3. System Architecture
- The four agents + orchestrator (from [02](02_agent_design.md) and [03](03_orchestrator_design.md)).
- The pipeline diagram.
- The JSON-contract design and why typed hand-offs matter.

## 4. Data Design
- The 10 synthetic patients ([data/patients.json](../data/patients.json)).
- The five scenario archetypes and *why each one stresses a different failure mode*:
  missed medication, false alarm, silent deterioration, incomplete record, conflicting data.
- How gold-standard briefs were created.

## 5. Prompt Engineering Methodology  ← **the heart of the report**
- Techniques used per agent (role prompting, grounding, cite-or-omit, rubric-in-prompt,
  few-shot, self-check).
- The v1 → v2 → v3 iteration story for each agent (from [08_prompt_portfolio.md](08_prompt_portfolio.md)):
  what failed in v1, what the fix was, what improved. **Show before/after prompt snippets.**
- The anti-hallucination + traceability strategy in depth.

## 6. Implementation (No-API Prototype)
- The notebook + orchestrator + schema validation.
- The no-API stored-output workflow and why it's valid for this project.
- The one-function seam to a real API.

## 7. Evaluation
- The seven metrics ([04_evaluation_framework.md](04_evaluation_framework.md)).
- The 5×7 scorecard with real numbers.
- Auto-scored vs. human-scored metrics, and why.
- Error analysis: where did the system under-perform, and what prompt change would help?

## 8. Results & Discussion
- Headline numbers (hallucination rate, traceability, triage accuracy).
- What the v1→v3 iteration bought you, quantitatively.
- Honest limitations (next section feeds this).

## 9. Limitations & Ethical Considerations
- Synthetic data only; not validated clinically; not a medical device.
- Risks of automation bias even in a "support" tool.
- Why human review is non-negotiable; what would be required before any real use
  (clinical validation, regulatory review, bias audit, real evaluation).

## 10. Future Work
- Live API integration; true parallel retrieval.
- More scenarios + adversarial test cases.
- Confidence calibration study.
- A real clinician-in-the-loop UI.

## 11. Conclusion
- Restate the contribution: a safe-by-design, fully-traceable, multi-agent context assembler, and
  the prompt-engineering lessons that made it work.

## Appendices
- **A.** Full system prompts (v3) for all four agents.
- **B.** The five scenarios in full (inputs + gold briefs).
- **C.** All seven JSON schemas.
- **D.** Prompt iteration changelogs (v1/v2/v3 diffs).
- **E.** Full evaluation scorecard + per-claim traceability audit.
- **F.** Notebook source.

## Writing tips
- Lead Section 5 with a concrete failure: "v1 of the Synthesis Agent wrote 'patient is in heart
  failure' — a diagnosis. Here's the prompt change that eliminated it." Graders love a clear
  before/after.
- Every claim about results should be backed by a number from the scorecard.
- Keep the safety framing consistent end-to-end; it's the spine of the project.
