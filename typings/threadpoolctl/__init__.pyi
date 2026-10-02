from types import TracebackType
from typing import Literal

class threadpool_limits:
    def __init__(
        self,
        limits: int | None = ...,
        user_api: Literal["blas", "openmp"] | None = ...,
    ) -> None: ...
    def __enter__(self) -> threadpool_limits: ...
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> Literal[False] | None: ...
