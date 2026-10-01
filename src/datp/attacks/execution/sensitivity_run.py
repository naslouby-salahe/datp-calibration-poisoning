"""Sensitivity analyses beside the bounded sweep: cluster stability, scale normalization, distinct draws."""

from __future__ import annotations

import math
from collections.abc import Sequence
from datetime import UTC, datetime
from itertools import product
from pathlib import Path
from typing import TypedDict, cast

import numpy as np
from joblib import Parallel, delayed
from threadpoolctl import threadpool_limits

from datp.artifacts.poison_layout import PoisonLayout
from datp.attacks.constants import (
    CLUSTER_SENSITIVITY_FRACTIONS,
    CLUSTER_SENSITIVITY_K_GRID,
    CLUSTER_SENSITIVITY_N_INIT_GRID,
    CLUSTER_SENSITIVITY_RANDOM_STATES,
    DRAW_VARIANT_FRACTIONS,
    NBAIOT_MAIN_SOURCE_OBJECTIVE_PAIRS,
    SCALE_NORMALIZATION_STATISTIC_QUANTILE,
    THRESHOLD_QUANTILE,
    TRIM_FRACTION_APPENDIX,
    TRIM_FRACTION_PRIMARY,
)
from datp.attacks.enums import AttackerObjective, PoisoningSourceStrategy, ReservoirDraw
from datp.attacks.execution.bounded_sweep_run import load_seed_collections
from datp.attacks.execution.cell_runner import (
    InjectionOutcome,
    InjectionSpec,
    PolicyPair,
    inject_single_victim,
    recompute_pair,
)
from datp.attacks.injection.defenses import (
    build_defended_collection,
    defend_poisoned_cal,
)
from datp.attacks.manifests.run_manifest import ProvenanceRecord
from datp.attacks.manifests.sensitivity_manifest import (
    ClusterStabilityRow,
    DrawVariantRow,
    ScaleNormalizationRow,
    SensitivityManifest,
    TrustBoundaryRow,
)
from datp.attacks.metrics.cluster_stability import (
    cluster_size_of,
    cluster_sizes,
    n_reassigned,
)
from datp.attacks.metrics.diagnostics import duplicate_rate
from datp.attacks.score_containers import ScoreCollection
from datp.attacks.threshold_recomputation.cluster_threshold_recompute import (
    ClusterHyperparams,
    compute_cluster_pair,
)
from datp.attacks.types import PoisonedCalibrationSet
from datp.config.attack_config import CalibrationPoisoningConfig
from datp.core.enums import ThresholdPolicy
from datp.core.provenance import REPOSITORY_NAME, hash_jsonable
from datp.core.seeds import SeedPair
from datp.statistics.aggregates import cv
from datp.thresholding.eligibility import (
    CalibrationErrorSet,
    EligibilityResult,
    compute_client_thresholds,
)

class _CellBase(TypedDict):
    training_seed: int
    victim_id: str
    source: PoisoningSourceStrategy
    objective: AttackerObjective
    fraction: float


_ClusterGrid = tuple[tuple[int, ...], tuple[int, ...], tuple[int, ...]]

_TaskRows = tuple[
    list[ClusterStabilityRow],
    ScaleNormalizationRow,
    list[DrawVariantRow],
    list[TrustBoundaryRow],
]


def _spec(
    seed_pair: SeedPair,
    source: PoisoningSourceStrategy,
    objective: AttackerObjective,
    fraction: float,
    draw: ReservoirDraw,
) -> InjectionSpec:
    return InjectionSpec(
        source=source,
        fraction=fraction,
        seed_pair=seed_pair,
        objective=objective,
        draw=draw,
    )


def _local_taus(
    collection: ScoreCollection, cal: dict[str, np.ndarray]
) -> dict[str, float]:
    ids = collection.eligible_ids
    taus = compute_client_thresholds(
        CalibrationErrorSet.from_mapping({cid: cal[cid] for cid in ids}),
        EligibilityResult(eligible_ids=ids, pending_ids=()),
        q=THRESHOLD_QUANTILE,
    )
    return {cid: taus[cid] for cid in ids}


def _fprs(
    collection: ScoreCollection, thresholds: dict[str, float]
) -> dict[str, float]:
    return {
        cid: float(np.mean(collection.for_client(cid).test_benign > thr))
        for cid, thr in thresholds.items()
    }


def _scale_row(
    collection: ScoreCollection,
    base: _CellBase,
    victim_id: str,
    poisoned_cal: np.ndarray,
) -> ScaleNormalizationRow:
    ids = collection.eligible_ids
    clean = {cid: collection.for_client(cid).cal for cid in ids}
    pois = {**clean, victim_id: poisoned_cal}
    t_clean, t_pois = _local_taus(collection, clean), _local_taus(collection, pois)
    scales = {
        cid: float(np.percentile(clean[cid], SCALE_NORMALIZATION_STATISTIC_QUANTILE))
        for cid in ids
    }
    t_arr = np.array([t_clean[c] for c in ids])

    raw_clean = dict.fromkeys(ids, float(np.mean(list(t_clean.values()))))
    raw_pois = dict.fromkeys(ids, float(np.mean(list(t_pois.values()))))
    norm_clean_tau = float(np.mean([t_clean[c] / scales[c] for c in ids]))
    norm_pois_tau = float(np.mean([t_pois[c] / scales[c] for c in ids]))
    norm_clean = {c: norm_clean_tau * scales[c] for c in ids}
    norm_pois = {c: norm_pois_tau * scales[c] for c in ids}

    fpr = {
        name: _fprs(collection, thr)
        for name, thr in {
            "raw_clean": raw_clean,
            "raw_pois": raw_pois,
            "norm_clean": norm_clean,
            "norm_pois": norm_pois,
        }.items()
    }

    def fleet_cv(name: str) -> float:
        return cv(np.array(list(fpr[name].values())))

    return ScaleNormalizationRow(
        **base,
        tau_local_cv_clean=cv(t_arr),
        tau_local_max_min_ratio_clean=float(t_arr.max() / t_arr.min())
        if t_arr.min() > 0.0
        else math.nan,
        score_scale_cv_clean=cv(np.array(list(scales.values()))),
        raw_global_victim_delta_tau=raw_pois[victim_id] - raw_clean[victim_id],
        normalized_global_victim_delta_tau=norm_pois[victim_id] - norm_clean[victim_id],
        raw_global_victim_delta_fpr=fpr["raw_pois"][victim_id]
        - fpr["raw_clean"][victim_id],
        normalized_global_victim_delta_fpr=fpr["norm_pois"][victim_id]
        - fpr["norm_clean"][victim_id],
        raw_global_cv_fpr_clean=fleet_cv("raw_clean"),
        normalized_global_cv_fpr_clean=fleet_cv("norm_clean"),
        raw_global_cv_fpr_poisoned=fleet_cv("raw_pois"),
        normalized_global_cv_fpr_poisoned=fleet_cv("norm_pois"),
    )


def _cluster_rows(
    collection: ScoreCollection,
    base: _CellBase,
    victim_id: str,
    poisoned_cal_set: PoisonedCalibrationSet,
    grid: _ClusterGrid,
) -> list[ClusterStabilityRow]:
    rows = []
    for k, n_init, random_state in product(*grid):
        pair = compute_cluster_pair(
            collection,
            poisoned_cal_set,
            THRESHOLD_QUANTILE,
            ClusterHyperparams(k=k, n_init=n_init, random_state=random_state),
        )
        clean_tau = pair.thresholds_clean[victim_id]
        rows.append(
            ClusterStabilityRow(
                **base,
                k=k,
                n_init=n_init,
                random_state=random_state,
                victim_delta_tau=pair.thresholds_pois[victim_id] - clean_tau,
                fixed_victim_delta_tau=pair.fixed_assignment_thresholds[victim_id]
                - clean_tau,
                victim_size_clean=cluster_size_of(pair.clean_assignments, victim_id),
                victim_size_poisoned=cluster_size_of(
                    pair.poisoned_assignments, victim_id
                ),
                n_reassigned=n_reassigned(
                    pair.clean_assignments, pair.poisoned_assignments
                ),
                silhouette_clean=pair.silhouette_clean,
                silhouette_poisoned=pair.silhouette_poisoned,
                sizes_clean=cluster_sizes(pair.clean_assignments),
                sizes_poisoned=cluster_sizes(pair.poisoned_assignments),
            )
        )
    return rows


_POLICIES = (
    ThresholdPolicy.GLOBAL_THRESHOLD,
    ThresholdPolicy.LOCAL_THRESHOLD,
    ThresholdPolicy.CLUSTER_THRESHOLD,
)

_DRAW_VARIANTS = (
    ReservoirDraw.WITHOUT_REPLACEMENT,
    ReservoirDraw.DISJOINT_RESERVOIR,
    ReservoirDraw.INTERPOLATED_TAIL,
)


def _victim_shift(pair: PolicyPair, victim_id: str) -> float:
    return pair.thresholds_pois[victim_id] - pair.thresholds_clean[victim_id]


def _draw_variant_rows(
    collection: ScoreCollection,
    base: _CellBase,
    seed_pair: SeedPair,
    victim_id: str,
    with_outcome: InjectionOutcome,
) -> list[DrawVariantRow]:
    n = collection.for_client(victim_id).cal.size
    requested = with_outcome.injection.n_replaced
    dup_with = duplicate_rate(with_outcome.injection.poisoned_cal)
    pairs_with = {
        policy: recompute_pair(collection, with_outcome.poisoned_cal_set, policy)
        for policy in _POLICIES
    }
    rows = []
    for draw in _DRAW_VARIANTS:
        budget = (
            min(requested, with_outcome.reservoir.pool.size)
            if draw == ReservoirDraw.WITHOUT_REPLACEMENT
            else requested
        )
        variant = inject_single_victim(
            collection,
            victim_id=victim_id,
            spec=_spec(
                seed_pair,
                base["source"],
                base["objective"],
                budget / n,
                draw,
            ),
        )
        dup_variant = duplicate_rate(variant.injection.poisoned_cal)
        for policy in _POLICIES:
            rows.append(
                DrawVariantRow(
                    **base,
                    policy=policy,
                    draw=draw,
                    requested_n_replaced=requested,
                    effective_n_replaced=variant.injection.n_replaced,
                    pool_size=variant.reservoir.pool.size,
                    delta_tau_with_replacement=_victim_shift(
                        pairs_with[policy], victim_id
                    ),
                    delta_tau_variant=_victim_shift(
                        recompute_pair(collection, variant.poisoned_cal_set, policy),
                        victim_id,
                    ),
                    duplicate_rate_with_replacement=dup_with,
                    duplicate_rate_variant=dup_variant,
                )
            )
    return rows


def _defended_pair(
    collection: ScoreCollection,
    with_outcome: InjectionOutcome,
    policy: ThresholdPolicy,
    trim_fraction: float,
) -> PolicyPair:
    ids = collection.eligible_ids
    poisoned = defend_poisoned_cal(
        {cid: with_outcome.poisoned_cal_set.for_client(cid).cal for cid in ids},
        trim_fraction,
    )
    return recompute_pair(
        build_defended_collection(collection, trim_fraction),
        PoisonedCalibrationSet.from_mapping(poisoned),
        policy,
    )


def _trust_boundary_rows(
    collection: ScoreCollection,
    base: _CellBase,
    victim_id: str,
    with_outcome: InjectionOutcome,
) -> list[TrustBoundaryRow]:
    victim_cal = collection.for_client(victim_id).cal
    extreme = (
        float(victim_cal.max())
        if base["objective"] == AttackerObjective.THRESHOLD_RAISE
        else float(victim_cal.min())
    )
    rows = []
    for policy in _POLICIES:
        undefended = recompute_pair(collection, with_outcome.poisoned_cal_set, policy)
        tau_clean = undefended.thresholds_clean[victim_id]
        shift = _victim_shift(undefended, victim_id)
        reference = extreme - tau_clean
        primary = _defended_pair(
            collection, with_outcome, policy, TRIM_FRACTION_PRIMARY
        )
        appendix = _defended_pair(
            collection, with_outcome, policy, TRIM_FRACTION_APPENDIX
        )
        rows.append(
            TrustBoundaryRow(
                **base,
                policy=policy,
                delta_tau_undefended=shift,
                delta_tau_trim_primary=_victim_shift(primary, victim_id),
                delta_tau_trim_appendix=_victim_shift(appendix, victim_id),
                residual_vs_clean_trim_primary=primary.thresholds_pois[victim_id]
                - tau_clean,
                residual_vs_clean_trim_appendix=appendix.thresholds_pois[victim_id]
                - tau_clean,
                overwrite_reference_shift=reference,
                buffer_to_overwrite_ratio=shift / reference
                if reference != 0.0
                else math.nan,
            )
        )
    return rows


def _task(
    collection: ScoreCollection,
    seed_pair: SeedPair,
    victim_id: str,
    source: PoisoningSourceStrategy,
    objective: AttackerObjective,
    fraction: float,
    grid: _ClusterGrid,
) -> _TaskRows:
    base: _CellBase = {
        "training_seed": seed_pair.training_seed,
        "victim_id": victim_id,
        "source": source,
        "objective": objective,
        "fraction": fraction,
    }
    with threadpool_limits(limits=1):
        with_outcome = inject_single_victim(
            collection,
            victim_id=victim_id,
            spec=_spec(
                seed_pair, source, objective, fraction, ReservoirDraw.WITH_REPLACEMENT
            ),
        )
        return (
            _cluster_rows(
                collection, base, victim_id, with_outcome.poisoned_cal_set, grid
            ),
            _scale_row(
                collection, base, victim_id, with_outcome.injection.poisoned_cal
            ),
            _draw_variant_rows(collection, base, seed_pair, victim_id, with_outcome),
            _trust_boundary_rows(collection, base, victim_id, with_outcome),
        )


def run_sensitivity(
    base_dir: Path, config: CalibrationPoisoningConfig
) -> SensitivityManifest:
    """Run all sensitivity analyses and return the manifest."""
    collections = load_seed_collections(base_dir, config)
    fractions = tuple(
        sorted(set(CLUSTER_SENSITIVITY_FRACTIONS) & set(DRAW_VARIANT_FRACTIONS))
    )
    grid: _ClusterGrid = (
        CLUSTER_SENSITIVITY_K_GRID,
        CLUSTER_SENSITIVITY_N_INIT_GRID,
        CLUSTER_SENSITIVITY_RANDOM_STATES,
    )
    tasks = [
        (
            collections[t_seed],
            SeedPair(training_seed=t_seed, poisoning_seed=p_seed),
            victim,
            src,
            obj,
            frac,
            grid,
        )
        for t_seed, p_seed in zip(
            config.seeds.training, config.seeds.poisoning, strict=True
        )
        for victim, (src, obj), frac in product(
            collections[t_seed].eligible_ids,
            NBAIOT_MAIN_SOURCE_OBJECTIVE_PAIRS,
            fractions,
        )
    ]
    results = cast(
        Sequence[_TaskRows],
        Parallel(n_jobs=-1)(delayed(_task)(*args) for args in tasks),
    )

    return SensitivityManifest(
        generated_at_utc=datetime.now(UTC).isoformat(),
        provenance=ProvenanceRecord(local_epochs=1, repository=REPOSITORY_NAME),
        config_hash=hash_jsonable(config.model_dump(mode="json")),
        cluster_stability=tuple(r for c, _, _, _ in results for r in c),
        scale_normalization=tuple(s for _, s, _, _ in results),
        draw_variants=tuple(r for _, _, d, _ in results for r in d),
        trust_boundary=tuple(r for _, _, _, t in results for r in t),
    )


def write_sensitivity_manifest(base_dir: Path) -> Path:
    """Run the sensitivity analyses and write the manifest JSON to disk."""
    out_path = PoisonLayout(base_dir=base_dir).sensitivity_manifest()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        run_sensitivity(
            base_dir, CalibrationPoisoningConfig.for_bounded_sweep()
        ).model_dump_json(indent=2)
    )
    return out_path
