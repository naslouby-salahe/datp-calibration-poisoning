# Input Inventory

**Synthesis run date:** 2026-06-30  
**Lock acquired:** paper_review/.synthesis_lock  
**Protocol:** Deterministic, idempotent rebuild. AUDIT-IDs assigned by lexicographic sort of filenames.

---

## Audit ID Mapping

| AUDIT-ID | Filename | SHA-256 (first 16) | Bytes | Grade | Recommendation | Notes |
|----------|----------|---------------------|-------|-------|----------------|-------|
| AUDIT-01 | Paper Audit 1.md | 72116f2ac091cd35 | 31,559 | 8.0 | borderline/weak-accept | |
| AUDIT-02 | Paper Audit 10.md | a313b19b2324c086 | 767,246 | 7.0 | borderline/weak-reject | URL-embedded; content degraded |
| AUDIT-03 | Paper Audit 2.md | 72116f2ac091cd35 | 31,559 | 8.0 | borderline/weak-accept | IDENTICAL to AUDIT-01 |
| AUDIT-04 | Paper Audit 3.md | 9ef6181358fe79c6 | 55,244 | 6.8 | borderline/weak-accept | |
| AUDIT-05 | Paper Audit 4.md | 0f00ffe492e8a2a4 | 9,536 | 7.8 | weak-accept | Shorter audit |
| AUDIT-06 | Paper Audit 5.md | 755ec5685e879ae3 | 58,712 | 7.8 | weak-accept | |
| AUDIT-07 | Paper Audit 6.md | 755ec5685e879ae3 | 58,712 | 7.8 | weak-accept | IDENTICAL to AUDIT-06 |
| AUDIT-08 | Paper Audit 7.md | 1716837f2fb7623d | 564,556 | 6.7 | weak-reject | URL-embedded; content degraded |
| AUDIT-09 | Paper Audit 8.md | 4d3b7dc1a71da565 | 55,454 | 8.2 | weak-accept/borderline | Most generous |
| AUDIT-10 | Paper Audit 9.md | c3abc4abbb3463b1 | 69,406 | 6.1 | borderline/weak-reject | Most critical |

---

## Duplicate Detection

- **AUDIT-01 ≡ AUDIT-03**: SHA-256 identical (`72116f2a…`). "Paper Audit 1.md" = "Paper Audit 2.md". Treated as two reviewer instances of identical text; findings attributed to both IDs for coverage traceability.
- **AUDIT-06 ≡ AUDIT-07**: SHA-256 identical (`755ec568…`). "Paper Audit 5.md" = "Paper Audit 6.md". Same treatment.

## Content-Degraded Audits

- **AUDIT-02** ("Paper Audit 10.md", 767 KB): Markdown tables had cells occupied by AWS S3 ppl-ai-file-upload URLs. Recoverable content: overall grade (7.0/10), top weaknesses including Contributions§3 vs §4.2/§5.4 spillover contradiction, Cluster under-specification, gate constants unjustified, spillover not tabulated.
- **AUDIT-08** ("Paper Audit 7.md", 565 KB): Same URL embedding. Recoverable content: grade 6.7/10, "weak reject / paper not ready for strong conference," realism gap near-fatal, narrow external validity, novelty defense incomplete.

## Grade Distribution

| Grade | Count | AUDIT-IDs |
|-------|-------|-----------|
| 8.2 | 1 | AUDIT-09 |
| 8.0 | 2 | AUDIT-01, AUDIT-03 (identical) |
| 7.8 | 2 | AUDIT-05, AUDIT-06 (AUDIT-07 dup) |
| 7.0 | 1 | AUDIT-02 |
| 6.8 | 1 | AUDIT-04 |
| 6.7 | 1 | AUDIT-08 |
| 6.1 | 1 | AUDIT-10 |

**Grade spread:** 6.1 – 8.2.  **Mean (unique audits, excl. dups):** ~7.3.  **Median:** 7.8.

## Paper and Protocol Inputs

- **Paper source:** `paper/main.tex` + `paper/sections/` (7 sections), `paper/tables/` (3 tables), `paper/references.bib`
- **Compiled PDF:** `paper/main.pdf`
- **Protocol/Roadmap:** `docs/DATP_CP_Roadmap.md`

---
*See `INPUT_MANIFEST.csv` for machine-readable version.*
