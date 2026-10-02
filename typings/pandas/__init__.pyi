from collections.abc import Mapping, Sequence
from os import PathLike
from typing import Any

class DataFrame:
    def __init__(
        self,
        data: Sequence[Mapping[str, object]] | Mapping[str, object] | None = ...,
        **kwargs: Any,
    ) -> None: ...
    def to_csv(
        self,
        path_or_buf: str | PathLike[str],
        *,
        index: bool = ...,
        **kwargs: Any,
    ) -> None: ...
