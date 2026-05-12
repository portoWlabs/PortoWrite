import json
from typing import Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from porto_write.constants import APP_VERSION

LATEST_RELEASE_URL = "https://api.github.com/repos/portoWlabs/PortoWrite/releases/latest"


def normalize_version(value: str) -> Tuple[int, ...]:
    """Parse version string to numeric tuple, ignoring any suffix like 'Beta'."""
    version = value.strip().lstrip("vV")
    # Strip non-numeric suffix words (e.g. "0.9.1 Beta" → "0.9.1")
    version = version.split()[0]
    parts = []
    for part in version.split("."):
        number = ""
        for char in part:
            if not char.isdigit():
                break
            number += char
        parts.append(int(number or "0"))
    return tuple(parts)


def is_newer_version(latest: str, current: str = APP_VERSION) -> bool:
    latest_parts = normalize_version(latest)
    current_parts = normalize_version(current)
    width = max(len(latest_parts), len(current_parts))
    latest_parts += (0,) * (width - len(latest_parts))
    current_parts += (0,) * (width - len(current_parts))
    return latest_parts > current_parts


def check_for_update(
    current_version: str = APP_VERSION,
    release_url: str = LATEST_RELEASE_URL,
    timeout: int = 10,
) -> Optional[Tuple[str, bool, str]]:
    """Return (latest_tag, is_newer, html_url) or None on network/parse error."""
    request = Request(
        release_url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"PortoWrite/{current_version}",
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError):
        return None

    latest_version = str(payload.get("tag_name") or "").strip()
    if not latest_version:
        return None

    html_url = str(payload.get("html_url") or "").strip()
    return latest_version, is_newer_version(latest_version, current_version), html_url
