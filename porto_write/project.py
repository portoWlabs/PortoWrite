import json
import logging
import os
import re
import shutil
from datetime import datetime

from porto_write.constants import DEFAULT_MAX_BACKUPS, PROJECTS_DIR
from porto_write.document import Chapter, PortoDocument, TextBlock
from porto_write.styles import StyleDefinition, StyleRegistry

logger = logging.getLogger(__name__)

_PROJECT_FILE = "project.json"
_AUTOSAVE_FILE = "autosave.json"
_BACKUPS_DIR = "backups"
_VERSIONS_DIR = "versions"


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------

def _style_to_dict(s: StyleDefinition) -> dict:
    return {
        "font_family": s.font_family,
        "font_size": s.font_size,
        "bold": s.bold,
        "italic": s.italic,
        "alignment": s.alignment,
        "space_before": s.space_before,
        "space_after": s.space_after,
        "page_break_before": s.page_break_before,
        "page_break_after": s.page_break_after,
    }


def _style_from_dict(name: str, d: dict) -> StyleDefinition:
    return StyleDefinition(
        name=name,
        font_family=d.get("font_family", "Georgia"),
        font_size=d.get("font_size", 12),
        bold=d.get("bold", False),
        italic=d.get("italic", False),
        alignment=d.get("alignment", "left"),
        space_before=d.get("space_before", 0),
        space_after=d.get("space_after", 6),
        page_break_before=d.get("page_break_before", False),
        page_break_after=d.get("page_break_after", False),
    )


def document_to_dict(doc: PortoDocument, max_backups: int = DEFAULT_MAX_BACKUPS) -> dict:
    return {
        "title": doc.title,
        "author": doc.author,
        "subtitle": doc.subtitle,
        "series_name": doc.series_name,
        "series_number": doc.series_number,
        "description": doc.description,
        "isbn": doc.isbn,
        "publisher": doc.publisher,
        "publish_date": doc.publish_date,
        "language": doc.language,
        "keywords": doc.keywords,
        "contributors": doc.contributors,
        "max_backups": max_backups,
        "metadata": doc.metadata,
        "toc": [entry.to_dict() for entry in doc.toc],
        "styles": {name: _style_to_dict(s) for name, s in
                   ((n, doc.styles.get(n)) for n in doc.styles.names())},
        "chapters": [
            {
                "title": ch.title,
                "blocks": [{"style_name": b.style_name, "text": b.text,
                             "drop_cap": b.drop_cap}
                           for b in ch.blocks],
            }
            for ch in doc.chapters
        ],
    }


def document_from_dict(data: dict) -> tuple[PortoDocument, int]:
    """Returns (PortoDocument, max_backups). Handles backward compatibility."""
    doc = PortoDocument(
        title=data.get("title", "Untitled"),
        author=data.get("author", ""),
        language=data.get("language", "en"),
        subtitle=data.get("subtitle", ""),
        series_name=data.get("series_name", ""),
        series_number=data.get("series_number", 0),
        description=data.get("description", ""),
        isbn=data.get("isbn", ""),
        publisher=data.get("publisher", ""),
        publish_date=data.get("publish_date", ""),
        keywords=data.get("keywords", []),
        contributors=data.get("contributors", []),
    )
    doc.metadata = data.get("metadata", {})

    # Restore TOC
    from porto_write.toc import TocEntry
    doc.toc = [TocEntry.from_dict(t_data) for t in data.get("toc", []) if (t_data := t)]
    # Safety: handle empty list/null
    if not doc.toc:
        doc.toc = []

    # Restore styles (built-ins are re-created by StyleRegistry.__init__;
    # override them if the saved data differs, add any user-defined ones)
    for name, style_data in data.get("styles", {}).items():
        doc.styles.add(_style_from_dict(name, style_data))

    for ch_data in data.get("chapters", []):
        ch = doc.add_chapter(ch_data.get("title", "Chapter"))
        for b_data in ch_data.get("blocks", []):
            blk = ch.add_block(b_data.get("style_name", "Body"), b_data.get("text", ""))
            blk.drop_cap = b_data.get("drop_cap", False)

    max_backups = data.get("max_backups", DEFAULT_MAX_BACKUPS)
    return doc, max_backups


# ---------------------------------------------------------------------------
# NovelProject
# ---------------------------------------------------------------------------

class NovelProject:
    """A folder-based novel project with versioned saves."""

    def __init__(self, project_dir: str) -> None:
        self.project_dir = project_dir
        self.project_file = os.path.join(project_dir, _PROJECT_FILE)
        self.autosave_path = os.path.join(project_dir, _AUTOSAVE_FILE)
        self.backups_dir = os.path.join(project_dir, _BACKUPS_DIR)
        self.max_backups: int = DEFAULT_MAX_BACKUPS
        self.doc: PortoDocument | None = None

    @property
    def name(self) -> str:
        return os.path.basename(self.project_dir)

    @property
    def versions_dir(self) -> str:
        return os.path.join(self.project_dir, _VERSIONS_DIR)

    # --- create / load ---

    @classmethod
    def create(cls, projects_dir: str, title: str, author: str = "",
               language: str = "en", max_backups: int = DEFAULT_MAX_BACKUPS) -> "NovelProject":
        folder_name = _safe_folder_name(title)
        project_dir = os.path.join(projects_dir, folder_name)
        os.makedirs(project_dir, exist_ok=True)
        os.makedirs(os.path.join(project_dir, _BACKUPS_DIR), exist_ok=True)

        proj = cls(project_dir)
        proj.max_backups = max_backups
        proj.doc = PortoDocument(title=title, author=author, language=language)
        proj.save()
        logger.info("Project created: %s", project_dir)
        return proj

    @classmethod
    def load(cls, project_dir: str) -> "NovelProject":
        proj = cls(project_dir)
        proj_file = os.path.join(project_dir, _PROJECT_FILE)
        if not os.path.exists(proj_file):
            raise FileNotFoundError(f"No project.json in {project_dir}")
        with open(proj_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        proj.doc, proj.max_backups = document_from_dict(data)
        os.makedirs(proj.backups_dir, exist_ok=True)
        logger.info("Project loaded: %s", project_dir)
        return proj

    # --- save with backup rotation ---

    def save(self, emergency_backup: bool = False) -> None:
        if self.doc is None:
            raise RuntimeError("No document loaded")
        os.makedirs(self.backups_dir, exist_ok=True)

        if os.path.exists(self.project_file):
            ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            backup_name = f"{ts}.json"
            shutil.copy2(self.project_file, os.path.join(self.backups_dir, backup_name))
            logger.debug("Backup created: %s", backup_name)
            self._prune_backups()

        if emergency_backup and os.path.exists(self.project_file):
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            emergency_path = os.path.join(self.backups_dir, f"emergency_{ts}.json")
            shutil.copy2(self.project_file, emergency_path)
            logger.info("Emergency backup created: %s", emergency_path)

        data = document_to_dict(self.doc, self.max_backups)
        with open(self.project_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info("Project saved: %s", self.project_file)

    # --- autosave (crash recovery) ---

    def has_autosave(self) -> bool:
        return os.path.isfile(self.autosave_path)

    def save_autosave(self) -> None:
        """Write current doc to autosave.json without touching project.json."""
        if self.doc is None:
            return
        data = document_to_dict(self.doc, self.max_backups)
        with open(self.autosave_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info("Autosave written: %s", self.autosave_path)

    def load_autosave(self) -> PortoDocument:
        """Load autosave.json as a PortoDocument (does not replace self.doc)."""
        with open(self.autosave_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        doc, _ = dict_to_document(data)
        return doc

    def get_autosave_metadata(self) -> dict:
        """Return metadata about the autosave file (timestamp, etc.)."""
        if not self.has_autosave():
            return {}
        stat = os.stat(self.autosave_path)
        mtime = datetime.fromtimestamp(stat.st_mtime)
        return {
            "mtime": mtime,
            "mtime_str": mtime.strftime("%Y-%m-%d %H:%M:%S"),
            "size_bytes": stat.st_size
        }

    def delete_autosave(self) -> None:
        if os.path.exists(self.autosave_path):
            os.remove(self.autosave_path)
            logger.info("Autosave deleted: %s", self.autosave_path)

    # --- backup management ---

    def list_backups(self) -> list[str]:
        """Returns backup filenames sorted newest-first."""
        if not os.path.isdir(self.backups_dir):
            return []
        files = [f for f in os.listdir(self.backups_dir) if f.endswith(".json")]
        return sorted(files, reverse=True)

    def load_backup(self, backup_filename: str) -> PortoDocument:
        """Load a backup as a read-only PortoDocument (does not replace self.doc)."""
        path = os.path.join(self.backups_dir, backup_filename)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        doc, _ = document_from_dict(data)
        return doc

    def delete_backup(self, backup_filename: str) -> None:
        path = os.path.join(self.backups_dir, backup_filename)
        if os.path.exists(path):
            os.remove(path)
            logger.debug("Backup deleted: %s", backup_filename)

    def _prune_backups(self) -> None:
        backups = self.list_backups()
        while len(backups) > self.max_backups:
            oldest = backups.pop()
            self.delete_backup(oldest)
            logger.debug("Pruned old backup: %s", oldest)

    def set_cover(self, source_path: str) -> str:
        """
        Copy an image file into the project folder and set it as the cover.
        Returns the new relative path within the project.
        """
        if not os.path.exists(source_path):
            raise FileNotFoundError(f"Cover image not found: {source_path}")

        ext = os.path.splitext(source_path)[1].lower()
        if ext not in (".jpg", ".jpeg", ".png"):
            raise ValueError("Unsupported image format. Use JPG or PNG.")

        # Ensure filename is safe and unique-ish
        dest_filename = f"cover{ext}"
        dest_path = os.path.join(self.project_dir, dest_filename)

        # Copy file
        shutil.copy2(source_path, dest_path)
        logger.info("Cover image copied to project: %s", dest_filename)

        # Update metadata
        self.doc.set_metadata("cover_image", dest_filename)
        self.save()

        return dest_filename

    # --- version snapshots ---

    def save_snapshot(self, name: str, description: str = "") -> dict:
        name = name.strip()
        if not name:
            raise ValueError("Snapshot name cannot be empty")
        safe_filename = re.sub(r'[^\w\-]', '_', name) + ".json"
        os.makedirs(self.versions_dir, exist_ok=True)
        snapshot_path = os.path.join(self.versions_dir, safe_filename)
        data = document_to_dict(self.doc, self.max_backups)
        with open(snapshot_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        word_count = sum(len(b.text.split()) for ch in self.doc.chapters for b in ch.blocks)
        entry_date = datetime.now().isoformat()
        index_path = os.path.join(self.versions_dir, "versions_index.json")
        index = []
        if os.path.exists(index_path):
            with open(index_path, "r", encoding="utf-8") as f:
                index = json.load(f)
        index = [e for e in index if e["filename"] != safe_filename]
        new_entry = {"name": name, "description": description, "date": entry_date,
                     "word_count": word_count, "filename": safe_filename}
        index.append(new_entry)
        index.sort(key=lambda x: x["date"], reverse=True)
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2, ensure_ascii=False)
        logger.info("Snapshot saved: %s", safe_filename)
        return new_entry

    def list_snapshots(self) -> list[dict]:
        index_path = os.path.join(self.versions_dir, "versions_index.json")
        if not os.path.exists(index_path):
            return []
        with open(index_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def restore_snapshot(self, filename: str) -> PortoDocument:
        snapshot_path = os.path.join(self.versions_dir, filename)
        if not os.path.exists(snapshot_path):
            raise FileNotFoundError(f"Snapshot not found: {filename}")
        with open(snapshot_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        doc, _ = document_from_dict(data)
        logger.info("Snapshot restored: %s", filename)
        return doc

    def delete_snapshot(self, filename: str) -> None:
        snapshot_path = os.path.join(self.versions_dir, filename)
        if os.path.exists(snapshot_path):
            os.remove(snapshot_path)
        index_path = os.path.join(self.versions_dir, "versions_index.json")
        if os.path.exists(index_path):
            with open(index_path, "r", encoding="utf-8") as f:
                index = json.load(f)
            index = [e for e in index if e["filename"] != filename]
            with open(index_path, "w", encoding="utf-8") as f:
                json.dump(index, f, indent=2, ensure_ascii=False)
        logger.info("Snapshot deleted: %s", filename)


# ---------------------------------------------------------------------------
# ProjectManager
# ---------------------------------------------------------------------------

class ProjectManager:
    """Scans the projects directory and manages all known projects."""

    def __init__(self, projects_dir: str = PROJECTS_DIR) -> None:
        self.projects_dir = projects_dir
        os.makedirs(projects_dir, exist_ok=True)

    def list_projects(self) -> list[str]:
        """Returns names of all project folders (sorted alphabetically)."""
        try:
            entries = os.listdir(self.projects_dir)
        except OSError as exc:
            logger.error("Cannot list projects: %s", exc)
            return []
        return sorted(
            e for e in entries
            if os.path.isfile(os.path.join(self.projects_dir, e, _PROJECT_FILE))
        )

    def create_project(self, title: str, author: str = "", language: str = "en",
                       max_backups: int = DEFAULT_MAX_BACKUPS) -> NovelProject:
        return NovelProject.create(self.projects_dir, title, author, language, max_backups)

    def open_project(self, name: str) -> NovelProject:
        project_dir = os.path.join(self.projects_dir, name)
        return NovelProject.load(project_dir)

    def open_project_by_path(self, path: str) -> NovelProject:
        return NovelProject.load(path)

    def delete_project(self, name: str) -> None:
        project_dir = os.path.join(self.projects_dir, name)
        if os.path.isdir(project_dir):
            shutil.rmtree(project_dir)
            logger.info("Project deleted: %s", name)
        else:
            logger.warning("delete_project: not found: %s", name)

    def project_exists(self, name: str) -> bool:
        return os.path.isfile(
            os.path.join(self.projects_dir, name, _PROJECT_FILE)
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_folder_name(title: str) -> str:
    """Convert a novel title to a safe folder name."""
    safe = "".join(c if c.isalnum() or c in " _-" else "_" for c in title)
    safe = safe.strip().replace(" ", "_")
    return safe or "Untitled"
