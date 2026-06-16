# CP2-T054 — CICIoT2023 Stretch Pre-Audit (Feasibility Gate)

**Date:** 2026-06-16
**Type:** scientific-feasibility-audit (read-only)
**Gate:** CP2-T049 = CONTINUE (Phase F open for implementation); execution
remains gated at CP2-T056.
**Verdict:** **INFEASIBLE-NOW (DEFERRED)** — see §5.
**FB4 gating state:** **NOT TRIGGERED** (CICIoT2023 stretch not feasible under
current artifacts/gate; B4 K-stability trigger also not fired).

---

## 1. Scope of this audit

Determine whether a protocol-faithful calibration-poisoning experiment on the
CICIoT2023 stretch regime is currently possible, **before** any stretch run.
This is read-only: no preprocessing, training, scoring, or poisoning was run
(none is authorized before CP2-T056). The check covers the five inputs named in
CP2-T054 §4: artifact availability, provenance (E=1, control origin),
pseudo-client semantics, eligibility counts, reservoir feasibility.

## 2. What exists

- **Source code:** `src/datp/data/datasets/ciciot2023/spec.py` and `prepare.py`
  are present and well-formed.
  - `CICIOT2023_SPEC`: `feature_count=39`, `benign_label="BENIGN"`,
    `client_identity=ClientIdentity.MERGED_FILE`, `expected_client_count=63`,
    `split_policy.calibration_benign_only=True`, `cal` ratio `0.15`,
    `cap_policy(total=50000, attack_reserve=10000, strategy="attack_preserving")`.
- **Raw artifacts:** `data/raw/CIC_IOT_Dataset2023/CSV/MERGED_CSV/Merged01..63.csv`
  are present (63 merged CSVs; the raw subtree holds 372 files including the
  per-capture `CSV/CSV` directory and `README.pdf`).

## 3. What is missing (decisive gaps)

- **No processed CICIoT2023 features.** `data/processed/` contains only
  `nbaiot/`; there is no `data/processed/ciciot2023/`.
- **No CICIoT2023 model scores.** `outputs/scores/` holds only N-BaIoT Regime-A
  scores (`outputs/scores/a/seed_*/…`). No CICIoT calibration/test scores exist.
- **No E=1 provenance / control origin** for CICIoT2023: with no training run and
  no score artifacts, there is no provenance manifest establishing E=1 or the
  pipeline-generated control origin (the same gate FB1 enforced for N-BaIoT).
- **Eligibility counts and reservoir feasibility are unknowable** without
  per-pseudo-client benign calibration scores — neither can be computed from raw
  CSVs alone.

## 4. Pseudo-client semantics (mandatory caveat)

CICIoT2023 "clients" are **file-level pseudo-clients** (`ClientIdentity.MERGED_FILE`,
one per `Merged*.csv`), **not physical devices**. This is correctly modeled in
`spec.py` and must be stated wherever CICIoT2023 appears. Pseudo-clients must
never be presented as physical devices, and CICIoT2023 must never be primary or
confirmatory evidence — N-BaIoT (physical devices) is the sole primary regime.

## 5. Verdict — INFEASIBLE-NOW (DEFERRED)

A protocol-faithful CICIoT2023 calibration-poisoning experiment **cannot proceed
under the current state**:

1. The entire downstream pipeline required by the protocol —
   processed features → E=1-trained autoencoder → clean per-pseudo-client
   benign calibration/test scores → reservoir feasibility — **does not exist**.
2. Producing it is itself a **heavy run** (preprocess + train + score), which is
   **gated until CP2-T056** and, under the current implementation-only
   authorization, **not permitted now**. This mirrors the FB1 precedent for
   N-BaIoT (no scores ⇒ provenance gate cannot pass ⇒ heavy run requires explicit
   authorization).

This is **not** a hard impossibility: the code path and raw CSVs are present, so
the stretch *could* become feasible if (a) a CONTINUE-gated CP2-T056
authorization explicitly funds a CICIoT2023 preprocessing+training+scoring run,
and (b) the resulting artifacts pass an E=1 provenance check and show non-empty
eligible pseudo-client sets with feasible (non-degenerate-tail) reservoirs.
Absent that, the verdict is INFEASIBLE-NOW and the stretch is **deferred**.

## 6. Consequences

- **FB4 stays NOT TRIGGERED.** FB4 activates only if T054 returns FEASIBLE
  (CICIoT2023 stretch path) **or** if the locked B4 `K=3` is shown unstable on
  stretch data. Neither holds: the stretch is not feasible now, and there is no
  CICIoT2023 stretch data on which a K-instability could be demonstrated. The
  N-BaIoT primary `K=3` lock is untouched and was confirmed stable by CP2-T046 /
  CP2-T048 (no drift).
- **CICIoT2023 is excluded from the paper's primary/confirmatory claims**
  (it always was — primary regime is N-BaIoT). If the stretch is ever run under
  a future authorization, it is external-validity only, reported separately, with
  the pseudo-client caveat.
- **Edge-IIoTset remains forbidden** (raw is present on disk under
  `data/raw/Edge-IIoTset/` but must never be used for CP2).

## 7. Evidence

- `src/datp/data/datasets/ciciot2023/spec.py` (pseudo-client semantics, splits).
- `find data/processed` → only `nbaiot/`; `find outputs/scores` → only Regime-A
  N-BaIoT; `find data/raw/CIC_IOT_Dataset2023` → 63 `Merged*.csv` present.
- FB1 precedent: `CP2_FALLBACK_REGISTER.md` (no scores ⇒ heavy run ⇒ explicit
  authorization required).
