# datp-cp Workflow Status

## Run identity
- Branch: main
- Start time: 2026-06-27T19:59:00Z
- Last update: 2026-06-27T20:00:00Z
- Current commit: f9faf94
- Current phase: Step 00 — Preflight complete
- Fresh run or resume: FRESH RUN (STATUS.md did not exist)
- Resume point: N/A
- Roadmap files consulted: docs/DATP_CP_Roadmap.md

## Scientific lock
- Calibration-channel only: YES — attack modifies only benign threshold-calibration scores
- N-BaIoT physical-device clients: YES — K=9, physical devices as clients
- Policies: GLOBAL_THRESHOLD, LOCAL_THRESHOLD, CLUSTER_THRESHOLD
- q: 95 (locked)
- Training/model/test unchanged: YES — non-negotiable isolation rules confirmed
- Journal-scope contamination check: No Edge-IIoTset, no journal-extension assets
- Roadmap consistency check: PASS — roadmap read, protocol understood

## Git discipline
- Single-commit workflow: YES — amend-only rule active
- Amend-only rule: YES
- Force-push-with-lease rule: YES
- AllCommandsPrompt.md staged: NO
- STATUS.md staged: NO
- Last amend commit: N/A (no fixes yet)
- Last pushed commit: N/A (no push yet)

## Command ledger

### Step 00 — Preflight git and roadmap read
- Status: PASSED
- Before status: FRESH RUN, no STATUS.md
- Command: pwd && git status --short && git branch --show-current && git log -1 --oneline; then read docs/DATP_CP_Roadmap.md
- Why this command is being run: Confirm repo root, working tree state, branch, commit; read active scientific protocol
- Expected result: Repo root confirmed, single commit, main branch, roadmap read
- Start time: 2026-06-27T19:59:30Z
- End time: 2026-06-27T20:00:00Z
- Duration: ~30s
- Exit code: 0
- Output summary: pwd=/home/naslouby/Projects/datp-calibration-poisoning; untracked: AllCommandsPrompt.md; branch=main; commit=f9faf94 "DATP Calibration-Channel Poisoning Project"; roadmap fully read
- Files changed: STATUS.md created (local-only)
- Fix summary: N/A
- Validation summary: Repo root confirmed, single commit confirmed, AllCommandsPrompt.md untracked (not staged), roadmap read
- Commit/push: None
- Next action: Step 01 — make check

### Step 01 — make check
- Status: PASSED
- Before status: Step 00 complete, fresh run
- Command: make check
- Why this command is being run: Verify ruff + pyright pass before experiment execution
- Expected result: 0 errors
- Start time: 2026-06-27T20:01:00Z
- End time: 2026-06-27T20:02:00Z
- Duration: 8s (rerun after fix)
- Exit code: 0
- Output summary: ruff "All checks passed!"; pyright "0 errors, 0 warnings, 0 informations"
- Files changed: none (pyright installed via pip — already listed in pyproject.toml optional test deps, just missing from venv)
- Fix summary: pyright not installed in venv → ran .venv/bin/pip install pyright; no code changes
- Validation summary: make check exit 0 confirmed
- Commit/push: none (no code files changed)
- Next action: Step 02 — make datp-cp-unit-tests

### Step 02 — make datp-cp-unit-tests
- Status: PASSED
- Before status: Step 01 PASSED
- Command: make datp-cp-unit-tests
- Why this command is being run: Run unit tests to verify implementation correctness
- Expected result: All unit tests pass
- Start time: 2026-06-27T20:03:00Z
- End time: 2026-06-27T20:08:35Z
- Duration: 335s (5m35s)
- Exit code: 0
- Output summary: 1509 passed in 335.80s
- Files changed: none
- Fix summary: N/A
- Validation summary: All 1509 unit tests passed
- Commit/push: none
- Next action: Step 03 — output cleanup

### Step 03 — output cleanup
- Status: PASSED
- Before status: Step 02 PASSED, fresh run confirmed
- Command: pwd; test -f Makefile; test -d .git; rm -rf outputs; test ! -e outputs && echo "outputs removed"
- Why this command is being run: Fresh run — delete outputs/ before experiment execution
- Expected result: outputs removed
- Start time: 2026-06-27T20:09:00Z
- End time: 2026-06-27T20:09:05Z
- Duration: <1s
- Exit code: 0
- Output summary: "outputs removed" confirmed
- Files changed: outputs/ directory deleted
- Fix summary: N/A
- Validation summary: test ! -e outputs passed
- Commit/push: none (STATUS.md not staged)
- Next action: Step 04 — make datp-cp-clean

### Step 04 — make datp-cp-clean
- Status: PASSED
- Before status: Step 03 PASSED, outputs/ deleted
- Command: make datp-cp-clean
- Why this command is being run: Generate clean N-BaIoT artifacts (scores, thresholds, manifests) under E=1 FedAvg q=95 locked protocol
- Expected result: Clean artifacts in outputs/conference_calibration_poisoning/; exit 0
- Start time: 2026-06-27T20:10:00Z
- End time: 2026-06-27T21:13:36Z
- Duration: 3816s (63m36s)
- Exit code: 0
- Output summary: Total=30, Completed=30, Skipped=0, Failed=0, Duration=3962.9s; 10 seeds × 3 policies = 30 cells all passing
- Files changed: outputs/ populated with checkpoints, logs, results, scores
- Fix summary: N/A
- Validation summary: Exit 0, all 30 cells completed, 0 failures
- Commit/push: none (no code changes)
- Next action: Step 05 — make datp-cp-smoke

### Step 05 — make datp-cp-smoke
- Status: PASSED
- Before status: Step 04 PASSED (30/30 clean cells)
- Command: make datp-cp-smoke
- Why this command is being run: Validate all protocol invariants (AUROC, mutation, direction, determinism, leakage etc.) on synthetic data before main run
- Expected result: All smoke tests pass
- Start time: 2026-06-27T21:14:00Z
- End time: 2026-06-27T21:14:11Z
- Duration: 11s
- Exit code: 0
- Output summary: 19 passed in 8.85s — all invariants passed including: f0 zero delta, no in-place mutation, HIGH raises/LOW lowers, determinism, cluster decomposition, 2-layer bootstrap, manifest round-trip, AUROC invariance, CV(FPR) zero handling, global<local shift, K=3 fixed, output isolation, FPR dispersion lowering
- Files changed: none
- Fix summary: N/A
- Validation summary: All 19 smoke invariants passed — main run gates cleared
- Commit/push: none
- Next action: Step 06 — make datp-cp-dry-run

### Step 06 — make datp-cp-dry-run
- Status: PASSED
- Before status: Step 05 PASSED (19/19 smoke invariants)
- Command: make datp-cp-dry-run
- Why this command is being run: Enumerate and validate the full N-BaIoT main run plan without executing
- Expected result: Plan matches authorized matrix; exit 0
- Start time: 2026-06-27T21:15:00Z
- End time: 2026-06-27T21:15:03Z
- Duration: 3s
- Exit code: 0
- Output summary: dataset=nbaiot; policies=[GLOBAL,LOCAL,CLUSTER]; sources=[RANDOM,HIGH_SCORE,LOW_SCORE]; objectives=[RAISE,LOWER]; fractions=[0,0.1,0.2,0.4]; seeds=10 triplets; cells/victim=480; valid source-objective pairs=RANDOM+RAISE, RANDOM+LOWER, HIGH_SCORE+RAISE, LOW_SCORE+LOWER — all correct per roadmap
- Files changed: none
- Fix summary: N/A
- Validation summary: Plan fully matches authorized matrix; no stale labels; no invalid combos; allow_run=True
- Commit/push: none
- Next action: Step 07 — make datp-cp-run

### Step 07 — make datp-cp-run
- Status: PASSED
- Before status: Step 06 PASSED (plan validated)
- Command: make datp-cp-run
- Why this command is being run: Execute the authorized N-BaIoT main calibration-poisoning matrix
- Expected result: All cells complete or infeasible; exit 0
- Start time: 2026-06-27T21:16:00Z
- End time: 2026-06-27T21:27:41Z
- Duration: 701s (11m41s)
- Exit code: 0
- Output summary: 4320 result rows; 0 infeasible; AUROC invariant=True throughout; f=0 gives delta_tau=0 (baseline correct); f=0.4 HIGH_SCORE_BENIGN gives positive delta_tau (e.g. 0.171 for GLOBAL/Danmini); manifest written to outputs/conference_calibration_poisoning/nbaiot_main_manifest.json
- Files changed: outputs/conference_calibration_poisoning/nbaiot_main_manifest.json and result artifacts
- Fix summary: N/A
- Validation summary: 4320/4320 cells completed; all AUROC invariant; signed correctly for f>0 directional attacks
- Commit/push: none
- Next action: Step 08 — make audit-results

### Step 08 — make audit-results
- Status: PASSED
- Before status: Step 07 PASSED (4320/4320 cells)
- Command: make audit-results
- Why this command is being run: Audit provenance, leakage, schema, scientific contract on all results
- Expected result: All audit gates pass; exit 0
- Start time: 2026-06-27T21:29:00Z
- End time: 2026-06-27T21:29:38Z
- Duration: 38s
- Exit code: 0
- Output summary: 30 controlled-policy invariant PASS cells (10 seeds × 3 policies); 0 FAIL; 29 warning records — all informational or observational: GLOBAL_NOT_POOLED_PERCENTILE (correct per roadmap — tau_global is mean of local q95s), LOCAL_UTILITY_TRADEOFF (observational), WORST_CLIENT_ stability/variation (observational), FIXED_OPERATING_POINT_METRICS_PENDING (non-blocking informational); 17 audit artifacts written to artifacts/audit/
- Files changed: artifacts/audit/ directory created with 17 CSVs/JSONs/MDs
- Fix summary: N/A — no failures
- Validation summary: Exit 0, all audit gates pass; warnings are informational/observational only, no protocol violations detected
- Commit/push: none
- Next action: Step 09 — make status

### Step 09 — make status
- Status: PASSED
- Before status: Step 08 PASSED (audit passed, 0 FAIL)
- Command: make status
- Why this command is being run: Report complete/missing/aborted/infeasible cell counts
- Expected result: All complete, 0 missing/aborted; exit 0
- Start time: 2026-06-27T21:30:00Z
- End time: 2026-06-27T21:30:03Z
- Duration: 3s
- Exit code: 0
- Output summary: Stage NBAIOT_MAIN: Complete=30, Missing=0, Aborted=0, Total=30; Overall: 30/30 complete
- Files changed: none
- Fix summary: N/A
- Validation summary: All 30 cells complete, 0 missing, 0 aborted, 0 infeasible
- Commit/push: none
- Next action: Step 10 — make datp-cp-report

### Step 10 — make datp-cp-report
- Status: PASSED (after fix)
- Before status: Step 09 PASSED (30/30 complete, 0 missing)
- Command: make datp-cp-report
- Why this command is being run: Generate final tables, figures, and claim-gate summary from completed results
- Expected result: Report artifacts written; exit 0
- Start time: 2026-06-27T21:31:00Z (first attempt); 2026-06-27T21:50:00Z (rerun)
- End time: 2026-06-27T21:52:25Z
- Duration: 4s (rerun)
- Exit code: 0
- Output summary: Wrote outputs/analysis/metrics_schema_validation.json, bootstrap_cis.json/.csv, figures/figure_1-3 (data+png+pdf), tables/table3_nbaiot.tex/.csv, analysis/reporting_audit.json
- Files changed: src/datp/artifacts/io.py (added OPT_NON_STR_KEYS); outputs/analysis/, figures/, tables/ populated
- Fix summary: orjson 3.11.9 does not accept StrEnum dict keys without OPT_NON_STR_KEYS; added that flag to write_json_atomic in io.py — serializes via str() which correctly returns the value for StrEnum; no scientific impact
- Validation summary: 591 targeted unit tests pass after fix; rerun exit 0
- Commit/push: amended 5f36c3e; pushed --force-with-lease to main
- Next action: Step 11 — final make status

## Failures and fixes
### Failure entry 1
- Failed command: make datp-cp-report
- Elapsed time before failure: 1s
- Exit code: 2
- Key error: TypeError: Dict key must be str (AuditField StrEnum keys in reporting_audit dict passed to orjson)
- Root cause: orjson 3.11.9 does not accept StrEnum subclass instances as dict keys without OPT_NON_STR_KEYS
- Roadmap/protocol check: Pure serialization fix; no scientific constants or protocol semantics affected
- Files inspected: src/datp/artifacts/io.py, src/datp/reporting/build.py, src/datp/core/enums.py
- Fix: Added orjson.OPT_NON_STR_KEYS to write_json_atomic option flags in io.py (1 line)
- Targeted validation: 591 unit tests (io/json/write filter) — all passed
- Rerun result: PASS — exit 0, all report artifacts written
- Commit: 5f36c3e (amended)
- Push: pushed --force-with-lease to main

### Step 11 — final make status
- Status: PASSED
- Before status: Step 10 PASSED (report artifacts written, amended commit pushed)
- Command: make status
- Why this command is being run: Final workflow state verification
- Expected result: 30/30 complete, 0 missing, 0 aborted
- Start time: 2026-06-27T21:53:00Z
- End time: 2026-06-27T21:53:03Z
- Duration: 3s
- Exit code: 0
- Output summary: Stage NBAIOT_MAIN — Complete=30, Missing=0, Aborted=0, Total=30; Overall 30/30
- Files changed: none
- Fix summary: N/A
- Validation summary: Final state confirmed — all 30 cells complete
- Commit/push: none (fix already committed at 5f36c3e)
- Next action: WORKFLOW COMPLETE

## Long-running command monitor
- Active command: none (datp-cp-clean complete)
- Start time: 2026-06-27T20:10:00Z
- Last heartbeat: 2026-06-27T21:08:00Z
- Elapsed: ~58min
- Latest observed log/artifact signal: Group [10/10] seed=9 at ROUND 4/150 (21:05:47Z)
- Current outputs/status summary: Seeds 0-8 complete; seed 9 just started
- Health assessment: HEALTHY — 9/10 seeds done, ~6 min/seed, ETA ~10-15 more min
- Next heartbeat due: 2026-06-27T21:28:00Z (or command finishes first)

## Failures and fixes
### Failure entry 1 — make datp-cp-report (first attempt)
- Failed command: make datp-cp-report
- Elapsed time before failure: 1s
- Exit code: 2
- Key error: TypeError: Dict key must be str (AuditField StrEnum keys passed to orjson)
- Root cause: orjson 3.11.9 does not accept StrEnum subclass instances as dict keys without OPT_NON_STR_KEYS
- Roadmap/protocol check: Pure serialization fix; no scientific constants or protocol semantics affected
- Files inspected: src/datp/artifacts/io.py, src/datp/reporting/build.py, src/datp/core/enums.py
- Fix: Added orjson.OPT_NON_STR_KEYS to write_json_atomic option flags in io.py (1 line)
- Targeted validation: 591 unit tests — all passed
- Rerun result: PASS — exit 0, duration 4s, all report artifacts written
- Commit: 5f36c3e (amended)
- Push: pushed --force-with-lease to main

## Final summary
- Completed commands: Steps 00–11 (all 12 steps passed)
- Failed commands: Step 10 first attempt — fixed narrowly (1-line io.py change); rerun passed
- Skipped with validation: none
- Infeasible cells: 0
- Missing cells: 0
- Aborted cells: 0
- Report artifacts: outputs/analysis/metrics_schema_validation.json, bootstrap_cis.json/.csv; outputs/figures/figure_1-3 (data.json, .png, .pdf); outputs/tables/table3_nbaiot.tex/.csv; outputs/analysis/reporting_audit.json; artifacts/audit/ (17 files)
- Remaining risks: FIXED_OPERATING_POINT_METRICS_PENDING (non-blocking informational); LOCAL_UTILITY_TRADEOFF seeds 2-7 (observational); WORST_CLIENT rotation (observational)
- Final commit: 5f36c3e (single amended commit; branch remains one-commit)
- Final pushed branch: main
