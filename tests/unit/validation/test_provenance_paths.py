"""Tests verifying git/source code path references and their hash validity for provenance logs."""

from __future__ import annotations

from datp.core.provenance import hash_file, source_hash
from datp.validation.results import (
    METRICS_SOURCE_FILES,
    SCORING_SOURCE_FILES,
    THRESHOLD_SOURCE_FILES,
)


class TestProvenanceSourcePaths:
    """Tests verifying source files lists and their non-empty hash digests."""

    def test_all_provenance_source_files_exist(self) -> None:
        """Verify that all files tracked under provenance source file paths exist on disk."""
        all_files = (
            *SCORING_SOURCE_FILES,
            *THRESHOLD_SOURCE_FILES,
            *METRICS_SOURCE_FILES,
        )
        missing = [str(p) for p in all_files if hash_file(p) == "MISSING"]
        assert not missing, f"provenance source files not found: {missing}"

    def test_provenance_hashes_are_not_missing_sentinel(self) -> None:
        """Verify that the generated source hashes do not match the missing file sentinel hash."""
        for group in (
            SCORING_SOURCE_FILES,
            THRESHOLD_SOURCE_FILES,
            METRICS_SOURCE_FILES,
        ):
            digest = source_hash(list(group))
            all_missing = source_hash([p.with_suffix(".does_not_exist") for p in group])
            assert digest != all_missing
