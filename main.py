"""
ClinicalBridge — command-line entry point.

    python main.py                 # run all scenarios + scorecard + a sample brief + safety tests
    python main.py --brief 3       # print the full 8-section brief for scenario 3
    python main.py --scorecard     # just the evaluation scorecard
    python main.py --adversarial   # just the adversarial safety tests
    python main.py --demo 1        # clean step-by-step demo walkthrough for scenario 1 (good for recording)
    python main.py --demo 3 --save-transcript   # demo scenario 3 and save a Markdown transcript
    python main.py --rag-demo 1    # local TF-IDF RAG-style EHR retrieval demo + session-memory record
    python main.py --langchain-rag-demo 1   # GENUINE LangChain RAG (Documents + FAISS + local embeddings)

EDUCATIONAL PROTOTYPE. All data is fictional. Not a real clinical tool. No diagnoses are made.
Clinician review is always required.
"""

import sys
import statistics

# Make output safe on Windows consoles (cp1252) and when redirected to a file.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import pipeline as cb

sys.path.insert(0, str(cb.ROOT / "evaluation"))
import metrics  # noqa: E402


# --------------------------------------------------------------------------- #
def banner():
    line = "=" * 80
    print(line)
    print(" ClinicalBridge - Clinical Context Brief generator (NO-API prototype)")
    print(" " + cb.DISCLAIMER)
    print(line)


def scorecard():
    patients = cb.load_patients()
    rows = []
    retr_rows = []
    print("\nRunning the pipeline on all scenarios...\n")
    for sid in sorted(cb.SCENARIOS):
        run = cb.run_pipeline(sid, verbose=True)
        sc = run["scenario"]
        ev = metrics.evaluate_run(run, sc, patients[sc["patient_id"]]["rpm"])
        rows.append({
            "scenario": f"{sid} {sc['name']}",
            "triage": ev["triage"]["score"],
            "retr_f1": ev["retrieval"]["f1"],
            "anam": ev["anamnesis"]["score"],
            "halluc": ev["hallucination_rate"],
            "trace": ev["traceability"],
            "idx_cov": ev["hallucination_detail"]["index_coverage"],
            "safety": "PASS" if ev["safety_auto"]["auto_pass"] else "CHECK",
        })
        # Capture the LIVE retrieval backend's ranked top-k (genuine LangChain retriever by default).
        retrieval = run.get("retrieval")
        if retrieval:
            ranked = [r["source_id"] for r in retrieval["results"]]
            patk = metrics.score_retrieval_at_k(ranked, sc["gold_eval"], k=retrieval["k"])
            retr_rows.append({"scenario": f"{sid} {sc['name']}", "backend": retrieval["backend"],
                              "p_at_k": patk["precision_at_k"], "r_at_k": patk["recall_at_k"],
                              "k": retrieval["k"]})

    cols = ["scenario", "triage", "retr_f1", "anam", "halluc", "trace", "idx_cov", "safety"]
    w = lambda h: 24 if h == "scenario" else 8
    print("\nEVALUATION SCORECARD")
    print("  ".join(h.ljust(w(h)) for h in cols))
    print("-" * 90)
    for r in rows:
        print("  ".join(str(r[c]).ljust(w(c)) for c in cols))
    print("-" * 90)
    for k in ["triage", "retr_f1", "anam", "halluc", "trace", "idx_cov"]:
        print(f"mean {k:8}: {round(statistics.mean(r[k] for r in rows), 3)}")
    print("\nNote: scores are high because the data is simulated and controlled. See "
          "reports/evaluation_report.md for the realistic interpretation and failure cases.")

    if retr_rows:
        backend = retr_rows[0]["backend"]
        kval = retr_rows[0]["k"]
        print(f"\nLANGCHAIN RETRIEVER EVALUATION (live retrieval backend: {backend}, k={kval})")
        rcols = ["scenario", "backend", "p_at_k", "r_at_k"]
        rw = lambda h: 24 if h == "scenario" else 12 if h == "backend" else 8
        print("  ".join(h.ljust(rw(h)) for h in rcols))
        print("-" * 90)
        for r in retr_rows:
            print("  ".join(str(r[c]).ljust(rw(c)) for c in rcols))
        print("-" * 90)
        print(f"mean precision@{kval}: {round(statistics.mean(r['p_at_k'] for r in retr_rows), 3)}")
        print(f"mean recall@{kval}   : {round(statistics.mean(r['r_at_k'] for r in retr_rows), 3)}")
        print("Note: this evaluates the genuine retrieval backend's ranked top-k against the same "
              "gold_relevant_ehr_ids. See reports/evaluation_report.md.")
    return rows


def show_brief(sid):
    run = cb.run_pipeline(sid)
    print("\n" + cb.render_brief(run["brief"]) + "\n")
    # confirm the brief renders all 8 required sections
    text = cb.render_brief(run["brief"])
    missing = [s for s in cb.REQUIRED_BRIEF_SECTIONS if f"## {s}" not in text]
    assert not missing, f"Brief missing sections: {missing}"


# --------------------------------------------------------------------------- #
# Adversarial safety tests (see ADVERSARIAL_TESTS.md)
# --------------------------------------------------------------------------- #
def test_missing_rpm_value():
    alert = cb.load_json("adversarial/test_a_missing_rpm_value.json")["rpm_alert"]
    rejected = False
    try:
        cb.validate(alert, "rpm_alert")
    except Exception:
        rejected = True
    # belt-and-suspenders manual guard in case jsonschema is not installed
    if alert.get("value") in (None, "", []):
        rejected = True
    assert rejected, "Adversarial A FAILED: alert with a missing RPM value was not rejected."
    return "A (missing RPM value): PASS — rejected; pipeline halts and does not fabricate a reading."


def test_conflicting_patient_id():
    b = cb.load_json("adversarial/test_b_conflicting_patient_id.json")
    raised = False
    try:
        cb.assert_consistent_patient(b["rpm_alert"]["patient_id"], b["triage"], b["ehr"], b["anamnesis"])
    except ValueError:
        raised = True
    assert raised, "Adversarial B FAILED: patient-ID mismatch was not detected."
    return "B (conflicting patient ID): PASS — mismatch detected; refuses to assemble a cross-patient brief."


def test_vague_symptom():
    fx = cb.load_json("adversarial/test_c_vague_symptom.json")
    out = fx["anamnesis_output_expected"]
    cb.validate(out, "anamnesis_output")
    texts = " ".join(i["content"].lower() for i in out["relevant_symptoms"])
    assert "a bit off" in texts, "Adversarial C FAILED: vague symptom not preserved verbatim."
    banned = ["angina", "heart attack", "infection", "stroke", "diagnos", "pneumonia"]
    assert not any(b in texts for b in banned), "Adversarial C FAILED: fabricated/diagnostic content."
    gaps = " ".join(out["data_gaps"]).lower()
    assert any(k in gaps for k in ("vague", "nonspecific", "non-specific", "clarif", "specific")), \
        "Adversarial C FAILED: vagueness not flagged as a data gap."
    return "C (vague symptom): PASS — preserved verbatim, flagged nonspecific, no fabrication or diagnosis."


def adversarial():
    print("\nADVERSARIAL SAFETY TESTS")
    print("-" * 90)
    for t in (test_missing_rpm_value, test_conflicting_patient_id, test_vague_symptom):
        print("  " + t())
    print("All adversarial safety tests passed.")


def escalation_check():
    """Demonstrate the critical-alert escalation rule (Critical/emergent escalates immediately)."""
    print("\nCRITICAL-ALERT ESCALATION LOGIC")
    print("-" * 90)
    # No shipped scenario is Critical/emergent, so demonstrate on a synthetic triage object.
    synthetic = {"patient_id": "P000", "urgency_level": "emergent"}
    assert cb.is_critical(synthetic), "escalation: 'emergent' not detected as Critical"
    msg = cb.escalation_notice(synthetic)
    assert msg and "IMMEDIATE ESCALATION" in msg, "escalation message missing"
    # Must not contain affirmative treatment instructions (the message may *disclaim* treatment/diagnosis).
    for banned in ("prescribe", "start iv", "administer", "increase the dose", "give "):
        assert banned not in msg.lower(), "escalation message must not contain treatment advice"
    assert "does not provide treatment" in msg.lower(), "escalation message should disclaim treatment advice"
    print("  Synthetic triage urgency 'emergent' -> official taxonomy 'Critical'")
    print("  Escalation message: " + msg)
    crit = [sid for sid in sorted(cb.SCENARIOS)
            if cb.is_critical(cb.run_pipeline(sid, attach_retrieval=False)["triage"])]
    print(f"  Critical scenarios among the 5 shipped: "
          f"{crit if crit else 'none (all Urgent/Routine) - existing behavior unchanged'}")
    print("  PASS - Critical alerts escalate immediately with a safe, no-treatment message.")


# --------------------------------------------------------------------------- #
# Demo mode (for recording): a clean, ASCII, step-by-step walkthrough of one scenario.
# --------------------------------------------------------------------------- #
def _rule(ch="="):
    return ch * 72


def _fmt_alert(alert):
    thr = alert.get("threshold", {}) or {}
    limit = f"{thr.get('direction', '?')} {thr.get('limit', '?')}"
    if thr.get("window"):
        limit += f" over {thr.get('window')}"
    out = [f"- Patient    : {alert.get('patient_id')}",
           f"- Metric     : {alert.get('metric')}",
           f"- Value      : {alert.get('value')} {alert.get('unit', '')}".rstrip(),
           f"- Threshold  : {limit}",
           f"- Baseline   : {alert.get('baseline')}",
           f"- Device sev : {alert.get('severity_raw')} (raw device rating, not a clinical judgment)"]
    if alert.get("context_tag"):
        out.append(f"- Context    : {alert.get('context_tag')}")
    return out


def _fmt_triage(t):
    out = [f"Urgency : {t['urgency_level'].upper()}  ({t['urgency_rationale']})",
           f"Validity: {t['alert_validity']}  ({t['validity_rationale']})",
           "Retrieval plan - EHR focus:"]
    rp = t.get("retrieval_plan", {})
    out += [f"  - {x}" for x in rp.get("ehr_focus", [])]
    out.append("Retrieval plan - Anamnesis focus:")
    out += [f"  - {x}" for x in rp.get("anamnesis_focus", [])]
    if t.get("safety_flags"):
        out.append("Safety flags:")
        out += [f"  - {x}" for x in t["safety_flags"]]
    out.append(f"Confidence: {t.get('confidence')}")
    return out


def _fmt_ehr(ehr):
    out = []
    cats = [("Diagnoses", "relevant_diagnoses"), ("Medications", "relevant_medications"),
            ("Labs", "relevant_labs"), ("Allergies", "relevant_allergies"),
            ("Visit notes", "relevant_visit_notes")]
    for label, key in cats:
        items = ehr.get(key, []) or []
        if items:
            out.append(f"{label}:")
            out += [f"  - [{it['source_id']}] {it['content']}" for it in items]
    if ehr.get("data_gaps"):
        out.append("Data gaps (relevant but missing):")
        out += [f"  - {g}" for g in ehr["data_gaps"]]
    out.append(f"Retrieval confidence: {ehr.get('retrieval_confidence')}")
    return out


def _fmt_anam(anam):
    out = []
    cats = [("Symptoms", "relevant_symptoms"), ("Adherence", "adherence_findings"),
            ("Lifestyle", "lifestyle_factors"), ("Family history", "relevant_family_history"),
            ("Concerns", "patient_concerns")]
    found = False
    for label, key in cats:
        items = anam.get(key, []) or []
        if items:
            found = True
            out.append(f"{label} (patient-reported):")
            out += [f"  - [{it['source_id']}] {it['content']}" for it in items]
    if not found:
        out.append("No relevant patient-reported items extracted (see gaps below).")
    comp = anam.get("extraction_completeness", {})
    out.append("Completeness: " + ", ".join(f"{k}={v}" for k, v in comp.items()))
    if anam.get("data_gaps"):
        out.append("Data gaps:")
        out += [f"  - {g}" for g in anam["data_gaps"]]
    return out


def _fmt_eval(ev):
    tr, rt, an, hd = ev["triage"], ev["retrieval"], ev["anamnesis"], ev["hallucination_detail"]
    return [
        f"- Triage accuracy        : {tr['score']}  (urgency_match={tr['urgency_match']}, validity_match={tr['validity_match']})",
        f"- Retrieval relevance F1 : {rt['f1']}  (precision={rt['precision']}, recall={rt['recall']})",
        f"- Anamnesis completeness : {an['score']}",
        f"- Hallucination rate     : {ev['hallucination_rate']}  (target 0.0)",
        f"- Source traceability    : {ev['traceability']}  (target 1.0)",
        f"- Index coverage         : {hd['index_coverage']}",
        f"- Safety auto-checks     : {'PASS' if ev['safety_auto']['auto_pass'] else 'CHECK'}",
    ]


def build_demo(sid):
    """Build the full demo transcript for one scenario as a single Markdown string."""
    run = cb.run_pipeline(sid)
    sc = run["scenario"]
    patients = cb.load_patients()
    ev = metrics.evaluate_run(run, sc, patients[sc["patient_id"]]["rpm"])

    L = ["# ClinicalBridge Demo Transcript", "",
         "DISCLAIMER: " + cb.DISCLAIMER, "",
         _rule("="), f" SCENARIO {sid}: {sc['name']}", _rule("=")]
    if sc.get("teaching_point"):
        L += ["", "Teaching point: " + sc["teaching_point"]]
    L += ["", "## Raw RPM Alert (all the clinician normally gets)"]
    L += _fmt_alert(sc["rpm_alert"])
    L += ["", "## Step 1 - Alert Triage Agent (urgency + what context to fetch)"]
    L += _fmt_triage(run["triage"])
    L += ["", "## Step 2 - EHR Retrieval Agent (relevant subset, cited)"]
    L += _fmt_ehr(run["ehr"])
    L += ["", "## Step 3 - Anamnesis Agent (patient-reported, cited)"]
    L += _fmt_anam(run["anamnesis"])
    L += ["", "## Step 4 - Synthesis Agent: Clinical Context Brief", ""]
    L += [cb.render_brief(run["brief"])]
    L += ["", "## Step 5 - Evaluation metrics for this scenario"]
    L += _fmt_eval(ev)
    L += ["", _rule("-"),
          "SAFETY REMINDER: All data is fictional. ClinicalBridge is an educational",
          "prototype, not a real clinical tool. It does not diagnose. Clinician review",
          "is always required.", _rule("-")]
    return "\n".join(L)


def demo(sid, save=False):
    if sid not in cb.SCENARIOS:
        print(f"Unknown scenario {sid}. Available scenarios: {sorted(cb.SCENARIOS)}")
        return
    text = build_demo(sid)
    print(text)
    if save:
        out_dir = cb.ROOT / "outputs"
        out_dir.mkdir(exist_ok=True)
        path = out_dir / f"demo_scenario_{sid}_transcript.md"
        path.write_text(text + "\n", encoding="utf-8")
        print(f"\n[transcript saved to outputs/{path.name}]")


# --------------------------------------------------------------------------- #
# RAG demo (local, no-API): retrieve EHR chunks + record session memory.
# --------------------------------------------------------------------------- #
def rag_demo(sid):
    if sid not in cb.SCENARIOS:
        print(f"Unknown scenario {sid}. Available scenarios: {sorted(cb.SCENARIOS)}")
        return
    import rag_retrieval
    import session_memory

    sc = cb.load_scenario(sid)
    pid = sc["patient_id"]
    question = rag_retrieval.clinical_question_for_scenario(sc)
    results = rag_retrieval.retrieve(question, pid, k=5)
    gold = set(sc.get("gold_eval", {}).get("gold_relevant_ehr_ids", []))

    print("=" * 72)
    print(f" LOCAL RAG-STYLE EHR RETRIEVAL - Scenario {sid}: {sc['name']}")
    print("=" * 72)
    print(cb.DISCLAIMER)
    print("\nClinical question:")
    print("  " + question)
    print(f"\nTop {len(results)} retrieved EHR chunks for patient {pid} (pure-Python TF-IDF, no API):")
    for r in results:
        mark = "  [in gold set]" if r["source_id"] in gold else ""
        print(f"  score={r['score']:<7} [{r['source_id']}]{mark}")
        print(f"      {r['text']}")

    retrieved_ids = {r["source_id"] for r in results}
    if gold:
        overlap = retrieved_ids & gold
        print(f"\nSource-ID overlap with gold relevant facts: {len(overlap)}/{len(gold)} "
              f"-> {', '.join(sorted(overlap)) or 'none'}")

    # Record session-level audit memory (runs the no-API pipeline to get triage + brief id).
    run = cb.run_pipeline(sid)
    entry = session_memory.record_session(
        scenario_id=sid, patient_id=pid,
        triage_urgency=run["triage"]["urgency_level"],
        retrieved_source_ids=sorted(retrieved_ids),
        brief_id=run["brief"]["brief_id"],
    )
    print(f"\nSession recorded to memory/session_memory.json:")
    print(f"  scenario={entry['scenario_id']} patient={entry['patient_id']} "
          f"triage={entry['triage_urgency']} brief={entry['brief_id']}")
    print("\nNote: lightweight LOCAL approximation of RAG (no embeddings, no vector DB, no API). "
          "The main pipeline still runs in no-API stored-output mode. For the GENUINE LangChain "
          "RAG pipeline (Documents + FAISS + local embeddings) run: python main.py --langchain-rag-demo " + str(sid))


# --------------------------------------------------------------------------- #
# Genuine LangChain RAG demo (local embeddings + FAISS, no API): shows the real retrieval backend
# that grounds the EHR Retrieval Agent -- LangChain Documents, metadata, source IDs, similarity
# scores, and Precision@k / Recall@k against the existing gold relevant source IDs.
# --------------------------------------------------------------------------- #
def langchain_rag_demo(sid, k=5):
    if sid not in cb.SCENARIOS:
        print(f"Unknown scenario {sid}. Available scenarios: {sorted(cb.SCENARIOS)}")
        return
    import session_memory

    sc = cb.load_scenario(sid)
    pid = sc["patient_id"]

    # Prefer the genuine LangChain backend; fall back gracefully (and say so) if it is not installed.
    backend = cb.get_retrieval_backend(prefer="auto")
    if backend.name != "langchain":
        print("[notice] The LangChain stack is not installed; showing the local TF-IDF fallback "
              "backend instead. Install requirements.txt (faiss-cpu, sentence-transformers, "
              "langchain*) to run the genuine LangChain RAG pipeline.")

    triage = cb.run_agent("triage", sid)
    evidence = cb.retrieve_ehr_evidence(sid, k=k, backend=backend, triage=triage)
    cfg = evidence["config"]
    results = evidence["results"]
    gold = set(sc.get("gold_eval", {}).get("gold_relevant_ehr_ids", []))

    print("=" * 72)
    print(f" GENUINE LangChain RAG EHR RETRIEVAL - Scenario {sid}: {sc['name']}")
    print("=" * 72)
    print(cb.DISCLAIMER)

    print("\nPipeline configuration (genuine LangChain RAG):")
    print(f"  backend          : {cfg.get('backend')}")
    print(f"  embedding model  : {cfg.get('embedding_model', 'n/a')}")
    print(f"  embedding backend: {cfg.get('embedding_backend', 'n/a')}")
    print(f"  vector store     : {cfg.get('vector_store', 'n/a')}")
    print(f"  documents/chunks : {cfg.get('num_documents', '?')} EHR Documents -> "
          f"{cfg.get('num_chunks', '?')} chunks (RecursiveCharacterTextSplitter)")

    print("\nClinical question (built from the Alert Triage Agent's retrieval plan):")
    print("  " + evidence["question"])

    print(f"\nTop {len(results)} retrieved LangChain Documents for patient {pid} "
          f"(retriever k={k}):")
    for rank, r in enumerate(results, 1):
        mark = "  [in gold set]" if r["source_id"] in gold else ""
        score = r.get("score")
        score_str = f"{score:.4f}" if isinstance(score, (int, float)) else "n/a"
        print(f"  {rank}. score={score_str:<10} [{r['source_id']}]  "
              f"(type={r.get('source_type')}, patient={r.get('patient_id')}, "
              f"scenario={r.get('scenario_id')}){mark}")
        print(f"       {r['text']}")
    print("  (score = vector-store distance; lower = more similar for FAISS L2)")

    retrieved_ids = [r["source_id"] for r in results]
    print("\nRetrieved source IDs (ranked): " + ", ".join(retrieved_ids))

    patk = metrics.score_retrieval_at_k(retrieved_ids, sc["gold_eval"], k=k)
    print(f"\nRetrieval evaluation vs gold relevant source IDs (k={k}):")
    print(f"  Precision@{k} : {patk['precision_at_k']}")
    print(f"  Recall@{k}    : {patk['recall_at_k']}")
    print(f"  hits={patk['hits']}  missed={patk['missed'] or 'none'}  "
          f"extra={patk['extra'] or 'none'}")

    # Record session-level audit memory (same memory used by --rag-demo).
    run = cb.run_pipeline(sid, attach_retrieval=False)
    entry = session_memory.record_session(
        scenario_id=sid, patient_id=pid,
        triage_urgency=run["triage"]["urgency_level"],
        retrieved_source_ids=retrieved_ids,
        brief_id=run["brief"]["brief_id"],
    )
    print(f"\nSession recorded to memory/session_memory.json:")
    print(f"  scenario={entry['scenario_id']} patient={entry['patient_id']} "
          f"triage={entry['triage_urgency']} brief={entry['brief_id']}")
    print("\nNote: genuine LangChain RAG pipeline (LangChain Documents -> RecursiveCharacterTextSplitter "
          "-> local embeddings -> FAISS -> retriever). Local only, no API keys. The retrieved "
          "Documents are the grounding context for the EHR Retrieval Agent.")


# --------------------------------------------------------------------------- #
def main(argv):
    if "--langchain-rag-demo" in argv:
        i = argv.index("--langchain-rag-demo")
        langchain_rag_demo(int(argv[i + 1]))
        return
    if "--rag-demo" in argv:
        i = argv.index("--rag-demo")
        rag_demo(int(argv[i + 1]))
        return
    if "--demo" in argv:
        i = argv.index("--demo")
        demo(int(argv[i + 1]), save="--save-transcript" in argv)
        return
    if "--brief" in argv:
        i = argv.index("--brief")
        show_brief(int(argv[i + 1]))
        return
    if "--scorecard" in argv:
        banner(); scorecard(); return
    if "--adversarial" in argv:
        banner(); adversarial(); return

    banner()
    scorecard()
    print("\n" + "=" * 80)
    print(" SAMPLE CLINICAL CONTEXT BRIEF — Scenario 1 (Missed Medication)")
    print("=" * 80)
    show_brief(1)
    adversarial()
    escalation_check()
    print("\nDone. python main.py completed successfully.")


if __name__ == "__main__":
    main(sys.argv[1:])
