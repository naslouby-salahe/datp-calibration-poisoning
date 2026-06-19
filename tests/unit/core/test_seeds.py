import random

import numpy as np
import torch

from datp.core.seeds import set_seeds


def test_set_seeds_makes_python_random_deterministic() -> None:
    set_seeds(0)
    first = random.getstate()
    set_seeds(0)
    second = random.getstate()
    assert first == second


def test_numpy_generator_fixture_is_deterministic() -> None:
    set_seeds(0)
    rng = np.random.default_rng(0)
    first = rng.random(4)
    set_seeds(0)
    rng = np.random.default_rng(0)
    second = rng.random(4)
    assert np.array_equal(first, second)


def test_set_seeds_makes_torch_deterministic() -> None:
    set_seeds(0)
    first = torch.randn(4)
    set_seeds(0)
    second = torch.randn(4)
    assert torch.equal(first, second)


def test_set_seeds_sets_cudnn_flags() -> None:
    set_seeds(0)
    assert torch.backends.cudnn.deterministic is True
    assert torch.backends.cudnn.benchmark is False


def test_set_seeds_sets_matmul_precision() -> None:
    set_seeds(0)
    assert torch.get_float32_matmul_precision() == "high"
