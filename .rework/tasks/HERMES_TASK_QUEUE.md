# Hermes Task Queue — datp-cp

Tasks that Hermes performs directly (audits, monitoring, coordination, log updates).

---

## TODO

### HERMES-TASK-001 — Bootstrap session and verify tool availability
Owner: Hermes
Type: coordination
Severity: CRITICAL
Instructions:
  1. Go to /home/naslouby/Projects/datp-calibration-poisoning.
  2. Read HERMES_MASTER_ORCHESTRATION.md and all supporting prompt files.
  3. Run tool availability check (command -v claude, codex, openclaw, graphify, etc.).
  4. Record available tools in .rework/logs/HERMES_LOG.md.
  5. Read STATUS.md and all task queues.
  6. Determine the next action based on last recorded state.
Status: TODO

### HERMES-TASK-002 — Initial obsolete terminology search
Owner: Hermes
Type: audit
Severity: HIGH
Instructions:
  1. Run obsolete terminology search from HERMES_AUDIT_LOOP.md section 2.
  2. Classify all hits (ACTIVE_ISSUE / STALE_ARTIFACT / HISTORICAL_NOTE / FALSE_POSITIVE).
  3. Write ACTIVE_ISSUE findings to .rework/SCIENTIFIC_DRIFT_AUDIT.md.
  4. Create Claude tasks for all ACTIVE_ISSUE hits.
  5. Update .rework/logs/HERMES_LOG.md.
Status: TODO

### HERMES-TASK-003 — Verify pre-execution checklist before running commands
Owner: Hermes
Type: verification
Severity: CRITICAL
Instructions:
  1. Run: python -m ruff check src/ tests/
  2. Run: python -m pyright
  3. Run: python -m pytest tests/unit/ tests/integration/
  4. Verify no CRITICAL code-quality or scientific-drift findings outstanding.
  5. Verify Makefile has only canonical public targets.
  6. If any check fails, dispatch Claude to fix before proceeding.
  7. Record results in .rework/logs/HERMES_LOG.md.
Status: TODO

### HERMES-TASK-004 — Delete outputs folder and run execution sequence
Owner: Hermes
Type: execution
Severity: CRITICAL
Dependencies: HERMES-TASK-003 must be DONE first
Instructions:
  1. Verify outputs/ exists at the correct path.
  2. Delete /home/naslouby/Projects/datp-calibration-poisoning/outputs only.
  3. Record deletion in .rework/logs/HERMES_LOG.md.
  4. Run the canonical execution sequence from OUTPUT_EXECUTION_PROTOCOL.md section 3.
  5. Monitor and handle failures per section 5 of that protocol.
  6. Verify artifacts per section 6 of that protocol.
Status: TODO

### HERMES-TASK-005 — Produce final report
Owner: Hermes
Type: reporting
Severity: HIGH
Dependencies: all implementation tasks DONE, execution sequence DONE, paper loop DONE
Instructions:
  1. Write .rework/FINAL_REPORT.md following the template in HERMES_MASTER_ORCHESTRATION.md.
  2. Include what Claude, Codex, OpenClaw, and Hermes each did.
  3. List all files changed.
  4. State execution results.
  5. State paper readiness.
  6. Document all remaining risks.
Status: TODO

---

## IN_PROGRESS

---

## DONE

---

## BLOCKED
