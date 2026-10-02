
from __future__ import annotations
from datp.types import (
    Ratio,
    SignedDelta,
    Threshold,
    TruePositiveRate,
)

COLLAPSE_BA_THRESHOLD: Threshold = 0.9
COLLAPSE_TPR_THRESHOLD: TruePositiveRate = 0.9

FPR_DELTA_ADVANTAGE_MIN: SignedDelta = 0.0
COVERAGE_RATIO_FLOOR: Ratio = 1.0
