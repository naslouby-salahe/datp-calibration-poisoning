# Docs and .claude Folder Audit — datp-cp

Audit of README.md, CLAUDE.md, docs/, and .claude/ for canonical terminology and accuracy.

---

## Verdict

Not yet audited.

---

## Required README.md Content

    Project name: datp-cp
    Installation instructions
    Makefile workflow: make help, make check, make datp-cp-smoke, make datp-cp-dry-run, make datp-cp-run, make datp-cp-report
    Data requirements
    Reproducibility notes (seeds, environment)
    No obsolete terminology

## Required CLAUDE.md Content

    Repository overview for Claude
    Project name: datp-cp
    Canonical threshold policies: GLOBAL_THRESHOLD, LOCAL_THRESHOLD, CLUSTER_THRESHOLD
    Canonical experiment stages
    No commits, no PRs
    Scientific boundaries
    Code quality rules
    No obsolete terminology

## Required .claude/ Content

    agents/ — if present, must use only canonical datp-cp names
    commands/ — if present, must invoke only canonical Makefile targets
    skills/ — if present, must be consistent with datp-cp roadmap

---

## Forbidden in README, CLAUDE.md, .claude/

    Regime A/B/C/D
    B1/B2/B3/B4 visible to users
    CP2, MVP, Phase E labels
    Old Makefile target names
    Journal-extension scope descriptions

---

## Findings

### Status: not yet audited

Agents: inspect docs:

    grep -RIn -E "Regime|B1|B2|B3|B4|CP2|MVP|Phase E" README.md CLAUDE.md .claude/ 2>/dev/null

Write findings here and create CLAUDE tasks for violations.
