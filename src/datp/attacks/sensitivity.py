from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from itertools import product
from pathlib import Path
from typing import cast

import numpy as np
from joblib import Parallel, delayed
from threadpoolctl import threadpool_limits

from datp.artifacts import sensitivity_manifest_path
from datp.attacks.injection import (
    PoisonedCalibrationSet,
    ScoreCollection,
    ThresholdPairBase,
    apply_defense,
)
from datp.attacks.manifests import (
    ClusterStabilityRow,
    DrawVariantRow,
    ProvenanceRecord,
    ScaleNormalizationRow,
    SensitivityManifest,
    TrustBoundaryRow,
)
from datp.attacks.metrics import (
    cluster_size_of,
    cluster_sizes,
    compute_cluster_pair,
    duplicate_rate,
    n_reassigned,
)
from datp.attacks.sweep import (
    InjectionOutcome,
    InjectionSpec,
    inject_single_victim,
    load_train_feature_reservoirs,
    load_seed_collections,
    recompute_pair,
)
from datp.config import (
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
    CalibrationPoisoningConfig,
)
from datp.core import REPOSITORY_NAME, SeedPair, get_logger, hash_jsonable
from datp.enums import (
    AttackerObjective,
    PoisoningDefense,
    PoisoningSourceStrategy,
    ReservoirDraw,
    ThresholdPolicy,
    ThresholdScaleScenario,
    is_train_feature_source,
)
from datp.statistics import cv, max_of, mean_of, min_of, percentile_of
from datp.thresholding import (
    CalibrationErrorSet,
    ClusterHyperparams,
    EligibilityResult,
    compute_client_thresholds,
)
from datp.types import (
    ClientId,
    FalsePositiveRate,
    PoisonFraction,
    RandomSeed,
    ScoreValue,
    ScoreVector,
    SignedCount,
    Threshold,
)

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class _CellBase:
    training_seed: RandomSeed
    victim_id: ClientId
    source: PoisoningSourceStrategy
    objective: AttackerObjective
    fraction: PoisonFraction


@dataclass(frozen=True, slots=True)
class _ClusterGrid:
    cluster_counts: tuple[SignedCount, ...]
    initializations: tuple[SignedCount, ...]
    random_states: tuple[RandomSeed, ...]


@dataclass(frozen=True, slots=True)
class _SensitivityTaskResult:
    cluster_stability: tuple[ClusterStabilityRow, ...]
    scale_normalization: ScaleNormalizationRow
    draw_variants: tuple[DrawVariantRow, ...]
    trust_boundary: tuple[TrustBoundaryRow, ...]


def _local_taus(
    collection: ScoreCollection, cal: dict[ClientId, ScoreVector]
) -> dict[ClientId, ScoreValue]:
    ids = collection.eligible_ids
    taus = compute_client_thresholds(
        CalibrationErrorSet.from_mapping({cid: cal[cid] for cid in ids}),
        EligibilityResult(eligible_ids=ids, pending_ids=()),
        q=THRESHOLD_QUANTILE,
    )
    return {cid: taus[cid] for cid in ids}


def _fprs(
    collection: ScoreCollection, thresholds: dict[ClientId, Threshold]
) -> dict[ClientId, FalsePositiveRate]:
    return {
        cid: mean_of(collection.clients[cid].test_benign > thr)
        for cid, thr in thresholds.items()
    }


def _scale_row(
    collection: ScoreCollection,
    base: _CellBase,
    victim_id: ClientId,
    poisoned_cal: ScoreVector,
) -> ScaleNormalizationRow:
    ids = collection.eligible_ids
    clean = {cid: collection.clients[cid].cal for cid in ids}
    pois = {**clean, victim_id: poisoned_cal}
    t_clean, t_pois = _local_taus(collection, clean), _local_taus(collection, pois)
    scales = {
        cid: percentile_of(clean[cid], SCALE_NORMALIZATION_STATISTIC_QUANTILE)
        for cid in ids
    }
    t_arr = np.array([t_clean[c] for c in ids])

    raw_clean = dict.fromkeys(ids, mean_of(list(t_clean.values())))
    raw_pois = dict.fromkeys(ids, mean_of(list(t_pois.values())))
    norm_clean_tau = mean_of([t_clean[c] / scales[c] for c in ids])
    norm_pois_tau = mean_of([t_pois[c] / scales[c] for c in ids])
    norm_clean = {c: norm_clean_tau * scales[c] for c in ids}
    norm_pois = {c: norm_pois_tau * scales[c] for c in ids}

    fpr = {
        name: _fprs(collection, thr)
        for name, thr in {
            ThresholdScaleScenario.RAW_CLEAN: raw_clean,
            ThresholdScaleScenario.RAW_POISONED: raw_pois,
            ThresholdScaleScenario.NORMALIZED_CLEAN: norm_clean,
            ThresholdScaleScenario.NORMALIZED_POISONED: norm_pois,
        }.items()
    }

    return ScaleNormalizationRow(
        training_seed=base.training_seed,
        victim_id=base.victim_id,
        source=base.source,
        objective=base.objective,
        fraction=base.fraction,
        tau_local_cv_clean=cv(t_arr),
        tau_local_max_min_ratio_clean=max_of(t_arr) / min_of(t_arr)
        if t_arr.min() > 0.0
        else math.nan,
        score_scale_cv_clean=cv(np.array(list(scales.values()))),
        raw_global_victim_delta_tau=raw_pois[victim_id] - raw_clean[victim_id],
        normalized_global_victim_delta_tau=norm_pois[victim_id] - norm_clean[victim_id],
        raw_global_victim_delta_fpr=fpr[ThresholdScaleScenario.RAW_POISONED][victim_id]
        - fpr[ThresholdScaleScenario.RAW_CLEAN][victim_id],
        normalized_global_victim_delta_fpr=fpr[
            ThresholdScaleScenario.NORMALIZED_POISONED
        ][victim_id]
        - fpr[ThresholdScaleScenario.NORMALIZED_CLEAN][victim_id],
        raw_global_cv_fpr_clean=cv(
            np.array(list(fpr[ThresholdScaleScenario.RAW_CLEAN].values()))
        ),
        normalized_global_cv_fpr_clean=cv(
            np.array(list(fpr[ThresholdScaleScenario.NORMALIZED_CLEAN].values()))
        ),
        raw_global_cv_fpr_poisoned=cv(
            np.array(list(fpr[ThresholdScaleScenario.RAW_POISONED].values()))
        ),
        normalized_global_cv_fpr_poisoned=cv(
            np.array(list(fpr[ThresholdScaleScenario.NORMALIZED_POISONED].values()))
        ),
    )


def _cluster_rows(
    collection: ScoreCollection,
    base: _CellBase,
    victim_id: ClientId,
    poisoned_cal_set: PoisonedCalibrationSet,
    grid: _ClusterGrid,
) -> list[ClusterStabilityRow]:
    rows: list[ClusterStabilityRow] = []
    for k, n_init, random_state in product(
        grid.cluster_counts, grid.initializations, grid.random_states
    ):
        pair = compute_cluster_pair(
            collection,
            poisoned_cal_set,
            THRESHOLD_QUANTILE,
            ClusterHyperparams(k=k, n_init=n_init, random_state=random_state),
        )
        clean_tau = pair.thresholds_clean[victim_id]
        rows.append(
            ClusterStabilityRow(
                training_seed=base.training_seed,
                victim_id=base.victim_id,
                source=base.source,
                objective=base.objective,
                fraction=base.fraction,
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


def _victim_shift(pair: ThresholdPairBase, victim_id: ClientId) -> ScoreValue:
    return pair.thresholds_pois[victim_id] - pair.thresholds_clean[victim_id]


def _draw_variant_rows(
    collection: ScoreCollection,
    base: _CellBase,
    seed_pair: SeedPair,
    victim_id: ClientId,
    with_outcome: InjectionOutcome,
) -> list[DrawVariantRow]:
    if is_train_feature_source(base.source):
        return []
    n = collection.clients[victim_id].cal.size
    requested = with_outcome.injection.n_replaced
    dup_with = duplicate_rate(with_outcome.injection.poisoned_cal)
    pairs_with = {
        policy: recompute_pair(collection, with_outcome.poisoned_cal_set, policy)
        for policy in _POLICIES
    }
    rows: list[DrawVariantRow] = []
    for draw in _DRAW_VARIANTS:
        budget = (
            min(requested, with_outcome.reservoir.pool.size)
            if draw == ReservoirDraw.WITHOUT_REPLACEMENT
            else requested
        )
        variant = inject_single_victim(
            collection,
            victim_id=victim_id,
            spec=InjectionSpec(
                source=base.source,
                fraction=budget / n,
                seed_pair=seed_pair,
                objective=base.objective,
                draw=draw,
            ),
        )
        dup_variant = duplicate_rate(variant.injection.poisoned_cal)
        for policy in _POLICIES:
            rows.append(
                DrawVariantRow(
                    training_seed=base.training_seed,
                    victim_id=base.victim_id,
                    source=base.source,
                    objective=base.objective,
                    fraction=base.fraction,
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
    trim_fraction: PoisonFraction,
) -> ThresholdPairBase:
    ids = collection.eligible_ids
    defended_collection, poisoned = apply_defense(
        collection,
        {cid: with_outcome.poisoned_cal_set[cid].cal for cid in ids},
        defense=PoisoningDefense.TRIMMED_CALIBRATION,
        trim_fraction=trim_fraction,
    )
    return recompute_pair(
        defended_collection,
        PoisonedCalibrationSet.from_mapping(poisoned),
        policy,
    )


def _trust_boundary_rows(
    collection: ScoreCollection,
    base: _CellBase,
    victim_id: ClientId,
    with_outcome: InjectionOutcome,
) -> list[TrustBoundaryRow]:
    victim_cal = collection.clients[victim_id].cal
    extreme = (
        max_of(victim_cal)
        if base.objective == AttackerObjective.THRESHOLD_RAISE
        else min_of(victim_cal)
    )
    rows: list[TrustBoundaryRow] = []
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
                training_seed=base.training_seed,
                victim_id=base.victim_id,
                source=base.source,
                objective=base.objective,
                fraction=base.fraction,
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
                if abs(reference) > 0.0
                else math.nan,
            )
        )
    return rows


@dataclass(frozen=True, slots=True)
class _SensitivityTask:
    collection: ScoreCollection
    seed_pair: SeedPair
    base: _CellBase
    grid: _ClusterGrid
    feature_reservoir_scores: dict[ClientId, ScoreVector] | None
    feature_row_ids: dict[ClientId, np.ndarray] | None
    feature_tail_mass: PoisonFraction


def _task(task: _SensitivityTask) -> _SensitivityTaskResult:
    collection = task.collection
    seed_pair = task.seed_pair
    base = task.base
    victim_id = base.victim_id
    with threadpool_limits(limits=1):
        with_outcome = inject_single_victim(
            collection,
            victim_id=victim_id,
            spec=InjectionSpec(
                source=base.source,
                fraction=base.fraction,
                seed_pair=seed_pair,
                objective=base.objective,
                draw=ReservoirDraw.WITH_REPLACEMENT,
            ),
            feature_reservoir_scores=(
                task.feature_reservoir_scores.get(victim_id)
                if task.feature_reservoir_scores is not None
                else None
            ),
            feature_row_ids=(
                task.feature_row_ids.get(victim_id)
                if task.feature_row_ids is not None
                else None
            ),
            feature_tail_mass=task.feature_tail_mass,
        )
        return _SensitivityTaskResult(
            cluster_stability=tuple(
                _cluster_rows(
                    collection,
                    base,
                    victim_id,
                    with_outcome.poisoned_cal_set,
                    task.grid,
                )
            ),
            scale_normalization=_scale_row(
                collection, base, victim_id, with_outcome.injection.poisoned_cal
            ),
            draw_variants=tuple(
                _draw_variant_rows(collection, base, seed_pair, victim_id, with_outcome)
            ),
            trust_boundary=tuple(
                _trust_boundary_rows(collection, base, victim_id, with_outcome)
            ),
        )


def run_sensitivity(
    base_dir: Path,
    config: CalibrationPoisoningConfig,
    *,
    data_root: Path = Path("."),
) -> SensitivityManifest:
    logger.info(
        "sensitivity analysis started",
        training_seed_count=len(config.seeds.training),
        poisoning_seed_count=len(config.seeds.poisoning),
    )
    collections = load_seed_collections(base_dir, config)
    feature_scores_by_seed: dict[RandomSeed, dict[ClientId, ScoreVector]] = {}
    feature_ids_by_seed: dict[RandomSeed, dict[ClientId, np.ndarray]] = {}
    if any(is_train_feature_source(source) for source in config.sources):
        feature_scores_by_seed, feature_ids_by_seed = load_train_feature_reservoirs(
            base_dir,
            collections,
            data_root=data_root,
            donor_scope=config.feature_donor_scope,
        )
    fractions = tuple(
        sorted(set(CLUSTER_SENSITIVITY_FRACTIONS) & set(DRAW_VARIANT_FRACTIONS))
    )
    grid = _ClusterGrid(
        cluster_counts=CLUSTER_SENSITIVITY_K_GRID,
        initializations=CLUSTER_SENSITIVITY_N_INIT_GRID,
        random_states=CLUSTER_SENSITIVITY_RANDOM_STATES,
    )
    tasks = [
        _SensitivityTask(
            collection=collections[t_seed],
            seed_pair=SeedPair(training_seed=t_seed, poisoning_seed=p_seed),
            base=_CellBase(
                training_seed=t_seed,
                victim_id=victim,
                source=src,
                objective=obj,
                fraction=frac,
            ),
            grid=grid,
            feature_reservoir_scores=feature_scores_by_seed.get(t_seed),
            feature_row_ids=feature_ids_by_seed.get(t_seed),
            feature_tail_mass=config.feature_tail_mass,
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
    logger.info(
        "sensitivity analysis plan prepared",
        task_count=len(tasks),
        cluster_count=len(grid.cluster_counts),
        initialization_count=len(grid.initializations),
        random_state_count=len(grid.random_states),
    )
    try:
        results = cast(
            Sequence[_SensitivityTaskResult],
            Parallel(n_jobs=-1)(delayed(_task)(task) for task in tasks),
        )
    except Exception:
        logger.exception(
            "sensitivity analysis task execution failed", task_count=len(tasks)
        )
        raise

    manifest = SensitivityManifest(
        generated_at_utc=datetime.now(UTC).isoformat(),
        provenance=ProvenanceRecord(local_epochs=1, repository=REPOSITORY_NAME),
        config_hash=hash_jsonable(config.model_dump(mode="json")),
        cluster_stability=tuple(
            row for result in results for row in result.cluster_stability
        ),
        scale_normalization=tuple(result.scale_normalization for result in results),
        draw_variants=tuple(row for result in results for row in result.draw_variants),
        trust_boundary=tuple(
            row for result in results for row in result.trust_boundary
        ),
    )
    logger.info(
        "sensitivity analysis completed",
        cluster_stability_count=len(manifest.cluster_stability),
        scale_normalization_count=len(manifest.scale_normalization),
        draw_variant_count=len(manifest.draw_variants),
        trust_boundary_count=len(manifest.trust_boundary),
    )
    return manifest


def write_sensitivity_manifest(base_dir: Path, data_root: Path = Path(".")) -> Path:
    out_path = sensitivity_manifest_path(base_dir)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        run_sensitivity(
            base_dir,
            CalibrationPoisoningConfig.for_bounded_sweep(),
            data_root=data_root,
        ).model_dump_json(indent=2)
    )
    logger.info("sensitivity manifest written", path=out_path)
    return out_path
