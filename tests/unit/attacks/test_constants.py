from datp.attacks.constants import (
    CLUSTER_K_NBAIOT,
    CLUSTER_MAX_ITER,
    CLUSTER_N_INIT,
    CLUSTER_RANDOM_STATE,
    MATERIALITY_FACTOR,
    N_MIN,
    NBAIOT_MAIN_SWEEP_FRACTIONS,
    TAIL_MASS,
)


def test_calibration_constants() -> None:
    assert N_MIN == 100
    assert abs(TAIL_MASS - 0.10) < 1e-9
    assert abs(MATERIALITY_FACTOR - 0.1) < 1e-9


def test_cluster_constants() -> None:
    assert CLUSTER_K_NBAIOT == 3
    assert CLUSTER_N_INIT == 10
    assert CLUSTER_MAX_ITER == 300
    assert CLUSTER_RANDOM_STATE == 42


def test_bounded_fraction_grid() -> None:
    assert NBAIOT_MAIN_SWEEP_FRACTIONS == (0.0, 0.10, 0.20, 0.40)
