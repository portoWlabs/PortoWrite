import hashlib
import json
import logging
import os
from datetime import datetime
from enum import Enum

from porto_write.constants import APP_EDITION, LICENCE_FILE

logger = logging.getLogger(__name__)


class Edition(str, Enum):
    FREE       = "free"
    SUPPORTER  = "supporter"   # Ko-fi donation — personal use
    COMMERCIAL = "commercial"  # commercial use


PRO_FEATURES: list[str] = [
    "docx_export",
    "md_export",
    "custom_styles",
    "footnotes",
    "hyperlinks",
    "track_changes",
    "kobo_export",
    "apple_books_export",
    "version_comparison",
]

# ── Key validation — salts MUST match keygen.py ──────────────────────────────
_SALT_SUP  = "PortoWrite_Supporter_2026"
_SALT_COM  = "PortoWrite_Commercial_2026"
_PEPPER    = b"PortoWriteApp"
_ITERS     = 75_000


def _fmt_key(raw_hex: str) -> str:
    h = raw_hex[:16].upper()
    return f"{h[:4]}-{h[4:8]}-{h[8:12]}-{h[12:16]}"


def _derive(identifier: str, salt: str) -> str:
    raw = hashlib.pbkdf2_hmac(
        "sha256",
        (identifier.strip().lower() + salt).encode("utf-8"),
        _PEPPER,
        iterations=_ITERS,
    )
    return _fmt_key(raw.hex())


def validate_supporter_key(email: str, key: str) -> bool:
    return _derive(email, _SALT_SUP) == key.strip().upper()


def validate_commercial_key(name: str, key: str) -> bool:
    return _derive(name, _SALT_COM) == key.strip().upper()


# ── Licence file persistence ──────────────────────────────────────────────────

def _load_licence_file() -> dict | None:
    try:
        if os.path.exists(LICENCE_FILE):
            with open(LICENCE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.warning("Could not read licence file: %s", e)
    return None


def _save_licence_file(data: dict):
    with open(LICENCE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def activate_supporter(email: str, key: str) -> bool:
    """Validate and persist a Supporter key. Returns True on success."""
    if not validate_supporter_key(email, key):
        return False
    _save_licence_file({
        "tier": "supporter",
        "identifier": email.strip().lower(),
        "key": key.strip().upper(),
        "activated": datetime.now().strftime("%Y-%m-%d"),
    })
    logger.info("Supporter licence activated for %s", email)
    return True


def activate_commercial(name: str, key: str) -> bool:
    """Validate and persist a Commercial key. Returns True on success."""
    if not validate_commercial_key(name, key):
        return False
    _save_licence_file({
        "tier": "commercial",
        "identifier": name.strip(),
        "key": key.strip().upper(),
        "activated": datetime.now().strftime("%Y-%m-%d"),
    })
    logger.info("Commercial licence activated for %s", name)
    return True


def deactivate_licence():
    """Remove the stored licence (revert to Free)."""
    if os.path.exists(LICENCE_FILE):
        os.remove(LICENCE_FILE)


# ── Edition resolution ────────────────────────────────────────────────────────

def get_edition() -> Edition:
    """Return the active edition — licence file takes precedence over APP_EDITION."""
    data = _load_licence_file()
    if data:
        tier = data.get("tier", "")
        if tier == "commercial":
            return Edition.COMMERCIAL
        if tier == "supporter":
            return Edition.SUPPORTER
    # Fall back to compile-time constant (beta ships as "pro" → treat as supporter)
    try:
        raw = APP_EDITION.lower()
        if raw == "pro":
            return Edition.SUPPORTER
        return Edition(raw)
    except ValueError:
        logger.warning("Unknown APP_EDITION '%s' — defaulting to FREE.", APP_EDITION)
        return Edition.FREE


def is_pro() -> bool:
    return get_edition() in (Edition.SUPPORTER, Edition.COMMERCIAL)


def is_commercial() -> bool:
    return get_edition() == Edition.COMMERCIAL


def get_edition_label() -> str:
    edition = get_edition()
    data = _load_licence_file()
    match edition:
        case Edition.FREE:
            return "Free (Beta)"
        case Edition.SUPPORTER:
            identifier = data.get("identifier", "") if data else ""
            return f"Supporter ({identifier})" if identifier else "Supporter"
        case Edition.COMMERCIAL:
            identifier = data.get("identifier", "") if data else ""
            return f"Commercial — {identifier}" if identifier else "Commercial"
        case _:
            return "Unknown"


def check_feature(feature_name: str) -> bool:
    return is_pro() or feature_name not in PRO_FEATURES
