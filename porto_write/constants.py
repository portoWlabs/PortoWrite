import os
import sys

APP_NAME = "PortoWrite"
APP_VERSION = "0.9.0 Beta"

# Edition controls feature availability. Values: "free" | "pro" | "commercial"
# Enforcement is not yet implemented — beta ships with all features unlocked.
APP_EDITION = "pro"

# When bundled by PyInstaller, _MEIPASS holds extracted assets; sys.executable is the .exe.
# In dev mode both resolve to the project root.
if getattr(sys, 'frozen', False):
    _bundle_dir = sys._MEIPASS
    _app_dir    = os.path.dirname(sys.executable)
else:
    _bundle_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _app_dir    = _bundle_dir

# App config lives alongside the exe so deleting the install folder is a complete uninstall.
_config_dir = os.path.join(_app_dir, 'data')
os.makedirs(_config_dir, exist_ok=True)

SETTINGS_FILE     = os.path.join(_config_dir, "settings.json")
LICENCE_FILE      = os.path.join(_config_dir, "licence.json")
USER_DICT_FILE    = os.path.join(_config_dir, "user_dict.txt")
LOG_FILE_DETAILED = os.path.join(_app_dir, "portowrite_debug.log")
LOG_FILE_LIGHT    = os.path.join(_app_dir, "portowrite.log")

DICTIONARIES_DIR = os.path.join(_bundle_dir, "dictionaries")

_documents = os.path.join(os.path.expanduser("~"), "Documents")
if not os.path.exists(_documents):
    _documents = os.path.expanduser("~")
PROJECTS_DIR = os.path.join(_documents, "PortoWrite")
os.makedirs(PROJECTS_DIR, exist_ok=True)

DEFAULT_FONT = "Georgia"
DEFAULT_FONT_SIZE = 12
DEFAULT_LOG_LEVEL = "light"
DEFAULT_MAX_BACKUPS = 10

KINDLE_FONTS = [
    "Bookerly", 
    "Caecilia", 
    "Helvetica", 
    "Georgia", 
    "Times New Roman", 
    "Arial", 
    "Courier", 
    "Courier New", 
    "Trebuchet MS", 
    "Vollkorn", 
    "Amazon Ember"
]

SUPPORTED_EXTENSIONS = {
    ".epub": "ePub Document",
    ".md":   "Markdown Document",
    ".docx": "Word Document",
}

# Custom QTextFormat property for storing style names
STYLE_NAME_PROPERTY = 0x1001
DROP_CAP_PROPERTY = 0x20001
