# TASK_BOARD.md — Refactor Loop Task Board

Live task state. OpenClaw is the only agent that may move tasks between states.

Status values: `TODO` | `IN_PROGRESS` | `DONE` | `BLOCKED` | `CANCELLED`

---

## DOC-INIT-001 — Initialize refactor-loop documentation

| Field | Value |
|---|---|
| Status | DONE |
| Priority | CRITICAL |
| Recommended agent | Claude Code Sonnet (initialization) |
| Fallback agent | OpenClaw |
| Dependencies | none |
| Output file | `.refactor_loop/00_LOOP_STATE.md` |
| Review requirement | NO |
| Quota sensitivity | LOW |
| Stop condition | All scaffold files created and checklist in `00_LOOP_STATE.md` complete |

---

## INV-001 — Populate file index

| Field | Value |
|---|---|
| Status | TODO |
| Priority | HIGH |
| Recommended agent | OpenClaw subagent |
| Fallback agent | Claude Code Sonnet |
| Dependencies | DOC-INIT-001 |
| Output file | `.refactor_loop/01_FILE_INDEX.md` |
| Review requirement | NO |
| Quota sensitivity | LOW |
| Stop condition | Every `src/` file listed with module path, role, and primary exports |

---

## INV-002 — Populate symbol index

| Field | Value |
|---|---|
| Status | TODO |
| Priority | HIGH |
| Recommended agent | OpenClaw subagent |
| Fallback agent | Claude Code Sonnet |
| Dependencies | INV-001 |
| Output file | `.refactor_loop/02_SYMBOL_INDEX.md` |
| Review requirement | NO |
| Quota sensitivity | MEDIUM |
| Stop condition | All classes, functions, enums, dataclasses in `src/` catalogued |

---

## INV-003 — Populate method input/output index

| Field | Value |
|---|---|
| Status | TODO |
| Priority | HIGH |
| Recommended agent | OpenClaw subagent |
| Fallback agent | Codex CLI |
| Dependencies | INV-002 |
| Output file | `.refactor_loop/03_METHOD_IO_INDEX.md` |
| Review requirement | NO |
| Quota sensitivity | MEDIUM |
| Stop condition | Public method signatures catalogued with parameter types and return types |

---

## INV-004 — Populate dataclass/enum/config index

| Field | Value |
|---|---|
| Status | TODO |
| Priority | HIGH |
| Recommended agent | OpenClaw subagent |
| Fallback agent | Codex CLI |
| Dependencies | INV-002 |
| Output file | `.refactor_loop/04_DATACLASS_ENUM_INDEX.md` |
| Review requirement | NO |
| Quota sensitivity | LOW |
| Stop condition | All dataclasses, enums, Pydantic models, and typed configs catalogued |

---

## DEBT-001 — Populate type-debt ledger

| Field | Value |
|---|---|
| Status | TODO |
| Priority | HIGH |
| Recommended agent | OpenClaw subagent |
| Fallback agent | Codex CLI |
| Dependencies | INV-002 |
| Output file | `.refactor_loop/05_TYPE_DEBT_LEDGER.md` |
| Review requirement | YES — Hermes recommended |
| Quota sensitivity | MEDIUM |
| Stop condition | All `Any`, `dict`, `object`, untyped returns, and loose contracts catalogued |

---

## DEBT-002 — Populate hardcoded-values ledger

| Field | Value |
|---|---|
| Status | TODO |
| Priority | HIGH |
| Recommended agent | OpenClaw subagent |
| Fallback agent | Codex CLI |
| Dependencies | INV-001 |
| Output file | `.refactor_loop/06_HARDCODED_VALUES_LEDGER.md` |
| Review requirement | YES — scientific values must be verified by Hermes |
| Quota sensitivity | LOW |
| Stop condition | All literal numerics, raw policy strings, and magic constants catalogued |

---

## DUP-001 — Populate duplication ledger

| Field | Value |
|---|---|
| Status | TODO |
| Priority | MEDIUM |
| Recommended agent | OpenClaw subagent |
| Fallback agent | Codex CLI |
| Dependencies | INV-002 |
| Output file | `.refactor_loop/07_DUPLICATION_LEDGER.md` |
| Review requirement | NO |
| Quota sensitivity | MEDIUM |
| Stop condition | All structurally duplicated logic identified with file/line evidence |

---

## CONFIG-001 — Populate config flow map

| Field | Value |
|---|---|
| Status | TODO |
| Priority | HIGH |
| Recommended agent | OpenClaw subagent |
| Fallback agent | Claude Code Sonnet |
| Dependencies | INV-003, INV-004 |
| Output file | `.refactor_loop/08_CONFIG_FLOW_MAP.md` |
| Review requirement | YES |
| Quota sensitivity | MEDIUM |
| Stop condition | Full config construction and propagation paths documented from CLI to experiment runners |

---

## SCI-001 — Populate scientific contract map

| Field | Value |
|---|---|
| Status | TODO |
| Priority | CRITICAL |
| Recommended agent | OpenClaw subagent + Hermes review |
| Fallback agent | Claude Code Sonnet |
| Dependencies | INV-003, DEBT-001, DEBT-002 |
| Output file | `.refactor_loop/09_SCIENTIFIC_CONTRACT_MAP.md` |
| Review requirement | YES — Hermes mandatory |
| Quota sensitivity | HIGH |
| Stop condition | All calibration-poisoning, threshold, reservoir, and policy contracts documented with evidence |

---

## TEST-001 — Discover safe test/check commands

| Field | Value |
|---|---|
| Status | TODO |
| Priority | MEDIUM |
| Recommended agent | OpenClaw |
| Fallback agent | Claude Code Sonnet |
| Dependencies | DOC-INIT-001 |
| Output file | `.refactor_loop/13_TEST_RUNS.md` |
| Review requirement | NO |
| Quota sensitivity | LOW |
| Stop condition | Safe unit test commands identified; pyright/ruff commands confirmed; output captured |

---

## BACKLOG-001 — Build initial typed-contract refactor backlog

| Field | Value |
|---|---|
| Status | TODO |
| Priority | HIGH |
| Recommended agent | OpenClaw |
| Fallback agent | Claude Code Sonnet |
| Dependencies | DEBT-001, DEBT-002, DUP-001, CONFIG-001, SCI-001 |
| Output file | `.refactor_loop/10_REFACTOR_BACKLOG.md` |
| Review requirement | YES — Hermes review required before implementation |
| Quota sensitivity | MEDIUM |
| Stop condition | Prioritized backlog with scientific-risk annotation for each item |

---

## REVIEW-001 — Review backlog for scientific drift and architecture risk

| Field | Value |
|---|---|
| Status | TODO |
| Priority | CRITICAL |
| Recommended agent | Hermes / DeepSeek Pro |
| Fallback agent | Claude Code Sonnet (partial review only) |
| Dependencies | BACKLOG-001 |
| Output file | `.refactor_loop/agents/REVIEW_RESULTS.md` |
| Review requirement | NO (this is the review) |
| Quota sensitivity | HIGH — reserve Hermes for this |
| Stop condition | All backlog items reviewed for drift risk; PASS/FAIL/AMEND per item |
