# This Python file uses the following encoding: utf-8
import sys

from PySide6.QtWidgets import QApplication, QMainWindow

# Important:
# You need to run the following command to generate the ui_form.py file
#     pyside6-uic form.ui -o ui_form.py, or
#     pyside2-uic form.ui -o ui_form.py
from ui_form import Ui_Main

from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout,
                             QLabel, QPushButton, QTextEdit)
from PySide6.QtCore import Qt

class USBDataProcessorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("USB Data Processor")
        self.setGeometry(100, 100, 1000, 600)

        # Create menu bar
        menubar = self.menuBar()
        device_menu = menubar.addMenu("Device")
        device_menu.addAction("Connect", self.connect_usb)
        device_menu.addAction("Disconnect", self.disconnect_usb)
        device_menu.addAction("Settings...", self.open_settings)
        device_menu.addSeparator()
        device_menu.addAction("Exit", self.close)

        # Create toolbar
        toolbar = self.addToolBar("Control")
        toolbar.addAction("Start", self.start_processing)
        toolbar.addAction("Stop", self.stop_processing)
        toolbar.addAction("Clear", self.clear_data)

        # Create central widget with layout
        central = QWidget()
        layout = QVBoxLayout()

        # Status display
        self.status_label = QLabel("Status: Disconnected")
        layout.addWidget(self.status_label)

        # Data display
        self.data_display = QTextEdit()
        self.data_display.setReadOnly(True)
        layout.addWidget(self.data_display)

        central.setLayout(layout)
        self.setCentralWidget(central)

        # Create status bar
        self.statusBar().showMessage("Ready")

    def connect_usb(self):
        self.statusBar().showMessage("Connected: COM3")
        self.status_label.setText("Status: Connected")

    def disconnect_usb(self):
        self.statusBar().showMessage("Disconnected")
        self.status_label.setText("Status: Disconnected")

    def start_processing(self):
        self.statusBar().showMessage("Processing...")

    def stop_processing(self):
        self.statusBar().showMessage("Stopped")

    def clear_data(self):
        self.data_display.clear()

    def open_settings(self):
        # This would open a QDialog
        pass


class Main(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_Main()
        self.ui.setupUi(self)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = USBDataProcessorApp()
    window.show()
    sys.exit(app.exec())

