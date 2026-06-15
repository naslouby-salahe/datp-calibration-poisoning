# CP2 Manifests

Store CP2 manifest schemas and concrete manifest instances here (or links to the
real manifests written under `outputs/conference_calibration_poisoning/`).

Expected CP2 manifests (per `docs/DATP_CP_Roadmap.md` §10):
`project_audit_report.json`, `clean_score_artifacts.json`,
`nbaiot_mvp_manifest.json`, `paper_figure_manifest.json`.

A manifest must record: artifact provenance (E=1 enforced, E=5 rejected), reservoir
sampling mode, locked `mu_flag_threshold`, and every derived child seed.
