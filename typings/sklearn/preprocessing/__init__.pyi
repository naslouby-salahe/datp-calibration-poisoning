from typing import Self

import numpy as np


class StandardScaler:
    n_features_in_: int

    def __init__(self, *, copy: bool = ..., with_mean: bool = ..., with_std: bool = ...) -> None: ...

    def fit(self, X: np.ndarray, y: None = ..., sample_weight: np.ndarray | None = ...) -> Self: ...

    def transform(self, X: np.ndarray, copy: bool | None = ...) -> np.ndarray: ...

    def fit_transform(
        self, X: np.ndarray, y: None = ..., sample_weight: np.ndarray | None = ...
    ) -> np.ndarray: ...
