from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import torch

from datp.attacks.injection import InjectionResult
from datp.modeling import Autoencoder
from datp.types import PoisonFraction, Ratio, ScoreVector, SignedCount


@dataclass(frozen=True, slots=True)
class FeatureReservoirInjection:
    injection: InjectionResult
    donor_indices: np.ndarray
    candidate_indices: np.ndarray
    donor_feature_unique_fraction: Ratio | None


def _validate_injection_inputs(
    clean_cal: ScoreVector,
    benign_reservoir_scores: ScoreVector,
    feature_row_ids: np.ndarray,
    fraction: PoisonFraction,
    tail_fraction: PoisonFraction,
) -> None:
    if clean_cal.ndim != 1 or benign_reservoir_scores.ndim != 1:
        raise ValueError("calibration and reservoir scores must be one-dimensional")
    if (
        feature_row_ids.ndim != 1
        or feature_row_ids.size != benign_reservoir_scores.size
    ):
        raise ValueError("feature_row_ids must align with reservoir scores")
    if (
        not np.isfinite(clean_cal).all()
        or not np.isfinite(benign_reservoir_scores).all()
    ):
        raise ValueError("calibration and reservoir scores must be finite")
    if not 0.0 <= fraction <= 1.0:
        raise ValueError(f"fraction must be in [0, 1]; got {fraction}")
    if not 0.0 < tail_fraction <= 1.0:
        raise ValueError(f"tail_fraction must be in (0, 1]; got {tail_fraction}")
    if benign_reservoir_scores.size == 0:
        raise ValueError("benign feature reservoir cannot be empty")
    if clean_cal.size == 0:
        raise ValueError("calibration score vector cannot be empty")


def score_feature_rows(
    model: Autoencoder, features: np.ndarray, *, batch_size: SignedCount = 512
) -> ScoreVector:
    if features.ndim != 2 or features.shape[0] == 0 or features.shape[1] == 0:
        raise ValueError(
            f"features must be a non-empty 2-D matrix; got {features.shape}"
        )
    if batch_size <= 0:
        raise ValueError(f"batch_size must be positive; got {batch_size}")
    if not np.isfinite(features).all():
        raise ValueError("features must contain only finite values")

    model.eval()
    parts: list[np.ndarray] = []
    with torch.inference_mode():
        for start in range(0, len(features), batch_size):
            batch = torch.as_tensor(
                features[start : start + batch_size], dtype=torch.float32
            )
            scores = model.reconstruction_error(batch).detach().cpu().numpy()
            parts.append(scores.astype(np.float64, copy=False))
    return np.concatenate(parts) if parts else np.empty(0, dtype=np.float64)


def inject_feature_reservoir(
    *,
    clean_cal: ScoreVector,
    benign_reservoir_scores: ScoreVector,
    feature_row_ids: np.ndarray,
    fraction: PoisonFraction,
    tail_fraction: PoisonFraction,
    rng: np.random.Generator,
) -> FeatureReservoirInjection:
    _validate_injection_inputs(
        clean_cal,
        benign_reservoir_scores,
        feature_row_ids,
        fraction,
        tail_fraction,
    )

    n_total = clean_cal.size
    n_replace = round(fraction * n_total)
    if fraction > 0.0:
        n_replace = max(1, n_replace)
    if n_replace == 0:
        return FeatureReservoirInjection(
            InjectionResult(
                poisoned_cal=clean_cal.copy(),
                n_replaced=0,
                n_total=n_total,
                fraction=0.0,
                positions_replaced=np.empty(0, dtype=np.intp),
            ),
            np.empty(0, dtype=np.intp),
            np.empty(0, dtype=np.intp),
            None,
        )

    _, unique_row_indices = np.unique(feature_row_ids, return_index=True)
    n_candidates = max(1, math.floor(tail_fraction * len(unique_row_indices)))
    if n_replace > n_candidates:
        raise ValueError(
            f"Requested {n_replace} replacements but the selected benign feature "
            f"tail contains only {n_candidates} distinct rows."
        )

    unique_row_indices = unique_row_indices[
        np.argsort(benign_reservoir_scores[unique_row_indices])
    ]
    candidate_indices = unique_row_indices[-n_candidates:]
    donor_indices = rng.choice(candidate_indices, size=n_replace, replace=False)
    positions = rng.choice(n_total, size=n_replace, replace=False)
    poisoned = clean_cal.copy()
    poisoned[positions] = benign_reservoir_scores[donor_indices]
    result = InjectionResult(
        poisoned_cal=poisoned,
        n_replaced=n_replace,
        n_total=n_total,
        fraction=n_replace / n_total,
        positions_replaced=positions,
    )
    donor_unique_fraction = len(np.unique(feature_row_ids[donor_indices])) / n_replace
    return FeatureReservoirInjection(
        result, donor_indices, candidate_indices, donor_unique_fraction
    )
