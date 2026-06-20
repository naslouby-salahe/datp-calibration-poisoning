# Claude Resume Prompt — datp-cp

You are Claude Code working in:

    /home/naslouby/Projects/datp-calibration-poisoning

Resume the interrupted datp-cp cleanup, refactor, implementation, testing, documentation, and audit effort.

This repository is now a greenfield datp-cp project. The new datp-cp roadmap is the source of truth. Existing code, tests, configs, prompts, README files, Makefile targets, CLI names, `.claude` agents, `.claude` commands, and old generated artifacts may be stale and must not be trusted until audited.

Do not commit.

Do not create a PR.

Do not stop at planning.

Work continuously until the repository is cleaned, aligned with the roadmap, tested, audited, documented, and reported.

---

## 1. First read, then act

Before editing, read:

- the new datp-cp roadmap;
- `.rework/STATUS.md`;
- `.rework/ROADMAP_CONTRACT.md` if present;
- `.rework/FINAL_REPORT.md` if present;
- `.rework/tasks/`;
- `.rework/audits/`;
- `Makefile`;
- `README*`;
- `CLAUDE.md`;
- `.claude/`;
- `src/`;
- `tests/`;
- configs if present;
- scripts if present.

Then create or update:

- `.rework/ROADMAP_CONTRACT.md`;
- `.rework/CODE_INVENTORY.md`;
- `.rework/OBSOLETE_TERMS_AUDIT.md`;
- `.rework/RENAME_PLAN.md`;
- `.rework/REMOVAL_PLAN.md`;
- `.rework/TEST_PLAN.md`;
- `.rework/STATUS.md`;
- `.rework/DECISIONS.md`.

Do not edit blindly. First understand the roadmap and the current repository state.

If `.rework/STATUS.md` indicates previous work, continue from the latest reliable state. Do not restart the effort unless the existing status is clearly invalid.

---

## 2. Roadmap authority

The new datp-cp roadmap wins over:

- existing code;
- old tests;
- old README content;
- old `CLAUDE.md` content;
- old `.claude` instructions;
- old tickets;
- old Makefile targets;
- old configs;
- old CLI help text;
- old output manifests;
- old experiment scripts;
- old prompt files.

When code and roadmap disagree, change the code.

When tests and roadmap disagree, change the tests.

When docs and roadmap disagree, change the docs.

When `.claude` and roadmap disagree, change `.claude`.

When old prompts and roadmap disagree, change the prompts.

Record important decisions in `.rework/DECISIONS.md`.

---

## 3. Canonical project identity

Canonical project name:

- `datp-cp`

Use `datp-cp` in human-facing docs, README files, `CLAUDE.md`, `.claude`, logs, final reports, and prompts.

Use Python-safe identifiers where needed:

- `datp_cp`
- `DatpCp`

Do not use old project names in active artifacts.

---

## 4. Canonical experiment stages

The only canonical active experiment stages are:

- `SYNTHETIC_SMOKE`
- `NBAIOT_MAIN`
- `CICIOT_STRETCH`

Use a strict enum for these.

Expected shape:

    from enum import Enum

    class ExperimentStage(Enum):
        SYNTHETIC_SMOKE = "synthetic_smoke"
        NBAIOT_MAIN = "nbaiot_main"
        CICIOT_STRETCH = "ciciot_stretch"

Rules:

- Internal APIs must accept `ExperimentStage`, not raw strings.
- CLI/config parsing may convert strings into `ExperimentStage` at the boundary.
- After parsing, pass enums through the codebase.
- Do not accept obsolete stage names.
- Do not add compatibility aliases.
- Do not silently map old names to new names.
- If an obsolete value is passed, fail clearly.

---

## 5. Canonical threshold policies

The only canonical active threshold policies are:

- `GLOBAL_THRESHOLD`
- `LOCAL_THRESHOLD`
- `CLUSTER_THRESHOLD`

Use a strict enum.

Expected shape:

    from enum import Enum

    class ThresholdPolicy(Enum):
        GLOBAL_THRESHOLD = "global_threshold"
        LOCAL_THRESHOLD = "local_threshold"
        CLUSTER_THRESHOLD = "cluster_threshold"

Rules:

- Internal APIs must accept `ThresholdPolicy`, not raw strings.
- No numbered threshold-policy names in active source code.
- No numbered threshold-policy names in tests.
- No numbered threshold-policy names in docs.
- No numbered threshold-policy names in configs.
- No numbered threshold-policy names in CLI values.
- No numbered threshold-policy names in Makefile targets.
- No numbered threshold-policy names in manifests.
- No numbered threshold-policy names in `.claude`.
- No obsolete policy aliases.
- No compatibility parser that accepts old names.
- No default policy outside the roadmap.
- If an obsolete value is supplied, fail clearly.

---

## 6. Canonical Makefile workflow

The public Makefile workflow must be exactly:

- `make help`
- `make check`
- `make datp-cp-clean`
- `make datp-cp-smoke`
- `make datp-cp-dry-run`
- `make datp-cp-run`
- `make datp-cp-report`
- `make clean`

Rules:

- `make help` must show only intended public targets.
- No obsolete regime, matrix, sweep, or bounded-run targets in public help.
- No hidden old workflow that humans or agents are instructed to use.
- Internal implementation helpers are allowed only if they do not expose obsolete naming or obsolete workflow.
- `check` must run tests, typecheck, and lint.
- `datp-cp-clean` must generate or validate clean N-BaIoT E=1 score artifacts required by datp-cp.
- `datp-cp-smoke` must run synthetic smoke invariants.
- `datp-cp-dry-run` must validate the N-BaIoT main poisoning matrix without running the full experiment.
- `datp-cp-run` must run the N-BaIoT main calibration-poisoning experiment.
- `datp-cp-report` must audit results and build stats, figures, and tables.
- `clean` must remove temporary/cache artifacts only.
- `clean` must not delete raw data.
- `clean` must not delete important outputs unless explicitly documented as safe.

---

## 7. Absolute no-compatibility rules

No backwards compatibility.

No legacy aliases.

No old aliases.

No old enum members.

No old CLI values accepted.

No old config values accepted.

No old Makefile workflow preserved.

No permissive parsing.

No fallback to old configs.

No translation maps from obsolete names to new names.

No “accept both old and new” behavior.

No “legacy mode”.

No “compat mode”.

No “old name accepted for convenience”.

Do not use compatibility unions such as:

- `ThresholdPolicy | str`
- `ExperimentStage | str`
- `DatpCpConfig | dict[str, Any]`
- `Enum | str`
- `Path | str` inside core logic

If raw inputs arrive from CLI, config files, JSON, or YAML, convert them at the boundary into strict enums and frozen dataclasses. After that point, core code must operate on typed objects.

If obsolete values are passed, fail fast with a clear error message.

---

## 8. Dataclasses and enum discipline

Use enums for closed vocabularies.

Use dataclasses for structured configuration, manifests, matrix definitions, run plans, audit records, typed DTOs, and result records.

Preferred dataclass style:

    from dataclasses import dataclass
    from pathlib import Path

    @dataclass(frozen=True, slots=True)
    class DatpCpRunConfig:
        stage: ExperimentStage
        policies: tuple[ThresholdPolicy, ...]
        output_root: Path

Rules:

- Prefer `@dataclass(frozen=True, slots=True)` for configs and immutable records.
- Use `tuple[...]` for immutable sequences in configs.
- Use `Path` instead of raw path strings internally.
- Parse raw CLI/config dictionaries at boundaries only.
- Convert raw inputs into typed dataclasses immediately.
- Internal functions should receive dataclasses/enums, not untyped dictionaries.
- Avoid `dict[str, Any]`; use typed dataclasses.
- Avoid `Any`, `object`, and broad `Mapping[str, Any]` unless at a strict external boundary.
- If `Any` is unavoidable, isolate it, justify it, and convert into typed structures immediately.
- Do not use dataclass fields that accept multiple unrelated types for compatibility.
- Do not use `type: ignore` unless truly unavoidable. If used, add a short justification.

---

## 9. Type-safety rules

Prefer precise types from the start.

Avoid:

- `Any`
- `object`
- `dict`
- `Dict`
- `Mapping[str, Any]`
- untyped `list`
- untyped `tuple`
- compatibility `Union`
- long `isinstance` chains for config cleanup
- unnecessary `type: ignore`

Acceptable only when justified:

- JSON boundary before validation;
- YAML boundary before validation;
- third-party library return type that is genuinely untyped;
- CLI raw input before conversion;
- temporary notes inside `.rework`, not active source.

After boundary parsing, code should operate on:

- enums;
- frozen dataclasses;
- typed paths;
- typed tuples;
- typed arrays;
- explicit metric/result records.

Tests must enforce rejection of obsolete strings.

---

## 10. Scientific contract

datp-cp is calibration-channel poisoning only.

The only attack surface is the benign threshold-calibration set.

The attack must not alter:

- training data;
- training labels;
- model weights;
- gradients;
- FedAvg aggregation;
- server code;
- test scores;
- test labels;
- test data;
- other clients’ raw data.

Clean and poisoned runs must be paired by:

- `training_seed`;
- victim plan;
- model/checkpoint;
- split;
- test scores;
- test labels.

Poisoning is the only stochastic difference.

Reservoir rules:

- victim-local reservoirs;
- with-replacement value resampling;
- fixed-size replacement;
- no test-score reservoir;
- no training-score reservoir;
- no cross-client reservoir in main claims.

Threshold recomputation rules:

- `GLOBAL_THRESHOLD` is recomputed from eligible clients’ local thresholds;
- `LOCAL_THRESHOLD` is recomputed per client;
- `CLUSTER_THRESHOLD` is recomputed using the fixed cluster procedure and client-effective thresholds;
- cluster deltas are compared by client, not by raw cluster label IDs.

---

## 11. Main implementation expectations

After cleanup, ensure the repository implements or clearly stubs with tests for:

- clean N-BaIoT E=1 artifact generation or validation;
- artifact provenance validation;
- score-level calibration poisoning;
- victim-local with-replacement reservoirs;
- `GLOBAL_THRESHOLD` recomputation;
- `LOCAL_THRESHOLD` recomputation;
- `CLUSTER_THRESHOLD` recomputation;
- cluster-threshold decomposition;
- paired clean-vs-poisoned metrics;
- synthetic smoke invariants;
- N-BaIoT main dry-run matrix enumeration;
- result audit;
- stats/figures/tables hooks;
- manifest completeness.

Do not implement broad out-of-scope features just because old code had them.

---

## 12. Obsolete active terminology audit

Search the repo for obsolete active terminology.

Use at minimum:

    grep -RIn --exclude-dir=.git --exclude-dir=.venv --exclude-dir=outputs --exclude-dir=.rework \
      -E "CP2|Regime A|Regime B|Regime C|Regime D|REGIME_A|REGIME_B|REGIME_C|REGIME_D|B1|B2|B3|B4|B1_GLOBAL|B2_PERSONALIZED|B4_CLUSTER|run-regime|run-main-matrix|poison-bounded|poison-stages|legacy|backward|compat" .

Classify each occurrence in `.rework/OBSOLETE_TERMS_AUDIT.md`.

Classification values:

- active issue;
- stale generated artifact;
- historical note;
- acceptable only inside `.rework`;
- already fixed;
- false positive.

Active issues must be fixed.

---

## 13. Required tests

Remove obsolete tests that validate removed behavior.

Add or update tests for:

- canonical enums contain only new values;
- obsolete enum/config/CLI values fail;
- internal APIs use enums/dataclasses instead of strings/dicts;
- Makefile exposes only intended public workflow;
- synthetic smoke fraction `0` gives zero threshold shift;
- `RANDOM_BENIGN` is near-null on synthetic data;
- `HIGH_SCORE_BENIGN` raises local thresholds;
- `LOW_SCORE_BENIGN` lowers local thresholds;
- clean calibration arrays are not mutated in place;
- AUROC remains invariant under threshold-only recalibration;
- cluster threshold decomposition is finite and client-indexed;
- N-BaIoT main dry-run enumerates expected dimensions;
- artifact manifests contain required provenance fields;
- outputs remain under `outputs/conference_calibration_poisoning/`;
- README, `CLAUDE.md`, and `.claude` do not advertise obsolete workflow.

Tests should protect the roadmap contract, not old behavior.

---

## 14. Required audits

Write or update:

- `.rework/audits/SCIENTIFIC_DRIFT_AUDIT.md`
- `.rework/audits/CODE_QUALITY_AUDIT.md`
- `.rework/audits/NAMING_AUDIT.md`
- `.rework/audits/MAKEFILE_AUDIT.md`
- `.rework/audits/TEST_AUDIT.md`
- `.rework/audits/DOCS_AND_CLAUDE_FOLDER_AUDIT.md`

Scientific audit must check:

- calibration-channel-only guarantee;
- no training leakage;
- no test leakage;
- no model poisoning;
- no aggregation poisoning;
- clean-vs-poisoned pairing;
- victim-local reservoir use;
- fixed-budget with-replacement injection;
- correct threshold policies;
- correct attack objectives;
- correct source strategies;
- correct unit of analysis;
- correct threshold-raising narrative;
- correct threshold-lowering narrative;
- cluster-threshold decomposition correctness;
- no journal contamination;
- no scope creep;
- claims do not exceed evidence.

Code-quality audit must check:

- enums for closed vocabularies;
- frozen dataclasses for configs/results/manifests;
- specific types over `Any`/`object`/`dict`;
- no compatibility unions;
- minimal `isinstance` checks;
- no unjustified `type: ignore`;
- deterministic seeding;
- no in-place mutation;
- clear validation;
- simple Makefile;
- clean CLI;
- no dead obsolete code.

---

## 15. Documentation and `.claude` update rules

Update:

- `README*`
- `CLAUDE.md`
- `.claude/`

They must teach agents and humans the current datp-cp workflow only.

They must not direct anyone toward:

- obsolete naming;
- old matrix workflows;
- old regime commands;
- old threshold-policy names;
- compatibility behavior;
- broad DATP sweeps;
- journal-only scope;
- unsafe experiment execution.

If `.claude` contains commands such as `cleanCode` or `cleanCodeCommit`:

1. Inspect the command definition.
2. Do not run anything that commits.
3. Reuse only non-commit checks if useful.
4. Update the command/instructions to datp-cp naming and no-compatibility rules.

---

## 16. Commands to run

Run when safe:

- `make help`
- `make check`
- `make datp-cp-smoke`
- `make datp-cp-dry-run`

Run only if data/environment are ready:

- `make datp-cp-clean`
- `make datp-cp-run`
- `make datp-cp-report`

If a command is not run, document exactly why in `.rework/FINAL_REPORT.md`.

If a command fails, fix the cause or document the blocker clearly with exact output.

---

## 17. Status and final report

Update `.rework/STATUS.md` after every major pass.

Write `.rework/FINAL_REPORT.md` before stopping.

Final report must include:

- what was changed;
- what active workflow was removed;
- current public commands;
- enums/dataclasses introduced or corrected;
- tests removed;
- tests added/updated;
- docs updated;
- `.claude` files updated;
- audits run;
- commands run and results;
- remaining risks;
- roadmap-alignment verdict;
- scientific-readiness verdict;
- execution-readiness verdict.

No commits.

No PRs.