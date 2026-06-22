from __future__ import annotations

from datp.data.specs import (
    ClientIdentity,
    DatasetID,
    DatasetSpec,
    RawLayout,
    SplitPolicy,
    SplitPolicyKind,
    SplitPolicyRole,
)

FEATURE_COUNT: int = 115

CHRONOLOGICAL_SPLIT: bool = True
BENIGN_ONLY_CALIBRATION: bool = True

DEVICE_DIRS: tuple[str, ...] = (
    "Danmini_Doorbell",
    "Ecobee_Thermostat",
    "Ennio_Doorbell",
    "Philips_B120N10_Baby_Monitor",
    "Provision_PT_737E_Security_Camera",
    "Provision_PT_838_Security_Camera",
    "Samsung_SNH_1011_N_Webcam",
    "SimpleHome_XCS7_1002_WHT_Security_Camera",
    "SimpleHome_XCS7_1003_WHT_Security_Camera",
)

NUM_DEVICES: int = len(DEVICE_DIRS)

DEVICE_FAMILY_MAP: dict[str, str] = {
    "Danmini_Doorbell": "doorbell",
    "Ecobee_Thermostat": "other",
    "Ennio_Doorbell": "doorbell",
    "Philips_B120N10_Baby_Monitor": "other",
    "Provision_PT_737E_Security_Camera": "camera",
    "Provision_PT_838_Security_Camera": "camera",
    "Samsung_SNH_1011_N_Webcam": "camera",
    "SimpleHome_XCS7_1002_WHT_Security_Camera": "camera",
    "SimpleHome_XCS7_1003_WHT_Security_Camera": "camera",
}

DEVICE_FAMILIES: frozenset[str] = frozenset(DEVICE_FAMILY_MAP.values())

BENIGN_TRAFFIC_FILE = "benign_traffic.csv"
ATTACK_FAMILY_DIRS: tuple[str, ...] = ("gafgyt_attacks", "mirai_attacks")

SPLIT_RATIOS: dict[SplitPolicyRole, float] = {
    SplitPolicyRole.TRAIN: 0.60,
    SplitPolicyRole.GAP1: 0.01,
    SplitPolicyRole.CAL: 0.20,
    SplitPolicyRole.GAP2: 0.01,
}

BALANCED_TEST_DEFAULT: bool = False

NBAIOT_SPEC = DatasetSpec(
    id=DatasetID.NBAIOT,
    display_name="N-BaIoT",
    processed_slug=DatasetID.NBAIOT.value,
    feature_count=FEATURE_COUNT,
    feature_columns=None,
    label_column=None,
    benign_label=None,
    client_identity=ClientIdentity.DEVICE_DIRECTORY,
    raw_layout=RawLayout(root_slug="N-BaIoT"),
    split_policy=SplitPolicy(
        name=SplitPolicyKind.CHRONOLOGICAL_GAPPED,
        calibration_benign_only=BENIGN_ONLY_CALIBRATION,
        chronological=CHRONOLOGICAL_SPLIT,
        contiguous_gaps=True,
        ratios=SPLIT_RATIOS,
    ),
    cap_policy=None,
    family_map=DEVICE_FAMILY_MAP,
    device_ids=DEVICE_DIRS,
    attack_family_dirs=ATTACK_FAMILY_DIRS,
    expected_client_count=NUM_DEVICES,
)
