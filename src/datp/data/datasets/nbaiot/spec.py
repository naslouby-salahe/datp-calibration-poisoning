from __future__ import annotations

from datp.types import (
    FeatureCount,
    Ratio,
    SampleCount,
)


from datp.data.specs import (
    DatasetID,
    DatasetSpec,
    SplitPolicy,
    SplitPolicyRole,
)
from datp.core.enums import (
    NBaIoTAttackFamily,
    NBaIoTDevice,
    NBaIoTDeviceFamily,
)

FEATURE_COUNT: FeatureCount = 115

DEVICE_DIRS: tuple[NBaIoTDevice, ...] = (
    NBaIoTDevice.DANMINI_DOORBELL,
    NBaIoTDevice.ECOBEE_THERMOSTAT,
    NBaIoTDevice.ENNIO_DOORBELL,
    NBaIoTDevice.PHILIPS_B120N10_BABY_MONITOR,
    NBaIoTDevice.PROVISION_PT_737E_SECURITY_CAMERA,
    NBaIoTDevice.PROVISION_PT_838_SECURITY_CAMERA,
    NBaIoTDevice.SAMSUNG_SNH_1011_N_WEBCAM,
    NBaIoTDevice.SIMPLEHOME_XCS7_1002_WHT_SECURITY_CAMERA,
    NBaIoTDevice.SIMPLEHOME_XCS7_1003_WHT_SECURITY_CAMERA,
)

NUM_DEVICES: SampleCount = len(DEVICE_DIRS)
DEVICE_FAMILY_MAP: dict[NBaIoTDevice, NBaIoTDeviceFamily] = {
    NBaIoTDevice.DANMINI_DOORBELL: NBaIoTDeviceFamily.DOORBELL,
    NBaIoTDevice.ECOBEE_THERMOSTAT: NBaIoTDeviceFamily.OTHER,
    NBaIoTDevice.ENNIO_DOORBELL: NBaIoTDeviceFamily.DOORBELL,
    NBaIoTDevice.PHILIPS_B120N10_BABY_MONITOR: NBaIoTDeviceFamily.OTHER,
    NBaIoTDevice.PROVISION_PT_737E_SECURITY_CAMERA: NBaIoTDeviceFamily.CAMERA,
    NBaIoTDevice.PROVISION_PT_838_SECURITY_CAMERA: NBaIoTDeviceFamily.CAMERA,
    NBaIoTDevice.SAMSUNG_SNH_1011_N_WEBCAM: NBaIoTDeviceFamily.CAMERA,
    NBaIoTDevice.SIMPLEHOME_XCS7_1002_WHT_SECURITY_CAMERA: NBaIoTDeviceFamily.CAMERA,
    NBaIoTDevice.SIMPLEHOME_XCS7_1003_WHT_SECURITY_CAMERA: NBaIoTDeviceFamily.CAMERA,
}

ATTACK_FAMILY_DIRS: tuple[NBaIoTAttackFamily, ...] = (
    NBaIoTAttackFamily.GAFGYT,
    NBaIoTAttackFamily.MIRAI,
)

SPLIT_RATIOS: dict[SplitPolicyRole, Ratio] = {
    SplitPolicyRole.TRAIN: 0.60,
    SplitPolicyRole.GAP1: 0.01,
    SplitPolicyRole.CAL: 0.20,
    SplitPolicyRole.GAP2: 0.01,
}

NBAIOT_SPEC = DatasetSpec(
    id=DatasetID.NBAIOT,
    display_name="N-BaIoT",
    processed_slug=DatasetID.NBAIOT,
    feature_count=FEATURE_COUNT,
    feature_columns=None,
    label_column=None,
    benign_label=None,
    raw_root_slug="N-BaIoT",
    split_policy=SplitPolicy(ratios=SPLIT_RATIOS),
    family_map=DEVICE_FAMILY_MAP,
    device_ids=DEVICE_DIRS,
    attack_family_dirs=ATTACK_FAMILY_DIRS,
    expected_client_count=NUM_DEVICES,
)
