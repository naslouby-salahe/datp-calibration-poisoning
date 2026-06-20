# HERMES_HANDOFF.md — Handoff Template for Hermes / DeepSeek Pro

Hermes / DeepSeek Pro is a **review-only** specialist. It does not implement code.
It performs harsh scientific and architectural critique, and its findings must be
addressed before any implementation loop proceeds.

---

## Hermes's Role in This Campaign

- Scientific drift gate review
- Architecture critique of proposed refactors
- Typed-contract critique (are the proposed contracts scientifically correct?)
- Backlog review (REVIEW-001 — mandatory before implementation)
- Claims-scope review (are any refactors inadvertently expanding scope?)
- Final readiness review (before `15_FINAL_READINESS_REPORT.md` is signed off)

Hermes does not write code. Hermes does not run experiments.
Hermes does not modify any files other than its review output files.

---

## Usage Guidelines

Hermes usage should be reserved for high-value review tasks. Record every invocation in
`agents/QUOTA_USAGE.md`. Do not invoke Hermes for routine inventory tasks.

Recommended invocations:
1. Review of `09_SCIENTIFIC_CONTRACT_MAP.md` after SCI-001 completes.
2. Review of `10_REFACTOR_BACKLOG.md` (REVIEW-001 — mandatory before implementation).
3. Drift gate review after each implementation loop.
4. Final readiness review at campaign completion.

---

## Review Request Format

Write a review request to `agents/REVIEW_REQUESTS.md` before invoking Hermes:

```
## REVIEW-REQ-<ID>
- Date: <ISO timestamp>
- Requested by: <agent>
- Assigned to: Hermes / DeepSeek Pro
- Task: <task ID>
- Input files: <list of files Hermes should read>
- Questions to answer:
  1. <specific question>
  2. <specific question>
- Scientific locks to verify: <list from CLAUDE.md §3>
- Output file: agents/REVIEW_RESULTS.md
- Priority: HIGH | CRITICAL
```

---

## Review Output Format

Hermes writes findings to `agents/REVIEW_RESULTS.md`:

```
## REVIEW-RES-<ID>
- Date: <ISO timestamp>
- Task: <task ID>
- Reviewer: Hermes / DeepSeek Pro
- Overall verdict: PASS | FAIL | AMEND

### Per-Item Findings
| Item | Verdict | Reason | Risk |
|---|---|---|---|
| <backlog item or contract element> | PASS/FAIL/AMEND | <reason> | LOW/MEDIUM/HIGH/CRITICAL |

### Drift Risk Summary
<overall assessment of scientific drift risk>

### Architectural Concerns
<structural or contract-level concerns>

### Claims-Scope Concerns
<any refactors that could inadvertently introduce new claims>

### Mandatory Changes Before Implementation
<list — all items here must be resolved before implementation begins>

### Optional Improvements
<lower-priority suggestions>
```

---

## Known Review Requests

*(append entries below as they occur)*
