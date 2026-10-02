import numpy as np
from numpy.typing import ArrayLike, NDArray

def multipletests(
    pvals: ArrayLike,
    alpha: float = ...,
    method: str = ...,
    maxiter: int = ...,
    is_sorted: bool = ...,
    returnsorted: bool = ...,
) -> tuple[NDArray[np.bool_], NDArray[np.float64], float, float]: ...
