import json
import logging
from dataclasses import dataclass, field
from porto_write.constants import DEFAULT_MAX_BACKUPS, PROJECTS_DIR, SETTINGS_FILE

logger = logging.getLogger(__name__)


@dataclass
class AppSettings:
    log_level: str = "none"               # "detailed" | "light" | "none"
    last_directory: str = ""
    last_format: str = "epub"           # "epub" | "md" | "docx"
    window_width: int = 1200
    window_height: int = 800
    editor_font: str = "Georgia"
    editor_font_size: int = 12
    zoom_steps: int = 0
    display_text_color: str = "#000000"
    display_bg_color: str = "#ffffff"
    editor_margin_left: int = 50
    editor_margin_right: int = 50
    text_margin_chars: int = 0           # 0 = disabled, > 0 = character-width margin
    dynamic_margins: bool = True
    max_content_width: int = 65
    autosave_interval_minutes: int = 5
    emergency_backup_enabled: bool = False
    recent_files: list = field(default_factory=list)
    projects_dir: str = field(default_factory=lambda: PROJECTS_DIR)
    default_max_backups: int = DEFAULT_MAX_BACKUPS
    show_beta_warning: bool = True
    beta_warning_initials: str = ""
    export_platform: str = "kindle"
    words_per_page: int = 275
    tooltips_enabled: bool = True
    
    # Ebook Reading Mode (S22.4)
    ebook_device: str = "Kindle Paperwhite"
    ebook_theme: str = "Paperwhite"
    ebook_line_height: float = 1.5
    ebook_margin: int = 0
    ebook_cpl: int = 55

    # App Theme (F9)
    app_theme: str = "System"

    # Update check
    check_updates_on_startup: bool = True

    def load(self) -> "AppSettings":
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.log_level            = data.get("log_level", self.log_level)
            self.last_directory       = data.get("last_directory", self.last_directory)
            self.last_format          = data.get("last_format", self.last_format)
            self.window_width         = int(data.get("window_width", self.window_width))
            self.window_height        = int(data.get("window_height", self.window_height))
            self.editor_font          = data.get("editor_font", self.editor_font)
            self.editor_font_size     = int(data.get("editor_font_size", self.editor_font_size))
            self.zoom_steps           = int(data.get("zoom_steps", self.zoom_steps))
            self.display_text_color   = data.get("display_text_color", self.display_text_color)
            self.display_bg_color     = data.get("display_bg_color", self.display_bg_color)
            self.editor_margin_left   = int(data.get("editor_margin_left", self.editor_margin_left))
            self.editor_margin_right  = int(data.get("editor_margin_right", self.editor_margin_right))
            self.text_margin_chars    = int(data.get("text_margin_chars", self.text_margin_chars))
            self.dynamic_margins      = bool(data.get("dynamic_margins", self.dynamic_margins))
            self.max_content_width    = int(data.get("max_content_width", self.max_content_width))
            self.autosave_interval_minutes = int(data.get("autosave_interval_minutes", self.autosave_interval_minutes))
            self.emergency_backup_enabled  = bool(data.get("emergency_backup_enabled", self.emergency_backup_enabled))
            self.recent_files         = data.get("recent_files", self.recent_files)
            self.projects_dir         = data.get("projects_dir", self.projects_dir)
            self.default_max_backups  = int(data.get("default_max_backups", self.default_max_backups))
            self.show_beta_warning    = bool(data.get("show_beta_warning", self.show_beta_warning))
            self.beta_warning_initials = data.get("beta_warning_initials", self.beta_warning_initials)
            self.export_platform      = data.get("export_platform", self.export_platform)
            self.words_per_page       = int(data.get("words_per_page", self.words_per_page))
            self.tooltips_enabled     = bool(data.get("tooltips_enabled", self.tooltips_enabled))
            
            self.ebook_device         = data.get("ebook_device", self.ebook_device)
            self.ebook_theme          = data.get("ebook_theme", self.ebook_theme)
            self.ebook_line_height    = float(data.get("ebook_line_height", self.ebook_line_height))
            self.ebook_margin         = int(data.get("ebook_margin", self.ebook_margin))
            self.ebook_cpl            = int(data.get("ebook_cpl", self.ebook_cpl))
            self.app_theme            = data.get("app_theme", self.app_theme)
            self.check_updates_on_startup = bool(data.get("check_updates_on_startup", self.check_updates_on_startup))
        except (FileNotFoundError, json.JSONDecodeError, ValueError):
            pass
        logger.debug("Settings loaded")
        return self

    def save(self) -> None:
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "log_level":            self.log_level,
                    "last_directory":       self.last_directory,
                    "last_format":          self.last_format,
                    "window_width":         self.window_width,
                    "window_height":        self.window_height,
                    "editor_font":          self.editor_font,
                    "editor_font_size":     self.editor_font_size,
                    "zoom_steps":           self.zoom_steps,
                    "display_text_color":   self.display_text_color,
                    "display_bg_color":     self.display_bg_color,
                    "editor_margin_left":   self.editor_margin_left,
                    "editor_margin_right":  self.editor_margin_right,
                    "text_margin_chars":    self.text_margin_chars,
                    "dynamic_margins":      self.dynamic_margins,
                    "max_content_width":    self.max_content_width,
                    "autosave_interval_minutes": self.autosave_interval_minutes,
                    "emergency_backup_enabled": self.emergency_backup_enabled,
                    "recent_files":         self.recent_files,
                    "projects_dir":         self.projects_dir,
                    "default_max_backups":  self.default_max_backups,
                    "show_beta_warning":    self.show_beta_warning,
                    "beta_warning_initials": self.beta_warning_initials,
                    "export_platform":      self.export_platform,
                    "words_per_page":       self.words_per_page,
                    "tooltips_enabled":     self.tooltips_enabled,
                    "ebook_device":         self.ebook_device,
                    "ebook_theme":          self.ebook_theme,
                    "ebook_line_height":    self.ebook_line_height,
                    "ebook_margin":         self.ebook_margin,
                    "ebook_cpl":            self.ebook_cpl,
                    "app_theme":            self.app_theme,
                    "check_updates_on_startup": self.check_updates_on_startup,
                }, f, indent=2)
            logger.debug("Settings saved")
        except Exception as exc:
            logger.error("Could not save settings: %s", exc)


    def add_recent_file(self, path: str, max_recent: int = 10) -> None:
        if path in self.recent_files:
            self.recent_files.remove(path)
        self.recent_files.insert(0, path)
        self.recent_files = self.recent_files[:max_recent]
        self.save()
