# AllCommandsPrompt.md

You are working in:

```bash
/home/naslouby/Projects/datp-calibration-poisoning
```

Your job is to execute the canonical `datp-cp` workflow from start to finish, command by command, while monitoring, fixing failures, updating `STATUS.md`, amending the existing commit, force-pushing with lease, and reporting progress to me.

You must behave like a careful research-engineering agent, not like a one-shot command runner.

Do not rush. Do not batch the main workflow commands. Do not silently skip steps. Do not change the scientific protocol to make commands pass.

## 0. Absolute source of truth

Before doing anything, read the active roadmap/protocol files in the repository.

The roadmap is the scientific source of truth for every decision. When unsure, refer back to the roadmap before editing code, changing tests, interpreting outputs, skipping a step, rerunning a step, or reporting results.

Preserve the `datp-cp` scientific contract exactly:

1. This is calibration-channel poisoning only.
2. The attack may modify only benign threshold-calibration data.
3. Training data must remain unchanged.
4. Training labels must remain unchanged.
5. Model weights must remain unchanged during poisoned comparisons.
6. Federated aggregation must remain unchanged.
7. Test scores must remain unchanged.
8. Test labels must remain unchanged.
9. Client eligibility logic must remain unchanged unless the roadmap explicitly requires a bug fix.
10. Threshold-policy definitions must remain unchanged unless the roadmap explicitly requires a bug fix.
11. Primary dataset is N-BaIoT using physical devices as clients.
12. Main policies are exactly:

    1. `GLOBAL_THRESHOLD`
    2. `LOCAL_THRESHOLD`
    3. `CLUSTER_THRESHOLD`
13. Threshold percentile is locked at `q = 95`.
14. Preserve paired clean-vs-poisoned semantics.
15. Preserve AUROC invariance as a sanity check, not as a contribution.
16. Do not introduce journal-extension scope.
17. Do not introduce Edge-IIoTset scope.
18. Do not introduce CICIoT stretch claims.
19. Do not introduce FedProx, Ditto, FedBN, FedRep, FedPer, or other model-personalization comparators.
20. Do not introduce training poisoning.
21. Do not introduce model poisoning.
22. Do not introduce aggregation poisoning.
23. Do not introduce Byzantine aggregation studies.
24. Do not introduce backdoor attacks.
25. Do not introduce evasion attacks.
26. Do not introduce privacy mechanisms.
27. Do not make privacy guarantee claims.
28. Do not make deployment-readiness claims.
29. Do not make raw-traffic realizability claims.
30. Do not tune anything against poisoned outcomes.

If a fix risks scientific drift, stop that fix, write the risk in `STATUS.md`, refer back to the roadmap, find a narrower implementation fix, and continue only if the protocol remains intact.

## 1. Mandatory idempotent run ledger: `STATUS.md`

Create and maintain a file at the repository root:

```bash
STATUS.md
```

This file is mandatory for idempotency and resume safety.

`STATUS.md` must remain local-only.

Do not commit `STATUS.md`.

Do not stage `STATUS.md`.

Do not include `STATUS.md` in any amend.

Do not include `STATUS.md` in any push.

Also do not commit, stage, amend, or push this file:

```bash
AllCommandsPrompt.md
```

Both files are operational local files only:

```text
AllCommandsPrompt.md
STATUS.md
```

When staging files, never use broad staging commands such as:

```bash
git add .
git add -A
git add --all
```

Instead, stage only the specific implementation, test, config, or documentation files required for the validated fix.

Before every amend, explicitly verify that `AllCommandsPrompt.md` and `STATUS.md` are not staged:

```bash
git status --short
git restore --staged AllCommandsPrompt.md STATUS.md 2>/dev/null || true
git status --short
```

If either `AllCommandsPrompt.md` or `STATUS.md` is tracked already, do not modify or commit it. Report this immediately and ask for manual cleanup guidance before continuing with any amend.

If `STATUS.md` already exists, read it before running any workflow command. Use it to determine the last safely completed step.

Before skipping any step on resume, validate that the expected artifacts or command result still exist. If validation is uncertain, rerun the smallest safe validation command.

Do not blindly restart from the beginning after a crash.

Do not delete `outputs` again on resume if `STATUS.md` shows that output cleanup already completed and later workflow steps started or completed.

`STATUS.md` must be updated:

1. before each command starts;
2. after each command finishes;
3. when a command fails;
4. before any fix;
5. after any fix;
6. before any rerun;
7. after any rerun;
8. before any amend or push;
9. after any amend or push;
10. every ~20 minutes during long-running commands.

Use this structure in `STATUS.md`:

```markdown
# datp-cp Workflow Status

## Run identity
- Branch:
- Start time:
- Last update:
- Current commit:
- Current phase:
- Fresh run or resume:
- Resume point:
- Roadmap files consulted:

## Scientific lock
- Calibration-channel only:
- N-BaIoT physical-device clients:
- Policies:
- q:
- Training/model/test unchanged:
- Journal-scope contamination check:
- Roadmap consistency check:

## Git discipline
- Single-commit workflow:
- Amend-only rule:
- Force-push-with-lease rule:
- AllCommandsPrompt.md staged:
- STATUS.md staged:
- Last amend commit:
- Last pushed commit:

## Command ledger

### Step 00 — Preflight git and roadmap read
- Status: NOT_STARTED | RUNNING | PASSED | FAILED | FIXING | SKIPPED_WITH_VALIDATION
- Before status:
- Command:
- Why this command is being run:
- Expected result:
- Start time:
- End time:
- Duration:
- Exit code:
- Output summary:
- Files changed:
- Fix summary:
- Validation summary:
- Commit/push:
- Next action:

### Step 01 — make check
- Status:
- Before status:
- Command:
- Why this command is being run:
- Expected result:
- Start time:
- End time:
- Duration:
- Exit code:
- Output summary:
- Files changed:
- Fix summary:
- Validation summary:
- Commit/push:
- Next action:

### Step 02 — make datp-cp-unit-tests
- Status:
- Before status:
- Command:
- Why this command is being run:
- Expected result:
- Start time:
- End time:
- Duration:
- Exit code:
- Output summary:
- Files changed:
- Fix summary:
- Validation summary:
- Commit/push:
- Next action:

### Step 03 — output cleanup
- Status:
- Before status:
- Command:
- Why this command is being run:
- Expected result:
- Start time:
- End time:
- Duration:
- Exit code:
- Output summary:
- Files changed:
- Fix summary:
- Validation summary:
- Commit/push:
- Next action:

### Step 04 — make datp-cp-clean
- Status:
- Before status:
- Command:
- Why this command is being run:
- Expected result:
- Start time:
- End time:
- Duration:
- Exit code:
- Output summary:
- Files changed:
- Fix summary:
- Validation summary:
- Commit/push:
- Next action:

### Step 05 — make datp-cp-smoke
- Status:
- Before status:
- Command:
- Why this command is being run:
- Expected result:
- Start time:
- End time:
- Duration:
- Exit code:
- Output summary:
- Files changed:
- Fix summary:
- Validation summary:
- Commit/push:
- Next action:

### Step 06 — make datp-cp-dry-run
- Status:
- Before status:
- Command:
- Why this command is being run:
- Expected result:
- Start time:
- End time:
- Duration:
- Exit code:
- Output summary:
- Files changed:
- Fix summary:
- Validation summary:
- Commit/push:
- Next action:

### Step 07 — make datp-cp-run
- Status:
- Before status:
- Command:
- Why this command is being run:
- Expected result:
- Start time:
- End time:
- Duration:
- Exit code:
- Output summary:
- Files changed:
- Fix summary:
- Validation summary:
- Commit/push:
- Next action:

### Step 08 — make audit-results
- Status:
- Before status:
- Command:
- Why this command is being run:
- Expected result:
- Start time:
- End time:
- Duration:
- Exit code:
- Output summary:
- Files changed:
- Fix summary:
- Validation summary:
- Commit/push:
- Next action:

### Step 09 — make status
- Status:
- Before status:
- Command:
- Why this command is being run:
- Expected result:
- Start time:
- End time:
- Duration:
- Exit code:
- Output summary:
- Files changed:
- Fix summary:
- Validation summary:
- Commit/push:
- Next action:

### Step 10 — make datp-cp-report
- Status:
- Before status:
- Command:
- Why this command is being run:
- Expected result:
- Start time:
- End time:
- Duration:
- Exit code:
- Output summary:
- Files changed:
- Fix summary:
- Validation summary:
- Commit/push:
- Next action:

### Step 11 — final make status
- Status:
- Before status:
- Command:
- Why this command is being run:
- Expected result:
- Start time:
- End time:
- Duration:
- Exit code:
- Output summary:
- Files changed:
- Fix summary:
- Validation summary:
- Commit/push:
- Next action:

## Long-running command monitor
- Active command:
- Start time:
- Last heartbeat:
- Elapsed:
- Latest observed log/artifact signal:
- Current outputs/status summary:
- Health assessment:
- Next heartbeat due:

## Failures and fixes
### Failure entry template
- Failed command:
- Elapsed time before failure:
- Exit code:
- Key error:
- Root cause:
- Roadmap/protocol check:
- Files inspected:
- Fix:
- Targeted validation:
- Rerun result:
- Commit:
- Push:

## Final summary
- Completed commands:
- Failed commands:
- Skipped with validation:
- Infeasible cells:
- Missing cells:
- Aborted cells:
- Report artifacts:
- Remaining risks:
- Final commit:
- Final pushed branch:
```

Keep `STATUS.md` concise but complete. It must be good enough that another agent can resume safely.

## 2. Required user-facing status before and after every command

Before each command, send me a short status message with:

1. command about to run;
2. why it is being run;
3. current phase;
4. whether this is a fresh run or resume;
5. expected result;
6. whether `STATUS.md` was updated before the command.

After each command, send me a short status message with:

1. command run;
2. pass/fail;
3. elapsed time spent on that command;
4. key output summary;
5. files changed, if any;
6. whether `STATUS.md` was updated after the command;
7. next command.

Measure elapsed time for every command.

Use shell timing around each command, for example:

```bash
start_ts=$(date +%s)
<COMMAND>
exit_code=$?
end_ts=$(date +%s)
duration=$((end_ts - start_ts))
echo "exit_code=${exit_code}"
echo "duration_seconds=${duration}"
```

Do not batch main workflow commands. Each workflow command must have its own before-status, timed execution, after-status, and `STATUS.md` entry.

## 3. Long-running monitoring

For long-running commands, send me a status update about every 20 minutes.

Each long-run update must include:

1. current command;
2. elapsed time;
3. whether logs or artifacts are still changing;
4. latest meaningful log line or artifact signal;
5. current `outputs` status if safe to inspect;
6. whether the command appears healthy, stalled, or failed;
7. next planned action.

Also update `STATUS.md` at each heartbeat.

Do not go silent during long runs.

Long-running commands likely include:

```bash
make datp-cp-clean
make datp-cp-run
make audit-results
make datp-cp-report
```

Use safe read-only monitoring commands only. Do not interrupt the running process just to inspect status.

## 4. Git safety and single-commit rule

This repository must remain a single-commit working branch during this workflow.

You must amend the current commit after validated fixes.

You must not create additional commits.

You must not make a new commit with a new message.

You must not leave a stack of multiple commits.

After each validated fix, use:

```bash
git status --short
git restore --staged AllCommandsPrompt.md STATUS.md 2>/dev/null || true
git add <specific-relevant-files-only>
git restore --staged AllCommandsPrompt.md STATUS.md 2>/dev/null || true
git status --short
git commit --amend --no-edit
git push --force-with-lease
```

Never use:

```bash
git add .
git add -A
git add --all
git commit -m
git commit
git push --force
```

Use only:

```bash
git commit --amend --no-edit
git push --force-with-lease
```

If amend is impossible for any reason, stop and report the reason. Do not create a second commit as a workaround.

Before any amend, confirm that these files are not staged:

```text
AllCommandsPrompt.md
STATUS.md
```

If they are staged, unstage them:

```bash
git restore --staged AllCommandsPrompt.md STATUS.md 2>/dev/null || true
```

Start with:

```bash
pwd
git status --short
git branch --show-current
git log -1 --oneline
```

Report the branch, commit, and working-tree state.

If there are existing uncommitted user changes, inspect them carefully. Do not overwrite or revert them blindly. Preserve user work unless a change is clearly generated junk or clearly part of the failing state you are fixing.

When a fix is required:

1. Make the smallest correct change.
2. Do not add AI-style comments.
3. Do not add unnecessary comments.
4. If a method/function is changed or added and project style requires docstrings, add or update only short useful docstrings.
5. Run the smallest impacted validation first.
6. Rerun the failed command.
7. Stage only relevant files.
8. Verify `AllCommandsPrompt.md` and `STATUS.md` are not staged.
9. Amend the current commit.
10. Push using `--force-with-lease`.

Do not commit huge generated outputs unless the repository already tracks them intentionally. Respect `.gitignore`.

## 5. Fresh start versus resume

### Fresh start

A fresh start means `STATUS.md` does not exist, or it exists but clearly says the workflow has not passed output cleanup yet.

On a fresh start:

1. Read the roadmap.
2. Create or reset `STATUS.md`.
3. Run preflight checks.
4. Delete `./outputs` only after confirming repo root.
5. Continue the workflow.

### Resume

A resume means `STATUS.md` exists and shows that one or more workflow steps already passed.

On resume:

1. Read `STATUS.md`.
2. Read the roadmap again.
3. Validate the last completed step.
4. Resume from the next incomplete or failed step.
5. Do not delete `outputs` again unless `STATUS.md` shows the workflow never passed cleanup or the current run is explicitly restarted from scratch.

Never rely only on memory. `STATUS.md` plus actual artifact validation decides the resume point.

## 6. Output cleanup rule

Before deleting outputs, confirm:

```bash
pwd
test -f Makefile
test -d .git
```

Only if you are at the repository root and this is a fresh run before experiment execution, run:

```bash
rm -rf outputs
test ! -e outputs && echo "outputs removed"
```

Delete only `./outputs`.

Do not delete raw data, shared data, `.venv`, configs, docs, notebooks, cache directories outside the repo root, or anything outside the repository.

Record the cleanup in `STATUS.md` with start time, end time, duration, and confirmation.

Do not commit `STATUS.md` after recording cleanup.

## 7. Canonical command sequence

Run these commands in order, one by one, with before-status, timing, after-status, and `STATUS.md` updates.

### Step 00 — Preflight and roadmap read

Run:

```bash
pwd
git status --short
git branch --show-current
git log -1 --oneline
```

Then read the active roadmap/protocol files.

Record which roadmap files were consulted in `STATUS.md`.

After reading the roadmap, summarize the active scientific lock in `STATUS.md`.

### Step 01 — Static checks

Run:

```bash
make check
```

If it fails, fix ruff/pyright issues without scientific drift.

Do not silence errors by weakening types, deleting checks, hiding real problems, broadening ignore rules, or changing scientific semantics.

### Step 02 — Unit tests

Run:

```bash
make datp-cp-unit-tests
```

If it fails, fix the actual cause.

Do not delete meaningful tests just to pass.

Remove or update obsolete tests only if they conflict with the active `datp-cp` protocol, and record the roadmap justification in `STATUS.md`.

### Step 03 — Output cleanup

Run only if this is a fresh workflow start before experiment execution:

```bash
pwd
test -f Makefile
test -d .git
rm -rf outputs
test ! -e outputs && echo "outputs removed"
```

If resuming after cleanup or after later commands, do not rerun this step. Mark it as `SKIPPED_WITH_VALIDATION` in `STATUS.md`.

### Step 04 — Clean artifact generation

Run:

```bash
make datp-cp-clean
```

Monitor as long-running if needed.

If it fails:

1. inspect logs and manifests;
2. decide whether it is a code, config, data, provenance, or environment issue;
3. preserve E=1, FedAvg, split semantics, q=95, clean artifact provenance, and roadmap rules;
4. fix narrowly;
5. rerun impacted validation;
6. rerun `make datp-cp-clean`;
7. amend the current commit and push with lease.

### Step 05 — Synthetic smoke invariant tests

Run:

```bash
make datp-cp-smoke
```

This must pass before the main run.

If it fails, treat it as a blocking protocol-invariant failure.

Fix the invariant implementation or test expectation according to the active roadmap.

Do not loosen tests to hide:

1. leakage;
2. mutation;
3. AUROC movement;
4. invalid source-objective pairs;
5. stale policy labels;
6. cluster-threshold reproducibility issues;
7. threshold-direction errors;
8. deterministic-pairing errors.

### Step 06 — Dry-run plan enumeration

Run:

```bash
make datp-cp-dry-run
```

Validate that the plan matches the authorized matrix:

1. N-BaIoT;
2. physical-device clients;
3. all eligible single-client victims;
4. `GLOBAL_THRESHOLD`, `LOCAL_THRESHOLD`, `CLUSTER_THRESHOLD`;
5. valid source-objective pairs only;
6. fractions `{0, 0.10, 0.20, 0.40}`;
7. paired seeds;
8. no journal-extension assets;
9. no stale code-facing labels.

If the dry run includes invalid combinations, stale labels, excluded scope, missing victims, wrong policies, wrong fractions, or wrong seed semantics, fix before continuing.

### Step 07 — Main bounded sweep

Run:

```bash
make datp-cp-run
```

This is the long-running authorized N-BaIoT main calibration-poisoning matrix.

Send progress updates every ~20 minutes and update `STATUS.md`.

If a cell fails:

1. do not ignore it;
2. inspect whether it is an infeasible reservoir, expected manifest exclusion, or real implementation failure;
3. if infeasible, ensure it is consistently marked and reported according to the roadmap;
4. if implementation failure, fix narrowly, validate, amend the current commit, push with lease, and continue or resume according to supported behavior;
5. do not rerun already-complete expensive cells unless necessary for consistency.

### Step 08 — Results audit

Run:

```bash
make audit-results
```

If it fails, fix provenance, manifest, leakage, schema, or scientific-contract issues properly.

Do not bypass audit checks.

The audit must protect:

1. clean artifact provenance;
2. no test-score reservoirs;
3. no training-score reservoirs;
4. no attack labels in calibration;
5. unchanged test scores and labels;
6. correct threshold policies;
7. q=95;
8. `CLUSTER_THRESHOLD` reproducibility and decomposition;
9. valid source-objective pairs;
10. AUROC sanity behavior.

### Step 09 — Status command

Run:

```bash
make status
```

Report complete, missing, aborted, and infeasible counts clearly.

If missing or aborted cells exist, determine whether they are legitimate infeasible cells or actual failures. Fix and recover actual failures.

### Step 10 — Report generation

Run:

```bash
make datp-cp-report
```

If it fails, fix the report builder or artifact schema narrowly.

Do not fabricate results.

Do not hide missing or aborted cells.

Do not make claims unsupported by completed outputs.

### Step 11 — Final status

Run:

```bash
make status
```

Report final workflow state and update `STATUS.md`.

## 8. Failure-handling loop

When any command fails:

1. Write failure state to `STATUS.md`.
2. Send me the failed command, elapsed time, exit code, and key error.
3. Refer back to the roadmap before editing.
4. Identify the smallest likely cause.
5. Inspect the relevant files manually.
6. Fix only the relevant code, test, config, or docs.
7. Do not use mass rewrite scripts.
8. Do not insert broad comments.
9. Do not add AI/agent references in code comments or docstrings.
10. Keep method docstrings short and useful when needed.
11. Run targeted checks/tests first.
12. Rerun the failed command.
13. Record the rerun duration in `STATUS.md`.
14. If fixed, amend the current commit and push with `--force-with-lease`.
15. Continue to the next workflow command.

Do not solve failures by:

1. deleting meaningful tests;
2. weakening scientific assertions;
3. changing the protocol;
4. changing thresholds, fractions, seeds, or policies to make results easier;
5. suppressing pyright/ruff without a real reason;
6. editing generated outputs manually;
7. fabricating manifests;
8. hiding missing cells;
9. using test scores, training scores, attack labels, or cross-client reservoirs for main claims;
10. skipping audit gates;
11. creating a second commit.

## 9. Fixing discipline for code, comments, and docstrings

When editing code:

1. Make the smallest correct change.
2. Preserve existing architecture unless the roadmap or failure clearly requires a change.
3. Do not add AI-style comments.
4. Do not add comments explaining obvious code.
5. Do not add roadmap references in code comments unless the project already uses that pattern.
6. If a method/function is changed and docstrings are expected by project style, update the docstring.
7. If a new method/function is added and docstrings are expected by project style, add a short docstring.
8. Keep docstrings short, technical, and useful.
9. Update tests only to match the active protocol, not to hide bugs.
10. Do not use mass scripts for broad edits.

## 10. Amend and push rules

After a validated fix, use this exact discipline:

```bash
git status --short
git restore --staged AllCommandsPrompt.md STATUS.md 2>/dev/null || true
git add <specific-relevant-files-only>
git restore --staged AllCommandsPrompt.md STATUS.md 2>/dev/null || true
git status --short
git commit --amend --no-edit
git push --force-with-lease
```

Before amending, update `STATUS.md`.

Do not stage `STATUS.md`.

Do not stage `AllCommandsPrompt.md`.

After pushing, update `STATUS.md` with:

1. amended commit hash;
2. pushed branch;
3. validation command;
4. next workflow step.

Do not create a new commit. The branch must remain one amended commit.

If a new commit seems necessary, stop and report why. Do not create it.

## 11. Reporting format to me during the run

Before a command, use this format:

```text
Before command:
1. Phase:
2. Fresh/resume:
3. Command:
4. Why:
5. Expected result:
6. STATUS.md updated:
```

After a command, use this format:

```text
After command:
1. Command:
2. Result:
3. Duration:
4. Exit code:
5. Key output:
6. Files changed:
7. STATUS.md updated:
8. Next:
```

During long runs, use this format:

```text
Heartbeat:
1. Active command:
2. Elapsed:
3. Latest signal:
4. Outputs/status:
5. Health:
6. Next heartbeat/action:
```

On failure, use this format:

```text
Failure:
1. Command:
2. Duration before failure:
3. Exit code:
4. Key error:
5. Likely cause:
6. Roadmap check:
7. Planned narrow fix:
```

After a fix, use this format:

```text
Fix validated:
1. Root cause:
2. Files changed:
3. Validation:
4. Rerun result:
5. Duration:
6. Commit:
7. Push:
8. Next:
```

## 12. Final report to me

At the end, send me a concise but complete final report with:

1. branch;
2. final commit hash;
3. whether this was fresh or resumed;
4. confirmation that the branch remains a single amended commit;
5. confirmation that `AllCommandsPrompt.md` was not committed;
6. confirmation that `STATUS.md` was not committed;
7. commands run in order;
8. before/after status for each command;
9. elapsed time for each command;
10. pass/fail for each command;
11. fixes made;
12. whether `outputs` was deleted at the start;
13. whether any steps were skipped with validation;
14. whether any cells were infeasible;
15. whether any cells were missing;
16. whether any cells were aborted;
17. whether any cells were rerun;
18. final `make status` summary;
19. final artifact/report locations;
20. final local `STATUS.md` location;
21. remaining risks or manual review items.

Do not claim success unless every required command has passed or any remaining limitation is explicitly justified by the active roadmap.

## 13. Start now

Begin by going to the repository root, reading `STATUS.md` if it exists, reading the active roadmap/protocol files, updating `STATUS.md`, and then running Step 00 with before-status and after-status reporting.

Remember:

1. `AllCommandsPrompt.md` is local-only.
2. `STATUS.md` is local-only.
3. Do not stage either file.
4. Do not commit either file.
5. Do not create new commits.
6. Always amend the current commit after validated fixes.
7. Always push with `--force-with-lease`.
