import logging
import os
import tempfile

logger = logging.getLogger(__name__)

def run_ui_smoke_test() -> bool:
    """Run basic UI smoke tests."""
    try:
        from PySide6.QtWidgets import QApplication
        import sys

        app = QApplication.instance()
        if not app:
            app = QApplication(sys.argv)

        from porto_write.ui.main_window import MainWindow
        from porto_write.settings import AppSettings
        from porto_write.project import NovelProject

        settings = AppSettings()
        with tempfile.TemporaryDirectory() as tmp:
            project = NovelProject.create(tmp, "Smoke Test", "Tester")
            window = MainWindow(settings, project)

        logger.debug("UI smoke test: MainWindow initialized successfully")
        return True

    except Exception as e:
        logger.error("UI smoke test failed: %s", e)
        return False
