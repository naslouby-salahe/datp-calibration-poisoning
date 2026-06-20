# Refactor Loop State

## 1. Current Phase

Phase: `DOCS_INITIALIZATION_ONLY`

This workspace exists to coordinate a future multi-agent refactor campaign for:

`/home/naslouby/Projects/datp-calibration-poisoning/`

The current phase is documentation and coordination setup only.

No source-code refactoring should happen from this file alone.

## 2. Repository Metadata

Fill these values when the workspace is initialized or refreshed.

| Field                              | Value                                                 |
| ---------------------------------- | ----------------------------------------------------- |
| Repository root                    | `/home/naslouby/Projects/datp-calibration-poisoning/` |
| Initialized at                     | `TO_BE_FILLED`                                        |
| Last refreshed at                  | `TO_BE_FILLED`                                        |
| Git branch                         | `TO_BE_FILLED`                                        |
| Git commit hash                    | `TO_BE_FILLED`                                        |
| Git status summary                 | `TO_BE_FILLED`                                        |
| Current phase                      | `DOCS_INITIALIZATION_ONLY`                            |
| Intended durable orchestrator      | `OpenClaw / Copilot Sonnet`                           |
| Primary specialist implementer     | `Claude Code Sonnet`                                  |
| Secondary code specialist          | `Codex CLI`                                           |
| Harsh reviewer                     | `Hermes / DeepSeek Pro`                               |
| Source files modified during setup | `NO`                                                  |
| Test files modified during setup   | `NO`                                                  |
| Experiments run during setup       | `NO`                                                  |
| Commits made during setup          | `NO`                                                  |

## 3. Campaign Objective

The campaign is refactor-first.

The main engineering objective is to make the repository strict, typed, auditable, and hard to misuse.

The target design is:

| Area                        | Target                          |
| --------------------------- | ------------------------------- |
| Domain modes                | Enums                           |
| Runtime configuration       | Dataclasses                     |
| Experiment plans            | Dataclasses                     |
| Manifest records            | Dataclasses                     |
| Metric records              | Dataclasses                     |
| Threshold results           | Dataclasses                     |
| Poisoning results           | Dataclasses                     |
| Scientific constants        | Centralized config/constants    |
| Raw CLI/config inputs       | Confined to parser boundaries   |
| Invalid configuration       | Fail fast                       |
| Duplicated scientific logic | Consolidated under clear owners |

The campaign should aggressively remove:

| Debt                                       | Expected direction                               |
| ------------------------------------------ | ------------------------------------------------ |
| `Any` in core/domain code                  | Eliminate                                        |
| `object` in core/domain code               | Eliminate                                        |
| `dict` shaped domain contracts             | Replace with dataclasses                         |
| Raw strings for domain choices             | Replace with enums                               |
| Hardcoded scientific values                | Move to config/constants                         |
| Duplicate poisoning/threshold/metric logic | Centralize                                       |
| Broad `isinstance` chains                  | Replace with typed boundaries                    |
| Silent coercion                            | Replace with validation                          |
| Backward-compatibility shims               | Avoid unless required by locked artifact formats |
| `type: ignore`                             | Remove unless documented as unavoidable          |

## 4. Locked Scientific Contract

CP2 is calibration-channel poisoning only.

The implementation must preserve every item below.

| Scientific invariant          | Required state                                                     |
| ----------------------------- | ------------------------------------------------------------------ |
| Poisoning scope               | Only benign threshold-calibration inputs or scores may be modified |
| Training data                 | Must remain clean                                                  |
| Model weights                 | Must remain clean                                                  |
| FedAvg aggregation            | Must remain clean                                                  |
| Test scores                   | Must remain clean                                                  |
| Test labels                   | Must remain clean                                                  |
| Clean artifacts               | Must be reused read-only                                           |
| Primary dataset               | N-BaIoT                                                            |
| Artifact reuse                | Conference-faithful E=1 artifacts only                             |
| Default threshold policies    | `B1_GLOBAL`, `B2_PERSONALIZED`, `B4_CLUSTER`                       |
| B3 status                     | Not part of the default CP2 path                                   |
| Clean/poisoned pairing        | Paired by `training_seed` and victim plan                          |
| Stochastic difference         | Poisoning must be the sole stochastic difference                   |
| Journal assets                | Out of scope                                                       |
| New FL algorithms             | Out of scope                                                       |
| Model personalization         | Out of scope                                                       |
| Aggregation-comparator claims | Out of scope                                                       |
| Training poisoning            | Out of scope                                                       |
| Model poisoning               | Out of scope                                                       |
| Test poisoning                | Out of scope                                                       |
| Evasion claims                | Out of scope                                                       |
| Privacy guarantees            | Out of scope                                                       |
| Deployment-readiness claims   | Out of scope                                                       |
| Broad robustness claims       | Out of scope beyond the calibration channel                        |

## 5. Threat-Model Lock

The attacker may compromise local calibration curation only.

The attacker may not alter:

| Forbidden target   | Required protection |
| ------------------ | ------------------- |
| Training data      | No mutation path    |
| Model updates      | No mutation path    |
| Server aggregation | No mutation path    |
| Model weights      | No mutation path    |
| Server code        | No attack path      |
| Test scores        | No mutation path    |
| Test labels        | No mutation path    |

The intended attack surface is the benign calibration channel only.

## 6. B4 Lock

B4 must remain the locked CP2/DATP procedure.

| B4 item                  | Required state                                         |
| ------------------------ | ------------------------------------------------------ |
| Regime A K               | `3`                                                    |
| Random state             | `42`                                                   |
| Initialization           | k-means++                                              |
| n_init                   | Locked by config/constants                             |
| max_iter                 | Locked by config/constants                             |
| Fingerprint              | Locked CP2/DATP fingerprint                            |
| Delta semantics          | Client-effective threshold deltas                      |
| Cluster-label comparison | Raw k-means label IDs must not be compared across runs |

## 7. Workspace File Status

Update this table as files are populated.

| File                            | Status           | Owner                 | Notes                         |
| ------------------------------- | ---------------- | --------------------- | ----------------------------- |
| `01_FILE_INDEX.md`              | `TEMPLATE`       | OpenClaw subagent     | File inventory                |
| `02_SYMBOL_INDEX.md`            | `TEMPLATE`       | OpenClaw subagent     | Symbol inventory              |
| `03_METHOD_IO_INDEX.md`         | `TEMPLATE`       | OpenClaw subagent     | Inputs, outputs, side effects |
| `04_DATACLASS_ENUM_INDEX.md`    | `TEMPLATE`       | OpenClaw subagent     | Typed contract inventory      |
| `05_TYPE_DEBT_LEDGER.md`        | `TEMPLATE`       | OpenClaw subagent     | Any/object/dict debt          |
| `06_HARDCODED_VALUES_LEDGER.md` | `TEMPLATE`       | OpenClaw subagent     | Hardcoded values              |
| `07_DUPLICATION_LEDGER.md`      | `TEMPLATE`       | OpenClaw subagent     | Duplicate logic               |
| `08_CONFIG_FLOW_MAP.md`         | `TEMPLATE`       | OpenClaw orchestrator | Config flow                   |
| `09_SCIENTIFIC_CONTRACT_MAP.md` | `TEMPLATE`       | OpenClaw orchestrator | Science invariant map         |
| `10_REFACTOR_BACKLOG.md`        | `TEMPLATE`       | OpenClaw orchestrator | Evidence-backed backlog       |
| `13_TEST_RUNS.md`               | `TEMPLATE`       | OpenClaw subagent     | Safe commands                 |
| `14_DRIFT_GATES.md`             | `READY_TEMPLATE` | OpenClaw orchestrator | Reusable gate                 |
| `15_FINAL_READINESS_REPORT.md`  | `TEMPLATE`       | OpenClaw orchestrator | Final report                  |

## 8. Phase Gates

### Gate A — Documentation Initialization

Required before read-only inventory:

| Check                      | Status         |
| -------------------------- | -------------- |
| Workspace exists           | `TO_BE_FILLED` |
| Agent docs exist           | `TO_BE_FILLED` |
| Inventory templates exist  | `TO_BE_FILLED` |
| Drift gate template exists | `TO_BE_FILLED` |
| Source code untouched      | `TO_BE_FILLED` |
| Tests untouched            | `TO_BE_FILLED` |
| Experiments not run        | `TO_BE_FILLED` |

### Gate B — Read-Only Inventory

Required before implementation planning:

| Check                             | Status    |
| --------------------------------- | --------- |
| File index populated              | `PENDING` |
| Symbol index populated            | `PENDING` |
| Method IO index populated         | `PENDING` |
| Dataclass/enum index populated    | `PENDING` |
| Type-debt ledger populated        | `PENDING` |
| Hardcoded-values ledger populated | `PENDING` |
| Duplication ledger populated      | `PENDING` |
| Config flow map populated         | `PENDING` |
| Scientific contract map populated | `PENDING` |
| Test command registry populated   | `PENDING` |

### Gate C — Refactor Backlog

Required before code changes:

| Check                                       | Status    |
| ------------------------------------------- | --------- |
| Backlog generated from evidence             | `PENDING` |
| Backlog dependency order reviewed           | `PENDING` |
| Drift risks mapped per ticket               | `PENDING` |
| Tests required per ticket                   | `PENDING` |
| Hermes or equivalent harsh review completed | `PENDING` |

### Gate D — Implementation

Required for each future patch:

| Check                         | Status    |
| ----------------------------- | --------- |
| One bounded patch plan exists | `PENDING` |
| One backlog item selected     | `PENDING` |
| Tests identified              | `PENDING` |
| Drift gate selected           | `PENDING` |
| Rollback plan exists          | `PENDING` |

## 9. Current Next Step

Next recommended phase:

`READ_ONLY_INVENTORY_POPULATION`

Recommended next orchestrator:

`OpenClaw / Copilot Sonnet`

Recommended next action:

Populate the inventory files using bounded OpenClaw subagents. Do not edit source code yet.

## 10. Notes

Use this file as the campaign state anchor.

Every agent should read this file before starting work.

Every phase transition should update this file.
