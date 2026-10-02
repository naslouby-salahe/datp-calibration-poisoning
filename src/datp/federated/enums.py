from __future__ import annotations

import enum


class FederatedRoundStage(enum.StrEnum):
    FIT = "fit"
    EVALUATE = "evaluate"
