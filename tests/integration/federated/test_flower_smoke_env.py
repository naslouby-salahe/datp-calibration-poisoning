import math

import pytest

from tests.fixtures.flower_smoke import SMOKE_NUM_ROUNDS, run_flower_smoke

_SMOKE_SEED = 42


@pytest.mark.integration
def test_two_client_flower_simulation() -> None:
    round_losses = run_flower_smoke(seed=_SMOKE_SEED)

    assert len(round_losses) == SMOKE_NUM_ROUNDS, (
        f"Expected {SMOKE_NUM_ROUNDS} rounds of distributed losses, "
        f"got {len(round_losses)}"
    )

    for rnd, loss in round_losses:
        assert math.isfinite(loss), (
            f"Round {rnd}: distributed loss is not finite ({loss})"
        )
