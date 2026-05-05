import sys
import os
import argparse
import logging
import traceback
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QIcon
from porto_write.constants import APP_NAME, APP_VERSION
from porto_write.logger import setup_logging
from porto_write.settings import AppSettings
from porto_write.ui.main_window import MainWindow
from porto_write.ui.dialogs import ProjectPickerDialog, BetaWarningDialog

logger = logging.getLogger("porto_write.main")

def exception_hook(exctype, value, tb):
    """Global hook to catch and log unhandled exceptions."""
    err_msg = "".join(traceback.format_exception(exctype, value, tb))
    logger.critical(f"Unhandled Exception:\n{err_msg}")
    
    # Also show a message box if possible
    if QApplication.instance():
        QMessageBox.critical(None, "Critical Error", f"An unexpected error occurred:\n\n{value}\n\nCheck logs for details.")
    
    sys.__excepthook__(exctype, value, tb)

sys.excepthook = exception_hook

def main():
    logger.debug("Parsing arguments...")
    parser = argparse.ArgumentParser(description=f"{APP_NAME} v{APP_VERSION}")
    parser.add_argument("--self-test", action="store_true", help="Run self-test suite and exit")
    args = parser.parse_args()

    # 1. Load settings
    logger.debug("Loading settings...")
    settings = AppSettings().load()

    # 2. Setup logging
    log_level = settings.log_level
    if args.self_test:
        log_level = "detailed"
    
    setup_logging(log_level)
    
    logger.info(f"--- {APP_NAME} v{APP_VERSION} Session Started ---")
    logger.info(f"Log Level: {log_level}")

    if args.self_test:
        logger.info("Running self-test mode...")
        from porto_write.self_test import run_all
        results = run_all()
        passed = sum(1 for _, ok, _ in results if ok)
        print(f"Self-test complete: {passed}/{len(results)} passed")
        sys.exit(0 if passed == len(results) else 1)

    # 3. Launch UI
    logger.debug("Creating QApplication instance...")
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    _ico = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'portowrite.ico')
    if os.path.isfile(_ico):
        app.setWindowIcon(QIcon(_ico))

    # 4. Show Beta Warning if enabled
    if settings.show_beta_warning:
        from PySide6.QtWidgets import QDialog
        logger.debug("Showing BetaWarningDialog...")
        dlg = BetaWarningDialog()
        if dlg.exec() != QDialog.Accepted:
            logger.info("Beta warning rejected, exiting.")
            sys.exit(0)

    try:
        # Show project picker first
        logger.debug("Initializing ProjectPickerDialog...")
        picker = ProjectPickerDialog(settings)
        logger.debug("Executing ProjectPickerDialog...")
        if picker.exec() != ProjectPickerDialog.Accepted:
            logger.info("Project picker cancelled or closed, exiting.")
            return

        project = picker.selected_project
        if not project:
            logger.error("Picker accepted but no project selected?")
            return

        logger.debug(f"Initializing MainWindow for project: {project.name}...")
        window = MainWindow(settings, project)
        logger.debug("Showing MainWindow...")
        window.show()
        
        logger.debug("Entering main event loop...")
        exit_code = app.exec()
        logger.info(f"--- {APP_NAME} Session Ended (exit code: {exit_code}) ---")
        sys.exit(exit_code)
    except Exception as exc:
        logger.critical(f"Critical application failure during UI startup: {exc}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
