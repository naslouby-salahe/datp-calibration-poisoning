# .rework — datp-cp repository rework workspace

This folder tracks the full repository rework from the old DATP/CP2 naming to the
clean `datp-cp` contract defined in `docs/DATP_CP_Roadmap.md`.

## Files

| File | Purpose |
|------|---------|
| STATUS.md | Per-phase completion status |
| ROADMAP_CONTRACT.md | Extracted contract from new roadmap |
| CODE_INVENTORY.md | All source modules, enums, tests, CLI, etc. |
| OBSOLETE_TERMS_AUDIT.md | Every obsolete active term found |
| RENAME_PLAN.md | What gets renamed to what |
| REMOVAL_PLAN.md | What gets deleted |
| TEST_PLAN.md | Tests to remove, rewrite, add |
| SCIENTIFIC_AUDIT.md | Scientific-lock compliance audit |
| CODE_AUDIT.md | Type safety / quality audit |
| DOCS_AUDIT.md | Documentation audit |
| CLAUDE_FOLDER_AUDIT.md | .claude agents/skills audit |
| MAKEFILE_AUDIT.md | Makefile targets audit |
| DECISIONS.md | Ambiguity resolution decisions |
| FINAL_REPORT.md | End-state report |

## Process

Phases are executed sequentially. Each phase updates STATUS.md before and after.
If restarted, read STATUS.md and resume from the last incomplete phase.
