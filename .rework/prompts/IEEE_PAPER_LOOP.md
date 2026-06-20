# IEEE Paper Loop -- datp-cp

This protocol governs how Hermes, Claude, Codex, and OpenClaw create and audit the IEEE paper from actual datp-cp outputs.

Claude and Codex have equal paper-authoring authority. Either may draft or revise the paper when assigned.

OpenClaw reviews only.

No invented results. No unsupported claims. No commits. No PRs.

---

## 1. PRECONDITIONS

Do not start the paper loop until:

    make datp-cp-run has completed successfully
    make datp-cp-report has completed successfully
    all expected artifacts are verified (see OUTPUT_EXECUTION_PROTOCOL.md section 6)
    no CRITICAL outstanding findings remain from the code audit loop

---

## 2. READ IEEE INSTRUCTIONS FIRST

All agents must read the IEEE folder before writing or reviewing the paper:

    /home/naslouby/Projects/datp-calibration-poisoning/IEEE/

Read all files in IEEE/ including:

    conference-latex-template/ and subdirectories
    IEEEtranBST2/ for citation style

Follow IEEE conference paper formatting exactly.

---

## 3. PAPER CONTENT REQUIREMENTS

The paper must include all of the following that are supported by actual outputs:

    Title and abstract aligned with datp-cp scope
    Calibration-channel threat model
    N-BaIoT main experiment description
    Threshold policy comparison: GLOBAL_THRESHOLD vs LOCAL_THRESHOLD vs CLUSTER_THRESHOLD
    THRESHOLD_RAISE and THRESHOLD_LOWER attack narrative
    Metrics and statistical plan consistent with the roadmap
    Result tables or figures from actual output files
    CV(FPR) reported with coverage ratio
    AUROC invariance result
    Calibration-Pending client handling
    Limitations section
    Threats to validity
    Reproducibility details (seeds, dataset, code reference)
    Artifact provenance

Forbidden content:

    invented results
    claims stronger than outputs support
    model/training/aggregation/evasion/privacy/deployment claims
    Edge-IIoTset references
    journal-extension scope claims
    obsolete terminology (CP2, Regime A/B/C, B1/B2/B3/B4)

---

## 4. PAPER AUTHORING (CLAUDE OR CODEX)

Hermes assigns paper drafting to Claude or Codex based on availability.

Both agents have the same authority to draft, revise, and finalize the paper.

The authoring agent must:

    Read the IEEE instructions from IEEE/.
    Read all verified output files.
    Draft each section grounded in actual outputs.
    Use only canonical terminology.
    Write reviewer-risk-aware wording (no overclaiming).
    Record paper decisions in .rework/DECISIONS.md.
    Flag any ambiguous or potentially unsupportable result before writing it.

---

## 5. PAPER AUDIT LOOP

Repeat until no CRITICAL or HIGH paper issues remain.

    Step 1.  Claude or Codex drafts or updates the paper.
    Step 2.  The other implementation agent reviews.
    Step 3.  Hermes audits as a harsh reviewer.
    Step 4.  OpenClaw audits as a review-only harsh reviewer.
    Step 5.  All findings become paper tasks in CLAUDE_TASK_QUEUE.md or CODEX_TASK_QUEUE.md.
    Step 6.  Claude or Codex fixes CRITICAL and HIGH issues.
    Step 7.  The other implementer rechecks the fixed sections.
    Step 8.  OpenClaw rechecks.
    Step 9.  Hermes rechecks.
    Step 10. Repeat until all CRITICAL and HIGH issues are resolved.

Do not declare the paper done until all reviewers agree or all remaining risks are documented.

---

## 6. PAPER AUDIT CHECKLIST

Each reviewer checks all of the following:

Scientific accuracy:

    All claims traceable to actual outputs
    No claim stronger than results support
    Threat model limited to calibration-channel poisoning
    AUROC invariance correctly stated
    CV(FPR) correctly defined (sigma/mu, no epsilon)
    Coverage ratio reported alongside CV(FPR)
    Calibration-Pending clients correctly described
    Seed scheme correctly described (SeedSequence)
    Paired comparisons correctly described
    Statistical plan correct (5 seed aggregates, bootstrap CI on aggregates)
    No 45-independent-samples language

Claim discipline:

    No model/training/aggregation/evasion/privacy/deployment claims
    No broad FL robustness claims
    Supportive evidence not presented as primary evidence

Terminology consistency:

    Only canonical policy names (GLOBAL_THRESHOLD, LOCAL_THRESHOLD, CLUSTER_THRESHOLD)
    No B1/B2/B3/B4 visible to readers
    No Regime A/B/C/D visible to readers
    No CP2, MVP, or Phase E visible to readers
    Consistent naming throughout

Result tables and figures:

    All numbers sourced from actual outputs
    No hardcoded results
    Tables formatted correctly for IEEE
    Captions accurate and non-overclaiming

Structure and format:

    IEEE conference paper structure
    Abstract matches introduction and conclusion
    Related work correctly positions datp-cp
    Contributions clearly stated and supported
    Limitations section present
    Threats to validity present
    Reproducibility details present
    References in IEEEtran style

---

## 7. PAPER TASK FORMAT

    ### PAPER-TASK-NNN -- <title>
    Owner: Claude / Codex
    Type: paper
    Severity: CRITICAL / HIGH / MEDIUM / LOW
    Section: <paper section>
    Finding: <finding ID from reviewer>
    Instruction: <what must change>
    Acceptance: <how to verify>
    Status: TODO

---

## 8. FINAL PAPER SIGN-OFF

Paper is ready when:

    Hermes audit: no CRITICAL or HIGH issues
    Codex audit: no CRITICAL or HIGH issues
    Claude audit: no CRITICAL or HIGH issues
    OpenClaw audit: no CRITICAL or HIGH issues (or all remaining risks documented)
    All claim-to-output traces verified
    Limitations and threats to validity complete
    IEEE formatting verified
    Paper files in a designated directory
    All remaining risks documented in .rework/FINAL_REPORT.md under paper-readiness verdict
