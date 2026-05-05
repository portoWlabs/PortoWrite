from PySide6.QtWidgets import (
    QDialog, QTabWidget, QVBoxLayout, QFormLayout, QLineEdit, QPushButton,
    QMessageBox, QWidget
)
from porto_write.licensing import activate_supporter, activate_commercial

class LicenceKeyDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Enter Licence Key')
        self.setMinimumWidth(400)

        # Main layout
        main_layout = QVBoxLayout()

        # Tab widget with two tabs: Supporter and Commercial
        tab_widget = QTabWidget()

        # Supporter tab
        supporter_tab = QWidget()
        supporter_form_layout = QFormLayout()

        self.supporter_email_field = QLineEdit()
        self.supporter_email_field.setPlaceholderText("email@example.com")
        self.supporter_key_field = QLineEdit()
        self.supporter_key_field.setPlaceholderText("XXXX-XXXX-XXXX-XXXX")
        self.activate_supporter_button = QPushButton('Activate')

        supporter_form_layout.addRow('Email:', self.supporter_email_field)
        supporter_form_layout.addRow('Key:', self.supporter_key_field)
        supporter_form_layout.addRow('', self.activate_supporter_button)

        supporter_tab.setLayout(supporter_form_layout)

        # Commercial tab
        commercial_tab = QWidget()
        commercial_form_layout = QFormLayout()

        self.commercial_name_field = QLineEdit()
        self.commercial_name_field.setPlaceholderText("Licensee Name")
        self.commercial_key_field = QLineEdit()
        self.commercial_key_field.setPlaceholderText("XXXX-XXXX-XXXX-XXXX")
        self.activate_commercial_button = QPushButton('Activate')

        commercial_form_layout.addRow('Licensee Name:', self.commercial_name_field)
        commercial_form_layout.addRow('Key:', self.commercial_key_field)
        commercial_form_layout.addRow('', self.activate_commercial_button)

        commercial_tab.setLayout(commercial_form_layout)

        # Add tabs to tab widget
        tab_widget.addTab(supporter_tab, 'Supporter')
        tab_widget.addTab(commercial_tab, 'Commercial')

        # Add tab widget to main layout
        main_layout.addWidget(tab_widget)

        # Set main layout
        self.setLayout(main_layout)

        # Connect signals and slots
        self.activate_supporter_button.clicked.connect(self._activate_supporter)
        self.activate_commercial_button.clicked.connect(self._activate_commercial)

    def _activate_supporter(self):
        email = self.supporter_email_field.text().strip()
        key = self.supporter_key_field.text().strip()

        if not email or not key:
            QMessageBox.warning(self, "Missing Information", "Please enter both email and key.")
            return

        if activate_supporter(email, key):
            QMessageBox.information(
                self,
                'Success',
                'Licence activated! Restart PortoWrite to apply.'
            )
            self.accept()
        else:
            QMessageBox.warning(
                self,
                'Invalid Key',
                'Invalid key. Please check your email and key and try again.'
            )

    def _activate_commercial(self):
        name = self.commercial_name_field.text().strip()
        key = self.commercial_key_field.text().strip()

        if not name or not key:
            QMessageBox.warning(self, "Missing Information", "Please enter both name and key.")
            return

        if activate_commercial(name, key):
            QMessageBox.information(
                self,
                'Success',
                'Licence activated! Restart PortoWrite to apply.'
            )
            self.accept()
        else:
            QMessageBox.warning(
                self,
                'Invalid Key',
                'Invalid key. Please check your name and key and try again.'
            )
