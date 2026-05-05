import logging
from porto_write.constants import LOG_FILE_DETAILED, LOG_FILE_LIGHT

_LEVELS = {
    "detailed": logging.DEBUG,
    "light":    logging.WARNING,
    "none":     None,
}

_fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")


def setup_logging(level: str = "light") -> None:
    """Configure root logger for the chosen level (detailed/light/none)."""
    root = logging.getLogger()
    root.handlers.clear()

    numeric = _LEVELS.get(level)
    if numeric is None:
        root.addHandler(logging.NullHandler())
        root.setLevel(logging.CRITICAL + 1)
        return

    root.setLevel(numeric)

    log_path = LOG_FILE_DETAILED if level == "detailed" else LOG_FILE_LIGHT
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setFormatter(_fmt)
    fh.setLevel(numeric)
    root.addHandler(fh)

    if level == "detailed":
        ch = logging.StreamHandler()
        ch.setFormatter(_fmt)
        ch.setLevel(logging.DEBUG)
        root.addHandler(ch)
