from __future__ import annotations

from pathlib import Path

from datp.core.enums import Regime
from datp.core.errors import fmt
from datp.data.contracts import PartitionResult, RegimeCResult
from datp.data.regimes.regime_a import prepare_regime_a
from datp.data.regimes.regime_b import prepare_regime_b
from datp.data.regimes.regime_c import partition_regime_c


def prepare_regime_data(
    *,
    regime: Regime,
    raw_dir: Path,
    output_dir: Path,
    n_min: int,
    seed: int,
    cap: int,
    attack_reserve_fraction: float,
    alpha: float | None,
    n_clients: int,
    train_frac: float,
    cal_frac: float,
    balanced_test: bool,
) -> dict[str, PartitionResult] | RegimeCResult:
    if regime == Regime.A:
        return prepare_regime_a(
            raw_dir=raw_dir,
            output_dir=output_dir,
            regime=regime,
            n_min=n_min,
            seed=seed,
            balanced_test=balanced_test,
        )
    if regime == Regime.B:
        return prepare_regime_b(
            raw_dir=raw_dir,
            output_dir=output_dir,
            regime=regime,
            n_min=n_min,
            cap=cap,
            seed=seed,
            attack_reserve_fraction=attack_reserve_fraction,
        )
    if regime == Regime.C:
        if alpha is None:
            raise ValueError(
                fmt("data.regimes", "alpha is required for regime c", "float", "None")
            )
        return partition_regime_c(
            raw_nbaiot_dir=raw_dir,
            output_dir=output_dir,
            alpha=alpha,
            seed=seed,
            n_clients=n_clients,
            n_min=n_min,
            train_frac=train_frac,
            cal_frac=cal_frac,
        )
    raise ValueError(
        fmt("data.regimes", "Unknown regime", "'a', 'b', or 'c'", repr(regime))
    )
