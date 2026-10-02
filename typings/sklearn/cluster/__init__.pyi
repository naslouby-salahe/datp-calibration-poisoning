from typing import Literal

import numpy as np


class KMeans:
    def __init__(
        self,
        n_clusters: int = 8,
        *,
        init: str | np.ndarray = "k-means++",
        n_init: int | Literal["auto"] = "auto",
        max_iter: int = 300,
        random_state: int | None = None,
    ) -> None: ...

    def fit_predict(self, X: np.ndarray) -> np.ndarray: ...
