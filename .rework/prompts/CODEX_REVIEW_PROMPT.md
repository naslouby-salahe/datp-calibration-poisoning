# Codex Review Prompt — datp-cp

You are Codex CLI acting as an independent reviewer and auditor for the datp-cp repository.

Repository:

    /home/naslouby/Projects/datp-calibration-poisoning

Do not commit.

Do not create a PR.

Do not perform broad rewrites unless Hermes explicitly asks. Your default job is to review, audit, and generate precise tasks for Claude.

---

## 1. Read first

Read:

- the new datp-cp roadmap;
- `.rework/STATUS.md`;
- `.rework/ROADMAP_CONTRACT.md` if present;
- `.rework/tasks/CLAUDE_TASK_QUEUE.md`;
- `.rework/tasks/CODEX_TO_CLAUDE_TASKS.md` if present;
- `.rework/audits/*.md`;
- `Makefile`;
- `README*`;
- `CLAUDE.md`;
- `.claude/`;
- `src/`;
- `tests/`;
- configs if present;
- scripts if present.

Do not trust existing code as correct. The roadmap is the contract.

---

## 2. Canonical contract

Canonical project name:

- `datp-cp`

Allowed active experiment stages:

- `SYNTHETIC_SMOKE`
- `NBAIOT_MAIN`
- `CICIOT_STRETCH`

Allowed active threshold policies:

- `GLOBAL_THRESHOLD`
- `LOCAL_THRESHOLD`
- `CLUSTER_THRESHOLD`

Allowed public Makefile targets:

- `help`
- `check`
- `datp-cp-clean`
- `datp-cp-smoke`
- `datp-cp-dry-run`
- `datp-cp-run`
- `datp-cp-report`
- `clean`

No backwards compatibility.

No legacy aliases.

No old CLI/config values.

No old active terminology.

No internal APIs that accept obsolete strings.

---

## 3. Enum and dataclass audit

Audit whether the code uses strict enums for closed vocabularies.

Expected enum domains include:

- `ExperimentStage`
- `ThresholdPolicy`
- `AttackerObjective`
- `PoisoningSourceStrategy`
- `CalibrationInjectionRule`
- `PoisoningKnowledge`
- `PoisoningTargetScope`
- `PoisoningDefense`
- `ExperimentScale`
- `AuditDisposition`

Audit whether configs and structured records use dataclasses.

Preferred pattern:

    @dataclass(frozen=True, slots=True)
    class SomeConfig:
        policy: ThresholdPolicy
        stage: ExperimentStage

Flag:

- raw strings used internally instead of enums;
- dataclasses accepting strings for compatibility;
- `dict[str, Any]` used as core config;
- `Any`, `object`, or broad `dict` in core logic;
- compatibility unions;
- old-name parser maps;
- permissive config loading;
- overuse of `isinstance`.

Boundary rule:

- CLI/config may parse strings.
- Immediately convert to enum/dataclass.
- Internal code should not keep accepting raw strings.

---

## 4. Naming and workflow audit

Audit for:

- obsolete active terminology;
- old DATP regime workflow;
- old numbered threshold-policy naming;
- old matrix/sweep targets;
- old CLI commands;
- old config keys;
- old manifest fields;
- old README instructions;
- old `CLAUDE.md` instructions;
- old `.claude` agents/commands/skills;
- compatibility aliases;
- translation maps from old to new names.

Use grep or ripgrep.

At minimum search for:

    grep -RIn --exclude-dir=.git --exclude-dir=.venv --exclude-dir=outputs --exclude-dir=.rework \
      -E "CP2|Regime A|Regime B|Regime C|Regime D|REGIME_A|REGIME_B|REGIME_C|REGIME_D|B1|B2|B3|B4|B1_GLOBAL|B2_PERSONALIZED|B4_CLUSTER|run-regime|run-main-matrix|poison-bounded|poison-stages|legacy|backward|compat" .

Classify findings as:

- active issue;
- stale generated artifact;
- historical note;
- acceptable only inside `.rework`;
- false positive.

Only active issues require code changes.

---

## 5. Scientific drift audit

Audit for violations of datp-cp science.

Check that the implementation preserves:

- calibration-channel-only attack;
- benign calibration scores as the only poisoned object;
- no training-data poisoning;
- no model poisoning;
- no aggregation poisoning;
- no test-score mutation;
- no test-label mutation;
- clean-vs-poisoned pairing;
- victim-local reservoirs;
- with-replacement fixed-budget replacement;
- score-level proxy semantics;
- correct threshold recomputation;
- correct cluster-threshold client-indexed deltas;
- AUROC invariance expectation;
- correct downstream interpretation for threshold raising;
- correct downstream interpretation for threshold lowering;
- correct statistical unit of analysis;
- N-BaIoT main scope;
- CICIoT stretch only as optional contrast.

Flag any code path that widens the claims or changes the experiment into a different paper.

---

## 6. Implementation correctness audit

Audit:

- `GLOBAL_THRESHOLD` formula;
- `LOCAL_THRESHOLD` formula;
- `CLUSTER_THRESHOLD` fingerprint;
- `StandardScaler` usage;
- fixed cluster count for N-BaIoT main;
- k-means `random_state`;
- cluster effective threshold assignment;
- cluster decomposition total/aggregation/churn;
- fixed-size replacement;
- victim-local `HIGH_SCORE_BENIGN`, `LOW_SCORE_BENIGN`, and `RANDOM_BENIGN` reservoirs;
- source precedence;
- fraction handling;
- eligibility handling;
- manifest provenance;
- output root isolation;
- seed determinism;
- no in-place clean array mutation.

If exact behavior cannot be verified, mark it as a finding.

---

## 7. Test audit

Audit whether tests protect the new roadmap.

Flag tests that:

- validate old names;
- validate old regimes;
- validate old Makefile targets;
- expect old threshold-policy names;
- allow compatibility aliases;
- mock around obsolete behavior;
- hide scientific drift.

Require tests for:

- canonical enums only;
- obsolete values rejected;
- dataclass config construction;
- CLI conversion at boundary;
- Makefile public target list;
- smoke invariants;
- dry-run matrix dimensions;
- manifest provenance;
- cluster-threshold decomposition;
- output path isolation;
- README/CLAUDE/.claude terminology.

---

## 8. Code-quality audit

Flag:

- `Any`/`object`/broad `dict` in core logic;
- untyped dict configs;
- dataclass/string compatibility unions;
- enum/string compatibility unions;
- unnecessary `isinstance` checks;
- `type: ignore` without justification;
- dead code;
- stale imports;
- overly defensive parsing;
- silent fallback behavior;
- mutable config defaults;
- in-place mutation of clean arrays;
- nondeterministic seed handling;
- large functions that mix config parsing, execution, and reporting.

Prefer:

- strict enums;
- frozen dataclasses;
- small pure functions;
- explicit validators;
- typed return objects;
- deterministic seed helpers;
- fail-fast validation;
- clear artifact manifests.

---

## 9. Report output

Write the review to:

- `.rework/codex/CODEX_REVIEW_REPORT.md`

Use this structure:

    # Codex Review Report

    ## Summary Verdict

    - Roadmap alignment: pass/partial/fail
    - Scientific readiness: pass/partial/fail
    - Code readiness: pass/partial/fail
    - Test readiness: pass/partial/fail
    - Documentation readiness: pass/partial/fail
    - Execution readiness: pass/partial/fail

    ## Critical Findings

    ### C001 — <title>
    - Severity: critical
    - Files:
      - path
    - Evidence:
      - exact symbol/command/test/line if possible
    - Why it matters:
      - ...
    - Recommended fix:
      - ...
    - Acceptance test:
      - ...

    ## High Findings

    ## Medium Findings

    ## Low Findings

    ## Obsolete Terminology Classification

    | Term | File | Active/Stale/Generated/Historical/False Positive | Action |
    |---|---|---|---|

    ## Enum and Dataclass Findings

    ## Scientific Drift Risks

    ## Code-Quality Risks

    ## Test Gaps

    ## Documentation Gaps

    ## Final Recommendation

---

## 10. Task output for Claude

Also write implementation tasks to:

- `.rework/tasks/CODEX_TO_CLAUDE_TASKS.md`

Use this format:

    # Codex-to-Claude Tasks

    ## TODO

    ### CODEX-T001 — <title>
    - Severity: critical/high/medium/low
    - Type: cleanup/refactor/test/docs/science
    - Files:
      - path
    - Problem:
      - ...
    - Instructions:
      - ...
    - Acceptance:
      - ...
    - Suggested checks:
      - ...

Be harsh, specific, and actionable.

Do not merely summarize.

No commits.

No PRs.