# Multi-Agent Refactor Workspace

## 1. Purpose

This directory coordinates the multi-agent refactor campaign for the DATP CP2 calibration-poisoning repository.

The campaign is designed to improve code quality without causing scientific drift.

The campaign has two simultaneous goals:

| Goal                       | Meaning                                                                                   |
| -------------------------- | ----------------------------------------------------------------------------------------- |
| Refactor-first engineering | Replace weak, duplicated, stringly typed, or hardcoded code with explicit typed contracts |
| Scientific safety          | Preserve the locked CP2 calibration-channel poisoning protocol                            |

This workspace is the shared memory for all agents.

No agent should rely on chat history or private memory.

## 2. Orchestration Model

OpenClaw / Copilot Sonnet is the planned durable orchestrator.

Claude Code Sonnet, Codex CLI, Hermes / DeepSeek Pro, and OpenClaw subagents are specialist workers or reviewers.

| Agent                     | Role                                              |
| ------------------------- | ------------------------------------------------- |
| OpenClaw / Copilot Sonnet | Durable orchestrator                              |
| OpenClaw subagents        | Bounded read-only inventory and audit workers     |
| Claude Code Sonnet        | Bounded implementation and integration specialist |
| Codex CLI                 | Code-aware refactor and test-diagnosis specialist |
| Hermes / DeepSeek Pro     | Harsh scientific and architectural reviewer       |

The orchestrator owns task flow, not scientific authority. Scientific authority comes from the locked protocol and evidence recorded in this workspace.

## 3. Universal Agent Rules

Every agent must follow these rules.

### 3.1 Before Working

An agent must read:

1. `.refactor_loop/00_LOOP_STATE.md`
2. `.refactor_loop/agents/README.md`
3. `.refactor_loop/agents/TASK_BOARD.md`
4. `.refactor_loop/agents/BLOCKERS.md`
5. The output file for the task it wants to perform

### 3.2 Claiming Work

Before starting, the agent must:

1. Select one task from `TASK_BOARD.md`.
2. Confirm dependencies are satisfied.
3. Add an entry to `LOCKS.md`.
4. Mark the task as `CLAIMED` or `IN_PROGRESS`.
5. Work only on that task.

### 3.3 During Work

The agent must:

1. Write findings to the required output file.
2. Record uncertainty explicitly.
3. Avoid overwriting another agent’s work.
4. Record blockers immediately.
5. Avoid broad edits.
6. Stop when the defined stop condition is reached.

### 3.4 After Work

The agent must:

1. Update `SESSION_LOG.md`.
2. Release its lock in `LOCKS.md`.
3. Update task status in `TASK_BOARD.md`.
4. Record quota issues if relevant.
5. Record decisions if any were made.
6. Request review when required.

## 4. Task States

Use only these task states.

| State               | Meaning                                     |
| ------------------- | ------------------------------------------- |
| `TODO`              | Not started                                 |
| `CLAIMED`           | Agent has claimed task but not started      |
| `IN_PROGRESS`       | Agent is actively working                   |
| `REVIEW_REQUESTED`  | Work is done and needs review               |
| `REVIEWED`          | Review completed                            |
| `BLOCKED`           | Cannot proceed without decision or fix      |
| `DONE`              | Complete and accepted                       |
| `PARKED_QUOTA`      | Paused because quota or usage limit was hit |
| `PARKED_DEPENDENCY` | Paused because dependency is missing        |

Do not invent new task states.

## 5. Source Edit Policy

### 5.1 Documentation Initialization Phase

Allowed:

1. Create or update files under `.refactor_loop/`.
2. Record coordination rules.
3. Record templates.
4. Record task structure.

Forbidden:

1. Editing source code.
2. Editing tests.
3. Running experiments.
4. Running training.
5. Committing.
6. Running mutating formatters.
7. Writing outputs outside `.refactor_loop/`.

### 5.2 Read-Only Inventory Phase

Allowed:

1. Inspect repository files.
2. Use safe read-only commands.
3. Populate inventory files.
4. Populate ledgers.
5. Populate maps.
6. Populate safe test command registry.

Forbidden:

1. Editing source code.
2. Editing tests.
3. Running experiments.
4. Committing.
5. Applying refactors.
6. Auto-formatting files.
7. Rewriting generated inventories without preserving prior findings.

### 5.3 Implementation Phase

Implementation may begin only after:

1. Inventories are populated.
2. The refactor backlog is evidence-backed.
3. Scientific contract map is populated.
4. Test command registry is populated.
5. Backlog has been reviewed.
6. A patch plan exists for the selected ticket.

Implementation rules:

1. One bounded ticket at a time.
2. One patch plan per ticket.
3. Tests updated with code.
4. Scientific drift gate after every patch.
5. No unrelated cleanup.
6. No broad rewrites.
7. No experiment launch unless explicitly requested.

## 6. Locked Refactor Direction

The future refactor should move the codebase toward:

| Problem                        | Direction                                 |
| ------------------------------ | ----------------------------------------- |
| Raw strings for domain choices | Enums                                     |
| Loose configs                  | Dataclasses                               |
| Runtime dicts                  | Dataclasses                               |
| JSON-like domain payloads      | Boundary-only parsing                     |
| Scattered constants            | Central constants/config                  |
| Duplicate threshold logic      | One canonical threshold owner             |
| Duplicate poisoning logic      | One canonical attack owner                |
| Duplicate metrics logic        | One canonical metrics owner               |
| Duplicate manifest logic       | One canonical provenance owner            |
| Optional config where required | Required config with fail-fast validation |
| `Any` in core code             | Remove                                    |
| `object` in core code          | Remove                                    |
| Broad `isinstance` chains      | Replace with typed contracts              |
| Silent coercion                | Replace with explicit validation          |
| `type: ignore`                 | Remove unless documented as unavoidable   |

## 7. Scientific Contract

CP2 is calibration-channel poisoning only.

Refactor work must preserve:

| Invariant              | Required state                                                                                          |
| ---------------------- | ------------------------------------------------------------------------------------------------------- |
| Poisoning location     | Benign threshold-calibration channel only                                                               |
| Training data          | Clean                                                                                                   |
| Model weights          | Clean                                                                                                   |
| FedAvg aggregation     | Clean                                                                                                   |
| Test scores and labels | Clean                                                                                                   |
| Clean artifacts        | Read-only reuse                                                                                         |
| Primary dataset        | N-BaIoT                                                                                                 |
| Artifact compatibility | E=1 only for conference-faithful reuse                                                                  |
| Default policies       | B1_GLOBAL, B2_PERSONALIZED, B4_CLUSTER                                                                  |
| Pairing                | Clean and poisoned paired by training_seed and victim plan                                              |
| Randomness             | Poisoning is sole stochastic difference                                                                 |
| Scope                  | No journal, privacy, deployment, evasion, training-poisoning, model-poisoning, or test-poisoning claims |

## 8. B4 Contract

B4 must remain the locked CP2/DATP clustering threshold policy.

Required:

1. K is 3 for Regime A.
2. Random state is 42.
3. k-means++ parameters are locked through config/constants.
4. Threshold deltas are client-effective deltas.
5. Raw k-means label IDs are not compared across runs.
6. Churn and aggregation decomposition are recorded as client-indexed threshold effects.
7. Any refactor touching B4 must run a B4-specific drift gate.

## 9. Quota and Availability Policy

If Claude Code quota is hit:

1. Mark task `PARKED_QUOTA`.
2. Record in `QUOTA_USAGE.md`.
3. Add resume note in `CLAUDE_CODE_HANDOFF.md`.
4. Continue with OpenClaw-owned tasks.

If Codex quota is hit:

1. Mark task `PARKED_QUOTA`.
2. Record in `QUOTA_USAGE.md`.
3. Add resume note in `CODEX_HANDOFF.md`.
4. Continue with OpenClaw or Claude Code if available.

If Hermes usage is high:

1. Stop using Hermes for routine checks.
2. Reserve Hermes for scientific drift and architecture review.
3. Record usage in `QUOTA_USAGE.md`.

The campaign must never depend on one quota-limited agent being available.

## 10. Review Policy

A review is required when:

1. A backlog is synthesized.
2. A patch plan touches scientific logic.
3. A patch touches attack, threshold, B4, artifact, manifest, metrics, or runner code.
4. A drift gate returns `UNCLEAR`.
5. A task proposes removing or merging a contract.
6. A task changes config flow.
7. A task changes test expectations.

Hermes is preferred for harsh scientific review. Claude Code may review implementation details. OpenClaw reviews task consistency.

## 11. Blocker Policy

Record blockers in `BLOCKERS.md`.

A blocker must include:

1. Task ID.
2. Severity.
3. Affected files.
4. Scientific risk.
5. Engineering risk.
6. Required decision.
7. Owner.
8. Status.

Critical blockers stop implementation.

Inventory can continue around non-critical blockers if independent.

## 12. Decision Policy

Record decisions in `DECISIONS.md`.

A decision is required when:

1. A typed contract is merged, split, or renamed.
2. A config object becomes canonical.
3. A backward-compatibility exception is allowed.
4. A hardcoded value remains intentionally.
5. A scientific invariant cannot be enforced directly.
6. A test is accepted as sufficient for a scientific invariant.
7. A task is deferred.

## 13. Session Logging

Every agent session must update `SESSION_LOG.md`.

Each session entry must include:

1. Agent.
2. Task ID.
3. Files read.
4. Files written.
5. Commands run.
6. Summary.
7. Blockers.
8. Next action.
9. Whether source files were modified.
10. Whether tests were modified.
11. Whether experiments were run.

## 14. Current Recommended Next Step

Next step:

Populate read-only inventories using OpenClaw as orchestrator and OpenClaw subagents where useful.

Do not implement yet.
