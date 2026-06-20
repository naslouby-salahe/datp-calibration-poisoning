from __future__ import annotations

from datp.core.provenance import hash_file, source_hash
from datp.validation.results import (
    _METRICS_SOURCE_FILES,
    _SCORING_SOURCE_FILES,
    _THRESHOLD_SOURCE_FILES,
)


class TestProvenanceSourcePaths:
    """Source files hashed into provenance must exist; a stale path makes
    hash_file return the 'MISSING' sentinel, silently breaking traceability."""

    def test_all_provenance_source_files_exist(self) -> None:
        all_files = (
            *_SCORING_SOURCE_FILES,
            *_THRESHOLD_SOURCE_FILES,
            *_METRICS_SOURCE_FILES,
        )
        missing = [str(p) for p in all_files if hash_file(p) == "MISSING"]
        assert not missing, f"provenance source files not found: {missing}"

    def test_provenance_hashes_are_not_missing_sentinel(self) -> None:
        for group in (
            _SCORING_SOURCE_FILES,
            _THRESHOLD_SOURCE_FILES,
            _METRICS_SOURCE_FILES,
        ):
            digest = source_hash(list(group))
            all_missing = source_hash([p.with_suffix(".does_not_exist") for p in group])
            assert digest != all_missing
