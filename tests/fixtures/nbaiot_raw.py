"""Fixture for generating synthetic raw N-BAIOT dataset files."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

N_FEATURES = 10
N_BENIGN = 300
N_ATTACK = 50
DEVICES = ["TestDev_A", "TestDev_B"]


def make_synthetic_raw(base: Path) -> Path:
    """Write synthetic CSV traffic logs mimicking N-BAIOT benign and attack data."""
    raw = base / "raw"
    rng = np.random.default_rng(42)
    cols = [f"feat_{i}" for i in range(N_FEATURES)]

    for device_id in DEVICES:
        dev_dir = raw / device_id
        dev_dir.mkdir(parents=True)
        pd.DataFrame(
            rng.standard_normal((N_BENIGN, N_FEATURES)),
            columns=pd.Index(cols),
        ).to_csv(
            dev_dir / "benign_traffic.csv",
            index=False,
        )
        attack_dir = dev_dir / "gafgyt_attacks"
        attack_dir.mkdir()
        pd.DataFrame(
            rng.standard_normal((N_ATTACK, N_FEATURES)),
            columns=pd.Index(cols),
        ).to_csv(
            attack_dir / "combo.csv",
            index=False,
        )
    return raw
