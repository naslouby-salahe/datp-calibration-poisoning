# CP2 Graphify Status

**Last checked:** 2026-06-15 (Phase 00 refresh)
**State:** AVAILABLE

---

## Installation record

| Step | Command | Result |
|---|---|---|
| 1 | `graphify --version` | not found |
| 2 | `uv --version` | uv 0.11.1 ✓ |
| 3 | `uv tool install graphifyy` | graphifyy==0.8.39 installed ✓ |
| 4 | `graphify --version` | graphify 0.8.39 ✓ |
| 5 | `graphify install` | skill installed for Claude ✓ |
| 6 | `graphify install --platform copilot` | skill installed for Copilot ✓ |
| 7 | `graphify update .` | 6229 nodes, 15572 edges, 406 communities ✓ |

## Output layout

- `graphify-out/graph.json` — full graph (6331 nodes)
- `graphify-out/GRAPH_REPORT.md` — community report (397 communities)
- HTML viz skipped (6331 nodes > 5000 limit)
- Built from commit: `27c1dc31`

## Canonical invocation

```bash
cd /home/naslouby/Projects/datp-calibration-poisoning
graphify update .    # code-only (no API key needed)
graphify .           # + LLM semantic extraction (requires GEMINI_API_KEY etc.)
```

Refresh after major refactors, package moves, or scope changes.

## Graphify in tickets

Graphify is now **available**. Tickets should run `graphify update .` where
their Graphify section says "Run if available". The code-only update needs
no API key.

For LLM-powered community naming (to replace "Community N" placeholders with
meaningful names), set `GEMINI_API_KEY` or another supported backend key.

---

## Run log

```
2026-06-15 | CP2-T004 | installed | uv tool install graphifyy → 0.8.39; initial graph: 6229 nodes, 15572 edges, 406 communities
2026-06-15 | CP2-T005 | refreshed | graphify --version → 0.8.39; graphify update . → 6298 nodes, 15638 edges, 407 communities
2026-06-15 | CP2-T005 | refreshed after sidecar cleanup | graphify update . → 6331 nodes, 15668 edges, 397 communities
```
