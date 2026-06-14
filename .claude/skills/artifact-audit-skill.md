# artifact-audit-skill

## Purpose

Validate artifact paths, files, manifests, markers, and result layout.

## Checks

1. Canonical path used
2. Required parent directory exists
3. Required input artifact exists
4. Empty files are rejected
5. Temporary files are ignored
6. Partial files are not treated as complete
7. Manifest is valid
8. Config provenance is present
9. Failure markers are meaningful
10. Resume behavior is safe

## Required Output

1. Valid artifacts
2. Missing artifacts
3. Invalid artifacts
4. Unsafe resume risks
5. Required fixes