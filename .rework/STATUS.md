# datp-cp Rework Status

Status: prompt pack v2 written -- ready for Hermes bootstrap.

Last updated: 2026-06-21

---

## Orchestration System

Hermes orchestrates:
- Claude Code -- full implementer + reviewer (equal to Codex)
- Codex CLI -- full implementer + reviewer (equal to Claude)
- OpenClaw on Sonnet -- review-only auditor

Claude and Codex are equal peers. Hermes assigns tasks to either based on
availability, quota, file conflict risk, and task suitability.

Entry point:

    .rework/prompts/HERMES_MASTER_ORCHESTRATION.md

---

## Canonical project name

datp-cp  (Python-safe: datp_cp / DatpCp)

---

## Canonical experiment stages

- SYNTHETIC_SMOKE
- NBAIOT_MAIN
- CICIOT_STRETCH
- FINAL_AUDIT

---

## Canonical threshold policies

- GLOBAL_THRESHOLD
- LOCAL_THRESHOLD
- CLUSTER_THRESHOLD

---

## Public Makefile workflow

- make help
- make check
- make datp-cp-clean
- make datp-cp-smoke
- make datp-cp-dry-run
- make datp-cp-run
- make datp-cp-report
- make clean

---

## Implementation status

Code cleanup: not started
Enum/dataclass alignment: not started
Test alignment: not started
Makefile alignment: not started
Docs alignment: not started
Execution: not started
Paper: not started

---

## Last agent actions

None -- awaiting first Hermes session.

---

## Next action

Hermes reads .rework/prompts/HERMES_MASTER_ORCHESTRATION.md and follows it.

No commits. No PRs.
