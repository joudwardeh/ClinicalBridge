# 07 — Demo Walkthrough Plan

**Project:** ClinicalBridge: Bridging the Clinical Context Gap  
**Course:** COP-3442 Prompt Engineering  
**University:** Bahçeşehir University  
**Department:** Artificial Intelligence Engineering Department  
**Professor:** Binnur Kurt  
**Group Members:**
- Kenan Eliyan — 2286181
- Rama Tamimi — 2285460
- Joud Wardeh — 2282493

A ~8–10 minute live demo that takes two contrasting scenarios end-to-end. The contrast is the point:
**Scenario 1 (Missed Medication)** shows the system assembling a clear actionable story;
**Scenario 3 (Silent Deterioration)** shows it catching something *no single alert* would reveal.

---

## Recording the demo with `python main.py --demo` (recommended)

The fastest way to record is the built-in **demo mode**. It prints a clean, ASCII, step-by-step
walkthrough of one scenario — raw alert, each agent's output, the final 8-section brief, and the
metrics — in one screen-recordable scroll. No API key, fully reproducible.

```bash
python main.py --demo 1                      # Scenario 1: Missed Medication
python main.py --demo 3                      # Scenario 3: Silent Deterioration
python main.py --demo 1 --save-transcript    # also writes outputs/demo_scenario_1_transcript.md
python main.py --demo 3 --save-transcript    # also writes outputs/demo_scenario_3_transcript.md
```

Before running either scenario, briefly show the high-level architecture diagram (in
[`docs/09_architecture_diagrams.md`](09_architecture_diagrams.md) or the README) so viewers see the
four-agent pipeline before watching it run on Scenario 1 and Scenario 3.

**Recording flow (~4 min each):** run `--demo 1`, scroll slowly top-to-bottom while narrating; then
run `--demo 3` for the trend case; add `--save-transcript` to hand in the Markdown alongside the video.

### Speaking script — Scenario 1 (Missed Medication)
- "All the clinician normally gets is this raw alert: **blood pressure 182/104**." *(point to Raw RPM Alert)*
- "**Step 1** — the Triage agent prioritizes it as **URGENT** and, crucially, does **not** diagnose; it
  just decides what context to fetch."
- "**Step 2** — EHR retrieval pulls only the relevant items — the lisinopril with its refill date — and
  flags that there's **no recent potassium**."
- "**Step 3** — the Anamnesis agent captures the patient's own words: she **ran out of her BP pill** a
  week ago."
- "**Step 4** — Synthesis ties it together as a **factor to consider** — a medication lapse — with
  every claim **cited to a source**. Note the missing-data section and the safety disclaimer."
- "**Step 5** — the metrics: **hallucination rate 0.0, traceability 1.0**. Nothing was invented."

### Speaking script — Scenario 3 (Silent Deterioration)
- "No single reading here is dramatic — the weight creeps up about half a kilo a day."
- "Triage still escalates to **URGENT** based on the **trend**, ignoring the device's 'medium' rating."
- "EHR shows heart failure and a diuretic; the patient reports tight shoes and breathlessness on stairs."
- "Synthesis connects the trend across all three systems into one **cited** picture — and still
  **refuses to diagnose** decompensation, flagging what we don't know."
- "Metrics again show **0 hallucinations and full traceability**."

### Using the notebook as the annotated demo
For a more visual, cell-by-cell version, open `notebook/clinicalbridge_prototype.ipynb` and
**Restart & Run All**. It renders the same brief and scorecard with Markdown formatting, which records
well for an annotated walkthrough. The CLI `--demo` mode is better for a quick, reproducible screen
capture; the notebook is better for a richly formatted on-screen version.

---

## Live walkthrough (alternative / deeper narration)

The sections below are the longer manual narration, useful if you prefer to step through the JSON
files and notebook cells by hand instead of (or in addition to) the `--demo` command.

## Before you start (30 sec)
- Open the notebook `notebook/clinicalbridge_prototype.ipynb`, "Restart & Run All" so everything is
  fresh.
- State the disclaimer out loud: *"All data is fictional; this is a decision-support prototype, it
  does not diagnose."*

---

## Part A — Scenario 1: Missed Medication (≈4 min)

**1. Show the raw alert (the "before").**
> "Here's all the clinician would normally get: `BP 182/104, severity high`. No story."

Display `scenarios/scenario_1_missed_medication.json → rpm_alert`.

**2. Run Triage.**
Show `triage_output`: urgency `urgent`, validity `likely_valid`, and the retrieval plan
("pull antihypertensives, refill dates, renal labs; ask about adherence").
> "The triage agent didn't diagnose — it prioritized and told the next agents what to fetch."

**3. Run EHR Retrieval.**
Show it pulled lisinopril with its **last refill date** and a 30-day supply — and flagged a
**refill gap**. Point out it left irrelevant chart items behind.

**4. Run Anamnesis.**
Show the extracted self-report: *"ran out of my BP pills about a week ago."* Labeled as
patient-reported.

**5. Run Synthesis → the Brief.**
Walk through the brief top to bottom:
- Alert summary + snapshot.
- Contributing factor: *medication lapse* — and trace each part of the claim to its source id live
  (refill math from EHR, "ran out" from anamnesis).
- Missing-data flag (e.g., no recent potassium).
- Suggested considerations (confirm adherence, recheck BP, consider refill) — **not orders**.
- Read the safety disclaimer.

**6. Show the score.**
Display the evaluation cell: hallucination rate `0.0`, traceability `1.0`, triage accuracy `1.0`.
> "Every claim resolved to a source. Nothing invented."

---

## Part B — Scenario 3: Silent Deterioration (≈4 min)

**1. Show why this one is sneaky.**
> "No single reading is dramatic. Each day's weight is 'just' +0.5 kg. The threshold for any one
> reading isn't even breached hard. A human skimming might wave it through."

Display the RPM trend (gradual weight gain + slow SpO2 drift).

**2. Run Triage.**
Show it caught the *trend* and set urgency `monitor`→`urgent` with rationale tied to the cumulative
change and the CHF history flag — not to any single number.

**3. Run EHR + Anamnesis.**
EHR: heart-failure diagnosis + diuretic. Anamnesis: *"shoes feel tight, a bit more short of breath
on the stairs."*

**4. Run Synthesis → the Brief.**
Highlight the **trend-based contributing factor** ("cumulative +X kg over N days against a CHF
baseline, with patient-reported exertional dyspnea") — every piece cited. Show the uncertainty
framing.

**5. Score it, and make the closing point.**
> "This is the case that justifies the whole project: the value isn't summarizing one alert, it's
> connecting a quiet trend across three systems into one traceable picture — while still refusing to
> diagnose and still flagging what we don't know."

---

## Backup talking points (if asked)
- **"What if it hallucinates?"** → show the hallucination metric + the cite-or-omit rule; show a v1
  output that *did* hallucinate and the v3 that doesn't.
- **"Isn't this diagnosing?"** → show the constrained "factors to consider" language and the safety
  checklist.
- **"Why no API?"** → prompt design is the graded skill; the seam to a real API is one function.
- **"What about a false alarm?"** → quickly show Scenario 2's brief flagging the artifact while
  still retrieving context.

## What to have on screen at the finale
The 5×7 scorecard, so the last thing the room sees is: **0 hallucinations, full traceability,
safety PASS across all five scenarios.**
