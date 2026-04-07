"""
Wake-on-LAN logic for wakeonlan premium tab.
Reads config from backend config.json (paths.wol_csv); targets from that CSV.
Sends magic packet via UDP; no external wakeonlan/etherwake dependency.
"""

import csv
import json
import re
import socket
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).resolve().parent / "config.json"
CSV_HEADER = "name,mac,broadcast"
DEFAULT_BROADCAST = "255.255.255.255"
WOL_PORT = 9


def _load_config() -> dict:
    """Load paths from config.json (infinite-index style)."""
    if not CONFIG_PATH.exists():
        logger.warning("WoL config.json not found, using default CSV path", extra={"config_path": str(CONFIG_PATH)})
        return {"paths": {"wol_csv": "/var/www/homeserver/premium/wakeonlan.csv"}}
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def get_wol_csv_path() -> Path:
    """Return CSV path from config."""
    config = _load_config()
    return Path(config.get("paths", {}).get("wol_csv", "/var/www/homeserver/premium/wakeonlan.csv"))


WOL_CSV = get_wol_csv_path()

MAC_RE = re.compile(
    r"^([0-9a-fA-F]{2})[:-]([0-9a-fA-F]{2})[:-]([0-9a-fA-F]{2})[:-]"
    r"([0-9a-fA-F]{2})[:-]([0-9a-fA-F]{2})[:-]([0-9a-fA-F]{2})$"
)


def normalize_mac(mac: str) -> bytes:
    """Parse MAC string to 6 bytes. Raises ValueError if invalid."""
    m = MAC_RE.match(mac.strip())
    if not m:
        raise ValueError(f"Invalid MAC format: {mac!r}")
    return bytes(int(g, 16) for g in m.groups())


def magic_packet(mac_bytes: bytes) -> bytes:
    """Build WoL magic packet: 6x 0xff + 16x MAC."""
    if len(mac_bytes) != 6:
        raise ValueError("MAC must be 6 bytes")
    return b"\xff" * 6 + mac_bytes * 16


def is_valid_ipv4(addr: str) -> bool:
    try:
        parts = addr.strip().split(".")
        if len(parts) != 4:
            return False
        return all(0 <= int(p) <= 255 for p in parts)
    except (ValueError, AttributeError):
        return False


def load_targets(csv_path: Path | None = None) -> list[dict]:
    """
    Load targets from CSV. Returns list of {name, mac_str, broadcast}.
    csv_path defaults to premium/wakeonlan.csv.
    Raises FileNotFoundError if CSV missing; ValueError on invalid row.
    """
    path = csv_path or WOL_CSV
    if not path.exists():
        logger.warning("WoL CSV not found", extra={"path": str(path)})
        raise FileNotFoundError(f"CSV not found: {path}")
    if not path.is_file():
        raise FileNotFoundError(f"Not a file: {path}")

    targets = []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, skipinitialspace=True)
        if not reader.fieldnames or "mac" not in (reader.fieldnames or []):
            raise ValueError("CSV must have header with at least 'mac' column")
        for i, row in enumerate(reader, start=2):
            mac_raw = (row.get("mac") or "").strip()
            if not mac_raw:
                raise ValueError(f"Row {i}: missing mac")
            try:
                mac_bytes = normalize_mac(mac_raw)
            except ValueError as e:
                raise ValueError(f"Row {i}: {e}") from e
            broadcast = (row.get("broadcast") or "").strip() or DEFAULT_BROADCAST
            if not is_valid_ipv4(broadcast):
                raise ValueError(f"Row {i}: invalid broadcast {broadcast!r}")
            name = (row.get("name") or mac_raw).strip()
            targets.append({
                "name": name,
                "mac": mac_bytes,
                "mac_str": ":".join(f"{b:02x}" for b in mac_bytes),
                "broadcast": broadcast,
            })
    return targets


def send_wol(mac_bytes: bytes, broadcast: str) -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    try:
        sock.sendto(magic_packet(mac_bytes), (broadcast, WOL_PORT))
    finally:
        sock.close()


def wake_targets(targets: list[dict], names: list[str] | None = None, wake_all: bool = False) -> list[dict]:
    """
    Send WoL to selected targets. If wake_all, send to all; else send to those in names.
    Returns list of {name, mac_str, broadcast} that were sent to.
    """
    if wake_all:
        to_wake = list(targets)
    elif names:
        to_wake = [t for t in targets if t["name"] in names]
        missing = set(names) - {t["name"] for t in to_wake}
        if missing:
            raise ValueError(f"Unknown target(s): {', '.join(sorted(missing))}")
    else:
        return []

    for t in to_wake:
        send_wol(t["mac"], t["broadcast"])
        logger.info(
            "Sent WoL",
            extra={"target_name": t["name"], "mac": t["mac_str"], "broadcast": t["broadcast"]},
        )
    return to_wake


def broadcast_from_ip(ip: str) -> str:
    """Derive /24 broadcast from IPv4 address."""
    parts = ip.strip().split(".")
    if len(parts) != 4:
        return DEFAULT_BROADCAST
    try:
        return f"{parts[0]}.{parts[1]}.{parts[2]}.255"
    except (IndexError, TypeError):
        return DEFAULT_BROADCAST


def ensure_csv_with_header(csv_path: Path | None = None) -> None:
    """Create CSV with header if it does not exist."""
    path = csv_path or get_wol_csv_path()
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(CSV_HEADER + "\n", encoding="utf-8")
    logger.info("Created WoL CSV with header", extra={"path": str(path)})


def append_target(name: str, mac: str, broadcast: str | None = None, csv_path: Path | None = None) -> None:
    """Append one target row to CSV. Validates MAC and broadcast. Creates file with header if missing."""
    path = csv_path or get_wol_csv_path()
    ensure_csv_with_header(path)
    mac_bytes = normalize_mac(mac)
    bc = (broadcast or "").strip() or DEFAULT_BROADCAST
    if not is_valid_ipv4(bc):
        raise ValueError(f"Invalid broadcast: {bc!r}")
    name_clean = (name or mac).strip()
    with path.open("a", newline="", encoding="utf-8") as f:
        f.write(f"{name_clean},{':'.join(f'{b:02x}' for b in mac_bytes)},{bc}\n")
    logger.info("Appended WoL target", extra={"target_name": name_clean, "mac": mac})


def remove_target(name: str, csv_path: Path | None = None) -> None:
    """Remove one target by name from CSV. Rewrites file without that row. Raises ValueError if name not found."""
    path = csv_path or get_wol_csv_path()
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {path}")
    targets = load_targets(path)
    matching = [t for t in targets if t["name"] == name]
    if not matching:
        raise ValueError(f"Unknown target: {name!r}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        f.write(CSV_HEADER + "\n")
        for t in targets:
            if t["name"] != name:
                f.write(f"{t['name']},{t['mac_str']},{t['broadcast']}\n")
    logger.info("Removed WoL target", extra={"target_name": name})
