# Output Execution Protocol — datp-cp

This protocol governs how Hermes runs the final command sequence, handles failures, and verifies artifacts.

No commits. No PRs.

---

## 1. PRE-EXECUTION CHECKLIST

Before running any make command, verify all of these:

    ruff passes:       python -m ruff check src/ tests/
    pyright passes:    python -m pyright
    tests pass:        python -m pytest tests/unit/ tests/integration/
    no CRITICAL code-quality findings outstanding
    no CRITICAL scientific-drift findings outstanding
    Makefile has only canonical public targets
    make help lists only canonical targets
    make check is functional

Do not run experiments if any of the above fail. Fix first.

---

## 2. OUTPUTS FOLDER CLEANUP

Before running the final command sequence, check whether the outputs folder exists:

    ls -la /home/naslouby/Projects/datp-calibration-poisoning/outputs || echo "no outputs folder"

If it exists, verify it is EXACTLY this path:

    /home/naslouby/Projects/datp-calibration-poisoning/outputs

Then delete only that folder:

    rm -rf /home/naslouby/Projects/datp-calibration-poisoning/outputs

Record the deletion in .rework/logs/HERMES_LOG.md:

    ## Outputs Deletion — <timestamp>
    Path deleted: /home/naslouby/Projects/datp-calibration-poisoning/outputs
    Reason: pre-execution clean state
    Verified safe: yes (no raw data, no shared data, no IEEE files, no source code in this path)

NEVER delete:

    data/ (raw and processed datasets)
    IEEE/ (paper templates and instructions)
    .rework/ (orchestration files)
    src/ (source code)
    tests/ (test files)
    docs/ (roadmap and tickets)
    any other folder

---

## 3. CANONICAL EXECUTION SEQUENCE

Run commands in this exact order:

    Step 1.  make help
    Step 2.  make check
    Step 3.  make datp-cp-smoke
    Step 4.  make datp-cp-dry-run
    Step 5.  make datp-cp-clean
    Step 6.  make datp-cp-run
    Step 7.  make datp-cp-report

Wait for each command to complete before running the next.

Do not skip steps.

Do not reorder steps.

---

## 4. COMMAND MONITORING

For each command:

    capture full output
    record start time
    record end time
    record exit code
    classify: SUCCESS / FAILURE / PARTIAL

For long-running commands (datp-cp-clean, datp-cp-run):

    monitor for error output during execution
    detect if the process hangs
    detect if GPU/CPU resources are exhausted

---

## 5. FAILURE HANDLING

If any command fails:

Step 1. Capture the full error output.

Step 2. Classify the failure:

    IMPLEMENTATION_ERROR  — code bug; fix in src/
    CONFIG_ERROR          — wrong config value; fix in config
    DATA_ERROR            — missing or malformed dataset; investigate data/
    ENVIRONMENT_ERROR     — missing dependency or wrong version; fix environment
    RESOURCE_ERROR        — out of memory or disk; adjust resource config
    TEST_ERROR            — test assertion failure; investigate test logic

Step 3. Dispatch the fix:

    IMPLEMENTATION_ERROR  -> assign to Claude (create CLAUDE task)
    CONFIG_ERROR          -> assign to Claude (create CLAUDE task)
    DATA_ERROR            -> investigate with Hermes; create HERMES task
    ENVIRONMENT_ERROR     -> investigate with Hermes; create HERMES task
    RESOURCE_ERROR        -> investigate with Hermes; create HERMES task
    TEST_ERROR            -> assign to Claude (create CLAUDE task)

Step 4. Ask OpenClaw to review the failure cause if the classification is ambiguous.

Step 5. Rerun the failed command after the fix.

Step 6. If the same failure recurs, escalate: create a BLOCKED task with exact evidence.

Step 7. Continue subsequent steps only after the failed command passes.

---

## 6. ARTIFACT VERIFICATION

After make datp-cp-run completes:

Verify the following for each expected experiment cell:

    output folder exists at the expected path under outputs/
    manifest.json exists and is non-empty
    metrics.json exists and is non-empty
    metrics.json.tmp does NOT exist (incomplete run)
    DONE.txt exists (or canonical completion marker)
    IN_PROGRESS file does NOT exist
    ABORTED.txt does NOT exist

If metrics.json.tmp exists without metrics.json, the run did not complete.

If DONE.txt is missing, the run did not complete.

Do not treat partial artifacts as successful outputs.

Report incomplete cells to Hermes and create a task to rerun them.

---

## 7. REPORT VERIFICATION

After make datp-cp-report:

Verify:

    report output files exist
    report references actual output metrics (not hardcoded values)
    all three threshold policies appear in the report
    N-BaIoT main results appear in the report
    no unsupported claims in the report text
    no obsolete terminology in the report

---

## 8. EXECUTION LOG

Record all execution events in .rework/logs/HERMES_LOG.md:

    ## Execution Event — <timestamp>
    Command: <make target>
    Exit code: <code>
    Duration: <approx time>
    Outcome: SUCCESS / FAILURE / PARTIAL
    Artifacts verified: <yes / no / partial>
    Failures dispatched: <task IDs or none>
    Notes: <any relevant observation>
