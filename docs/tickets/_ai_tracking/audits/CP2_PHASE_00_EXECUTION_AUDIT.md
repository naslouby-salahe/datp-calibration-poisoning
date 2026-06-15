# CP2 Phase 00 Execution Audit

**Date:** 2026-06-15  
**Scope:** CP2-T000 through CP2-T005, with CP2-T003/CP2-T004 evidence verification  
**Repository:** `/home/naslouby/Projects/datp-calibration-poisoning`

This audit records the Phase 00 setup execution evidence. It is not a substitute
for the Phase A read-only scientific/code audit.

## 1. Pre-Start Repository and Ticket-Tree Audit

### Ticket tree

Commands:

```bash
find docs/tickets -maxdepth 3 -type f | sort
find docs/tickets -maxdepth 2 -type d | sort
python - <<'PY'
from pathlib import Path
import re
idx = Path('docs/tickets/TICKET_INDEX.md').read_text()
tickets = sorted(set(re.findall(r'CP2-T\d{3}', idx)))
fb = sorted(set(re.findall(r'CP2-FB\d', idx)))
print('numbered_count', len(tickets))
print('first', tickets[:3], 'last', tickets[-3:])
print('missing', [f'CP2-T{i:03d}' for i in range(59) if f'CP2-T{i:03d}' not in tickets])
print('fallbacks', fb)
PY
```

Findings:

- Phase folders exist from `phase_00_setup/` through
  `phase_g_experiment_and_paper/`.
- Tracking folders exist under `_ai_tracking/`: `audits/`, `decisions/`,
  `diagnostics/`, `graphify/`, `manifests/`, `paper_notes/`, `progress/`,
  and `run_logs/`.
- `TICKET_INDEX.md` contains 59 numbered tickets, `CP2-T000` through
  `CP2-T058`, with no missing numbered IDs.
- Fallbacks present: `CP2-FB1`, `CP2-FB2`, `CP2-FB3`, `CP2-FB4`.
- Final numbered tickets are correctly fixed as `CP2-T056` experiment,
  `CP2-T057` analysis, and `CP2-T058` paper.

Verdict for CP2-T000: **done**.

## 2. Repository Inventory Refresh

Commands:

```bash
find src/datp tests -maxdepth 3 -type f | sort
make help
rg -n "class PoisoningObjective|shift_magnitude|attack_rate|poison_calibration_errors|CalibrationPoisoningConfig|PoisoningEffect" \
  src/datp/attacks src/datp/experiments tests/unit/attacks tests/integration/attacks
rg -n "class Baseline|B1|B2|B3|B4|bootstrap_ci|bca_ci|cv\(|Fingerprint|KMeans|random_state|n_init|max_iter|SCORE_COLUMN|calibration" \
  src/datp/core src/datp/thresholding src/datp/statistics src/datp/scoring
```

Findings:

- Current attack prototype files remain:
  - `src/datp/attacks/calibration_poisoning.py`
  - `src/datp/attacks/poisoning_config.py`
  - `src/datp/attacks/poisoning_metrics.py`
  - `src/datp/experiments/calibration_poisoning.py`
- The prototype still uses `attack_rate` and `shift_magnitude` and therefore
  remains non-protocol CP2 code. This confirms, rather than changes, the existing
  `CP2_INITIAL_REPO_AUDIT.md` finding.
- Reusable DATP substrate remains present in `thresholding`, `scoring`,
  `statistics`, `validation`, `reporting`, and `core`.
- `src/datp/thresholding/thresholds.py` still contains `conformal_threshold()`.
  This is inherited DATP/journal-context code; it is not introduced or activated
  by Phase 00 and remains out of CP2 scope unless a future ticket explicitly
  audits/quarantines it.
- `make help` enumerated the expected lightweight checks plus heavy real-data
  experiment targets. No heavy target was run.

Verdict for CP2-T001: **done**. Existing initial audit remains substantively
current; a refresh addendum was appended there.

## 3. CP2-T003 Evidence Verification

Inspected:

- `CLAUDE.md`
- `.github/copilot-instructions.md`
- `.claude/settings.json`
- `.claude/agents/orchestrator-agent.md`
- `.claude/agents/scientific-contract-agent.md`
- `.claude/agents/drift-enforcer-agent.md`
- `.claude/agents/code-quality-gate-agent.md`
- `.claude/agents/ticket-completion-auditor-agent.md`
- `.claude/agents/reviewer-agent.md`
- `.claude/skills/datp-invariant-check-skill.md`
- `.claude/skills/ticket-progress-skill.md`
- `.claude/skills/ticket-audit-skill.md`
- `.claude/skills/ticket-completion-audit-skill.md`
- `.claude/skills/static-analysis-quality-gate-skill.md`
- `.claude/skills/refactor-clean-code-skill.md`

Findings:

- `CLAUDE.md` exists and correctly identifies CP2 as the active project.
- `.github/copilot-instructions.md` has a CP2-active preface that points to
  `docs/DATP_CP_Roadmap.md`, `TICKET_INDEX.md`, `CP2_PROGRESS.md`, the decision
  log, paper notes, and Graphify status.
- `.claude/settings.json` includes `Bash(graphify:*)`.
- The inspected relevant agents/skills contain CP2 path and lock guidance.
- `.claude/agents/implementation-agent.md` exists in the current repository tree.
  Historical audit/update references to that file are valid as path references;
  CP2 root guidance and the available relevant agents cover the active setup
  workflow.

Verdict for CP2-T003: **done, verified**. No redo or config edit was necessary.

## 4. CP2-T004 Evidence Verification

Commands:

```bash
graphify --version
graphify update .
```

Outcome:

- `graphify --version` returned `graphify 0.8.39`.
- `graphify update .` completed successfully.
- Refreshed graph: 6298 nodes, 15638 edges, 407 communities.
- After sidecar instruction cleanup, Graphify was refreshed again:
  6331 nodes, 15668 edges, 397 communities.
- HTML visualization was skipped because the graph exceeds the 5000-node default
  limit.
- `docs/tickets/_ai_tracking/graphify/CP2_GRAPHIFY_STATUS.md` was updated with
  the refresh.

Verdict for CP2-T004: **done, verified**.

## 5. Setup Consistency Checkpoint

Commands:

```bash
rg -n "CP2-T000|CP2-T058|CP2-FB|DATP_CP_Roadmap|CP2_PROGRESS|TICKET_INDEX|Graphify|graphify" \
  docs CLAUDE.md .github .claude
rg -ni "Edge-IIoTset|FedProx|Ditto|FedRep|FedPer|Laridi|B-FedStatsBenign|conformal|temporal|E=5|shift_magnitude" \
  docs src tests CLAUDE.md .github .claude
git status --short
```

Findings:

- CP2 path references are present in root and agent instructions.
- Forbidden-scope terms in Phase 00 docs are in forbid, boundary, fallback, or
  future-ticket audit contexts, not active CP2 scope expansion.
- `shift_magnitude` remains in the legacy prototype and its tests, matching the
  Phase A/C tickets that will audit and replace it.
- `git status --short` was clean before Phase 00 doc edits.
- No production code changes were made.
- Sidecar subagent findings led to minimal CP2-routing cleanup in
  `.github/copilot-instructions.md`, `.claude/agents/orchestrator-agent.md`, and
  `.claude/skills/ticket-progress-skill.md`; DATP journal paths remain only as
  explicitly labelled fallback context.

Static-check sampling:

```bash
python -m ruff check src/datp --select E,F
pyright
```

Outcome:

- Ruff failed with 343 pre-existing diagnostics across source files:
  342 `E501` line-length findings and one `F401` unused import in
  `src/datp/experiments/calibration_poisoning.py`. No Phase 00 source edits
  caused these diagnostics.
- Pyright exited 0 with `0 errors, 0 warnings, 0 informations`, while also
  printing that `src/datp/baselines` does not exist. This appears to come from
  existing pyright configuration and is not a Phase 00 regression.

Verdict for CP2-T005: **done**. No blocker for Phase A because Phase 00 changed
only docs/tracking and Graphify metadata.

## 6. Subagent Availability

Subagent tooling was available and used for read-only sidecar checks:

- T003/T004 evidence verification.
- Phase 00 drift and forbidden-scope scan.

Their findings are integrated into the final Phase 00 readiness report.
