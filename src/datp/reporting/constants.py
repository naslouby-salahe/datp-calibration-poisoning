from __future__ import annotations

from datp.types import (
    NarrativeText,
    PoisonFraction,
    SchemaVersion,
)

from datp.core.enums import MetricName, NBaIoTDevice
from datp.reporting.enums import ReportTerm

NBAIOT_DEVICE_SHORT_LABELS: dict[NBaIoTDevice, NarrativeText] = {
    NBaIoTDevice.DANMINI_DOORBELL: "Danmini DB",
    NBaIoTDevice.ECOBEE_THERMOSTAT: "Ecobee Tstat",
    NBaIoTDevice.ENNIO_DOORBELL: "Ennio DB",
    NBaIoTDevice.PHILIPS_B120N10_BABY_MONITOR: "Philips B120N10",
    NBaIoTDevice.PROVISION_PT_737E_SECURITY_CAMERA: "Prov. PT-737E",
    NBaIoTDevice.PROVISION_PT_838_SECURITY_CAMERA: "Prov. PT-838",
    NBaIoTDevice.SAMSUNG_SNH_1011_N_WEBCAM: "Samsung SNH",
    NBaIoTDevice.SIMPLEHOME_XCS7_1002_WHT_SECURITY_CAMERA: "SH XCS7-1002",
    NBaIoTDevice.SIMPLEHOME_XCS7_1003_WHT_SECURITY_CAMERA: "SH XCS7-1003",
}


REPORTING_AUDIT_SCHEMA_VERSION: SchemaVersion = "1"
SEED_SELECTION_RULE: NarrativeText = (
    "training seed whose GLOBAL_THRESHOLD CV(FPR) is the lower median across all training seeds"
)
CLIENT_SELECTION_RULE: NarrativeText = (
    "clients with the lowest, median and highest GLOBAL_THRESHOLD FPR in the representative seed"
)
POISONING_FIGURE_FRACTION: PoisonFraction = 0.40
NOT_CONFIRMATORY_WARNING: NarrativeText = (
    "Representative seed only; descriptive evidence, not confirmatory."
)

METRIC_DEFINITIONS: dict[MetricName | ReportTerm, NarrativeText] = {
    MetricName.WORST_BA: "Minimum per-client balanced accuracy, (TPR + TNR) / 2, over eligible clients with complete evaluation.",
    MetricName.P10_MACRO_F1: "10th percentile of per-client macro-F1 (mean of benign-class and attack-class F1) over eligible clients with complete evaluation.",
    MetricName.CV_FPR: "Population coefficient of variation (std with ddof=0 divided by mean) of per-client FPR over eligible clients.",
    MetricName.DELTA_CV_FPR: "CV(FPR) under the poisoned thresholds minus CV(FPR) under the clean thresholds, same fleet and seed.",
    MetricName.VICTIM_DELTA_TPR: "Victim TPR under the poisoned threshold minus TPR under the clean threshold.",
    MetricName.VICTIM_DELTA_FPR: "Victim FPR under the poisoned threshold minus FPR under the clean threshold.",
    MetricName.VICTIM_DELTA_FP: "Victim count of benign test samples above the threshold, poisoned minus clean.",
    MetricName.VICTIM_DELTA_FN: "Victim count of attack test samples at or below the threshold, poisoned minus clean.",
    MetricName.NONVICTIM_MEAN_DELTA_TPR: "Mean over eligible non-victim clients of TPR change under the poisoned thresholds.",
    MetricName.NONVICTIM_WORST_DELTA_TPR: "Most negative per-client TPR change among eligible non-victim clients.",
    MetricName.NONVICTIM_MEAN_DELTA_FPR: "Mean over eligible non-victim clients of FPR change under the poisoned thresholds.",
    MetricName.NONVICTIM_WORST_DELTA_FPR: "Most positive per-client FPR change among eligible non-victim clients.",
    MetricName.NONVICTIM_DELTA_FP_TOTAL: "Total change in false-positive count over eligible non-victim clients.",
    MetricName.NONVICTIM_DELTA_FN_TOTAL: "Total change in missed-detection count over eligible non-victim clients.",
    ReportTerm.FIXED_CLUSTER: "CLUSTER_THRESHOLD thresholds where clean cluster assignments stay frozen and per-cluster means are taken over poisoned per-client quantiles.",
    MetricName.DELTA_TAU_BOUND_UTILIZATION: "Threshold shift divided by the distance from the clean threshold to the extreme victim-local benign calibration score in the attack direction.",
    MetricName.CAL_DUPLICATE_RATE: "Fraction of calibration entries repeating an earlier value.",
    ReportTerm.CELL: "One (policy, objective, source, fraction, victim, training seed) row of the bounded sweep; rows sharing a training seed are not independent.",
    ReportTerm.SEED_AGGREGATE: "Mean over victims of a row metric within one training seed; the inferential unit.",
}
