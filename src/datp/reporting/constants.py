"""Canonical reporting constants: device labels, figure specs, alpha display order."""

from __future__ import annotations

# Short display labels for N-BaIoT device client IDs used in figures 1 and 2.
NBAIOT_DEVICE_SHORT_LABELS: dict[str, str] = {
    "Danmini_Doorbell": "Danmini DB",
    "Ecobee_Thermostat": "Ecobee Tstat",
    "Ennio_Doorbell": "Ennio DB",
    "Philips_B120N10_Baby_Monitor": "Philips B120N10",
    "Provision_PT_737E_Security_Camera": "Prov. PT-737E",
    "Provision_PT_838_Security_Camera": "Prov. PT-838",
    "Samsung_SNH_1011_N_Webcam": "Samsung SNH",
    "SimpleHome_XCS7_1002_WHT_Security_Camera": "SH XCS7-1002",
    "SimpleHome_XCS7_1003_WHT_Security_Camera": "SH XCS7-1003",
}

# Canonical figure filename stems — seed suffix appended by figure1 only.
FIGURE1_STEM = "figure1_seed"  # completed by generate_figure1 with seed number
FIGURE2_STEM = "figure2_ecdf"
FIGURE3_STEM = "figure3_boxplots"
FIGURE4_STEM = "figure4_alpha_sweep"

REPORTING_AUDIT_SCHEMA_VERSION: str = "1"

# Canonical warning text for representative-seed figures (Figures 1 and 2).
NOT_CONFIRMATORY_WARNING: str = (
    "Representative seed only; descriptive evidence, not confirmatory."
)
