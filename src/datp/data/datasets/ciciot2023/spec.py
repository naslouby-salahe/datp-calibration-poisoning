from __future__ import annotations

from pathlib import Path

from datp.data.specs import (
    CapPolicy,
    CapStrategy,
    ClientIdentity,
    DatasetID,
    DatasetSpec,
    RawLayout,
    SplitPolicy,
    SplitPolicyKind,
    SplitPolicyRole,
)

LABEL_COLUMN: str = "Label"
BENIGN_LABEL: str = "BENIGN"

FEATURE_COLUMNS: tuple[str, ...] = (
    "Header_Length",
    "Protocol Type",
    "Time_To_Live",
    "Rate",
    "fin_flag_number",
    "syn_flag_number",
    "rst_flag_number",
    "psh_flag_number",
    "ack_flag_number",
    "ece_flag_number",
    "cwr_flag_number",
    "ack_count",
    "syn_count",
    "fin_count",
    "rst_count",
    "HTTP",
    "HTTPS",
    "DNS",
    "Telnet",
    "SMTP",
    "SSH",
    "IRC",
    "TCP",
    "UDP",
    "DHCP",
    "ARP",
    "ICMP",
    "IGMP",
    "IPv",
    "LLC",
    "Tot sum",
    "Min",
    "Max",
    "AVG",
    "Std",
    "Tot size",
    "IAT",
    "Number",
    "Variance",
)

FEATURE_COUNT: int = 39
EXPECTED_COLUMNS: tuple[str, ...] = (*FEATURE_COLUMNS, LABEL_COLUMN)

NUM_CLIENTS: int = 63

RAW_CSV_DIR = "CSV"
RAW_MERGED_DIR = "MERGED_CSV"
RAW_MERGED_PATTERN = "Merged*.csv"

CAP_TOTAL: int = 50000
CAP_ATTACK_RESERVE: int = 10000

CAL_FRACTION: float = 0.15

TEST_ATTACK_LABELS_ARTIFACT: str = "test_attack_labels.parquet"

ATTACK_FAMILIES: tuple[str, ...] = (
    "DDoS",
    "DoS",
    "Mirai",
    "Recon",
    "Spoofing",
    "Web-based",
    "Brute-Force",
)

_ATTACK_FAMILY_PREFIXES: tuple[tuple[str, str], ...] = (
    ("DDOS", "DDoS"),
    ("DOS", "DoS"),
    ("MIRAI", "Mirai"),
    ("RECON", "Recon"),
    ("SPOOFING", "Spoofing"),
    ("BRUTEFORCE", "Brute-Force"),
    ("BRUTE_FORCE", "Brute-Force"),
)

_KNOWN_WEBATTACK_LABELS: frozenset[str] = frozenset(
    {
        "XSS",
        "SQL_INJECTION",
        "SQLINJECTION",
        "COMMANDINJECTION",
        "BACKDOOR_MALWARE",
        "MITM",
        "BROWSERHIJACKING",
        "UPLOADING_ATTACK",
    }
)

_KNOWN_RECON_LABELS: frozenset[str] = frozenset(
    {
        "VULNERABILITYSCAN",
    }
)

_KNOWN_SPOOFING_LABELS: frozenset[str] = frozenset(
    {
        "DNS_SPOOFING",
        "MITM_ARPSPOOFING",
    }
)

_KNOWN_BRUTE_FORCE_LABELS: frozenset[str] = frozenset(
    {
        "DICTIONARYBRUTEFORCE",
    }
)


def attack_family(label: str) -> str | None:
    """Return the attack family for a raw CICIoT2023 label, or None if unknown."""
    normalized = label.strip().replace("-", "_").upper()
    for prefix, family in _ATTACK_FAMILY_PREFIXES:
        if normalized.startswith(prefix):
            return family
    if normalized in _KNOWN_WEBATTACK_LABELS:
        return "Web-based"
    if normalized in _KNOWN_RECON_LABELS:
        return "Recon"
    if normalized in _KNOWN_SPOOFING_LABELS:
        return "Spoofing"
    if normalized in _KNOWN_BRUTE_FORCE_LABELS:
        return "Brute-Force"
    return None


CICIOT2023_SPEC = DatasetSpec(
    id=DatasetID.CICIOT2023,
    display_name="CICIoT2023",
    processed_slug=DatasetID.CICIOT2023.value,
    feature_count=FEATURE_COUNT,
    feature_columns=FEATURE_COLUMNS,
    label_column=LABEL_COLUMN,
    benign_label=BENIGN_LABEL,
    client_identity=ClientIdentity.MERGED_FILE,
    raw_layout=RawLayout(root_slug="CIC_IOT_Dataset2023"),
    split_policy=SplitPolicy(
        name=SplitPolicyKind.STRATIFIED_RANDOM,
        calibration_benign_only=True,
        chronological=False,
        contiguous_gaps=False,
        ratios={
            SplitPolicyRole.TRAIN: 0.70,
            SplitPolicyRole.CAL: CAL_FRACTION,
            SplitPolicyRole.TEST_BENIGN: 0.15,
        },
    ),
    cap_policy=CapPolicy(
        total=CAP_TOTAL,
        attack_reserve=CAP_ATTACK_RESERVE,
        strategy=CapStrategy.ATTACK_PRESERVING,
    ),
    expected_client_count=NUM_CLIENTS,
)


def merged_csv_root(raw_dir: Path) -> Path:
    """Return the merged-CSV subdirectory of the CICIoT2023 raw root."""
    return raw_dir / RAW_CSV_DIR / RAW_MERGED_DIR
