from typing import NamedTuple

import numpy as np
from numpy.typing import NDArray

class _NormalDistribution:
    def cdf(self, x: float) -> float: ...
    def ppf(self, q: float) -> float: ...

norm: _NormalDistribution

class BinomTestResult(NamedTuple):
    statistic: float
    pvalue: float
    def proportion_ci(self, confidence_level: float = ..., method: str = ...) -> object: ...

def binomtest(
    k: int, n: int, p: float = ..., alternative: str = ...
) -> BinomTestResult: ...
def skew(a: NDArray[np.float64], axis: int = ..., **kwargs: object) -> float: ...

class SignificanceResult(NamedTuple):
    statistic: float
    pvalue: float

def spearmanr(
    a: NDArray[np.float64], b: NDArray[np.float64], **kwargs: object
) -> SignificanceResult: ...
def wilcoxon(
    x: NDArray[np.float64], y: NDArray[np.float64], **kwargs: object
) -> SignificanceResult: ...
