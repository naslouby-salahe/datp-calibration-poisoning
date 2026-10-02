import numpy as np
from numpy.typing import NDArray

def jensenshannon(
    p: NDArray[np.float64], q: NDArray[np.float64], **kwargs: object
) -> float: ...
