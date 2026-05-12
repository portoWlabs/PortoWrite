import webbrowser
from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QMessageBox

from porto_write.constants import APP_NAME, APP_VERSION
from porto_write.update_check import check_for_update


class UpdateWorker(QThread):
    finished = Signal(object)  # emits (latest, is_newer, url) tuple or None

    def run(self):
        self.finished.emit(check_for_update())


def show_update_result(parent, result, silent_if_current: bool = False):
    """Show update dialog. If silent_if_current=True, show nothing when already up to date."""
    if result is None:
        if not silent_if_current:
            QMessageBox.warning(
                parent, f"{APP_NAME} — Updates",
                "Could not reach the update server.\nCheck your connection and try again."
            )
        return
    latest, is_newer, url = result
    if is_newer:
        msg = QMessageBox(parent)
        msg.setWindowTitle(f"{APP_NAME} — Update Available")
        msg.setText(f"Version {latest} is available (you have {APP_VERSION}).")
        msg.setInformativeText("Download the latest release from GitHub?")
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg.setDefaultButton(QMessageBox.StandardButton.Yes)
        if msg.exec() == QMessageBox.StandardButton.Yes:
            webbrowser.open(url)
    elif not silent_if_current:
        QMessageBox.information(
            parent, f"{APP_NAME} — Updates",
            f"You are up to date ({APP_VERSION})."
        )
