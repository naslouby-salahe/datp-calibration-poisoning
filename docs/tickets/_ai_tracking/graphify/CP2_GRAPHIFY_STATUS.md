# CP2 Graphify Status

**Status:** ✅ AVAILABLE
**Tool:** `graphify 0.8.39` (graphifyy), installed 2026-06-15 via `uv tool install graphifyy`
**Registered:** Claude + Copilot platforms; VS Code integration
**Output:** `graphify-out/graph.json` + `graphify-out/GRAPH_REPORT.md`

---

## 1. Canonical invocation (CP2 default — no API key)

```bash
graphify update .
```

Optional LLM-enriched mode (requires an API key such as `GEMINI_API_KEY`; **not**
the CP2 default):

```bash
graphify .
```

## 2. Current graph

- Existing graph: **6331 nodes · 15668 edges · 397 communities** (per
  `graphify-out/GRAPH_REPORT.md`), built from commit `27c1dc31`.
- Current repo HEAD: `0a5e380`. The graph is slightly behind HEAD but Phase 00
  changed **docs/config only** (no `src/` change), so code structure is unchanged.
- HTML visualization skipped (node count > 5000 limit).

## 3. CP2-T004 / Phase 00 refresh attempt (2026-06-15)

```
graphify update .
  AST extraction: 404/404 files (100%) [6 workers]
  WARNING: new graph has 6253 nodes but existing graph.json has 6331.
  Refusing to overwrite — you may be missing chunk files from a previous session.
  Pass --force to override.
```

**Decision:** **not** forced. The code-only AST pass yields 6253 nodes vs the
existing 6331; graphify refused the overwrite to avoid dropping chunk data from a
prior (richer) session. Forcing could destroy useful graph content for no Phase 00
benefit (docs-only changes). The existing 6331-node graph is **retained** as the
reference. This is a documented, honest deferral of the overwrite, not a hard-stop.

**Re-evaluation trigger:** rebuild/refresh after the first real `src/` change
(Phase B onward). At that point, if the AST pass exceeds or matches the existing
node count, a normal `graphify update .` will overwrite cleanly; otherwise
investigate the missing chunk files before using `--force`.

## 4. Fallback policy

Graphify findings are **accelerators, not proof** — verify with `rg`, code
inspection, `ruff`, `pyright`, `pytest`. If a future `graphify update .` cannot run,
record the exact blocker here and switch to those fallbacks. Graphify being
unavailable is **not** a project hard-stop.

## 6. CP2-T016 Graphify Run (2026-06-16)

```
graphify update .
  AST extraction: 6484 nodes, 15894 edges, 416 communities (rebuilt)
```

**Decision:** Overwrite succeeded (6484 > 6365). Graph reflects cp2_enums.py addition
and quarantined-file enum retirement. HTML viz skipped (>5000 nodes).

---

## 5. CP2-T013 Graphify Run (2026-06-16)

```
graphify update .
  AST extraction: 414/414 files (100%)
  Rebuilt: 6365 nodes, 15697 edges, 413 communities
  graph.json and GRAPH_REPORT.md updated in graphify-out
```

**Decision:** Overwrite succeeded (6365 > 6331; no chunk data lost). Graph now
reflects current repo state for the upcoming Phase B protocol lock. HTML viz
skipped (>5000 nodes). No API key used.

---

## 6. Per-ticket usage

Each ticket either runs `graphify update .` (where code structure changed) or
records a deferral with reason. Docs-only Phase 00 tickets (T000–T003, T005–T006)
defer with reason; T004 (this file) is the discovery/workflow record.

---

## 7. CP2-T036 Graphify Run (2026-06-16)

```
graphify update .
  AST extraction: 453/453 files (100%)
  Rebuilt: 7381 nodes, 18465 edges, 458 communities
  graph.json and GRAPH_REPORT.md updated in graphify-out
```

**Context:** End-of-Phase-C consolidation checkpoint. Phase C added 9 new modules
(synthetic_scores, score_containers, reservoir, injector, source_strategies,
threshold_recompute, b4_recompute, metric_engine, diagnostics, inference, run_logger)
and removed 3 quarantined prototype modules. Node count grew from 6365 → 7381.
HTML viz skipped (>5000 nodes). No API key used.

---

## 8. CP2-T038–T041 Graphify Run (2026-06-16, Phase D)

```
graphify update .
  AST extraction: 457/457 files (100%)
  Rebuilt: 7479 nodes, 18740 edges, 446 communities
  graph.json and GRAPH_REPORT.md updated in graphify-out
```

**Context:** Phase D smoke validation. Added the synthetic smoke harness
(`src/datp/testsupport/cp2_smoke_harness.py`) and the invariant suite
(`tests/integration/attacks/test_cp2_smoke.py`). Node count 7381 → 7479. HTML viz
skipped (>5000 nodes). No API key used.
