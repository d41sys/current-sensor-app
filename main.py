# This Python file uses the following encoding: utf-8
import sys

from PySide6.QtWidgets import QApplication, QMainWindow

# Important:
# You need to run the following command to generate the ui_form.py file
#     pyside6-uic form.ui -o ui_form.py, or
#     pyside2-uic form.ui -o ui_form.py
from test import USBDataReader
from ui_form import Ui_Main

from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QPushButton, QTextEdit)
from PySide6.QtCore import Qt
import pyqtgraph as pg

class USBDataProcessorApp(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("USB Data Processor")
        self.setGeometry(100, 100, 1000, 600)
        
        self.usb_reader = None
        self.template = None
        
        # Initialize data structures
        self.voltage_data = []
        self.current_data = []
        self.max_points = 400
        
        # Setup UI from designer if available
        if self.template is not None:
            self.ui = Ui_Main()
            self.ui.setupUi(self)
        else:
            # Fallback to programmatic UI if ui_form.py not available
            self.setup_ui_programmatic()

    def setup_ui_programmatic(self):
        """Fallback UI setup if ui_form.py is not available"""
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
        toolbar.addAction("Export", self.export_chart)

        # Create central widget with layout
        central = QWidget()
        layout = QVBoxLayout()

        # Status display
        self.status_label = QLabel("Status: Disconnected")
        layout.addWidget(self.status_label)

        # Chart widget
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('w')
        self.plot_widget.setTitle("Real-time Voltage & Current Monitor", color="k", size="14pt")
        self.plot_widget.setLabel('left', 'Value', color='k')
        self.plot_widget.setLabel('bottom', 'Time', units='s', color='k')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.addLegend()
        
        # Chart curves (without symbols to avoid segfault)
        # self.voltage_curve = self.plot_widget.plot(
        #     pen=pg.mkPen(color=(75, 192, 192), width=2),
        #     name="Voltage (V)"
        # )
        
        self.current_curve = self.plot_widget.plot(
            pen=pg.mkPen(color=(255, 99, 132), width=2),
            name="Current (A)"
        )
        
        layout.addWidget(self.plot_widget)

        # Data display
        self.data_display = QTextEdit()
        self.data_display.setReadOnly(True)
        self.data_display.setMaximumHeight(150)
        layout.addWidget(self.data_display)

        central.setLayout(layout)
        self.setCentralWidget(central)

        # Create status bar
        self.statusBar().showMessage("Ready")

    def connect_usb(self):
        """Connect to Pico device"""
        if self.usb_reader is None:
            # Auto-detect port and OS
            port = USBDataReader.find_pico_port()
            os_name = USBDataReader.get_os()
            print(f"Detected OS: {os_name}, Port: {port}")
            
            self.usb_reader = USBDataReader(port=port, baudrate=115200)
            self.usb_reader.data_received.connect(self.on_data_received)
            self.usb_reader.connection_status.connect(self.on_connection_status)
            self.statusBar().showMessage(f"Detected: {os_name} | Port: {port}")
            self.usb_reader.start()

    def disconnect_usb(self):
        """Disconnect from Pico device"""
        if self.usb_reader:
            self.usb_reader.stop()
            self.usb_reader.wait()
            self.usb_reader = None
            self.statusBar().showMessage("Disconnected")
            self.status_label.setText("Status: Disconnected")

    def on_data_received(self, data):
        """Handle received data from Pico"""
        message = f"[{data['timestamp']}] Voltage: {data['voltage']:.2f}V, Current: {data['current']:.2f}A\n"
        self.data_display.append(message)
        print(f"[{data['timestamp']}] V: {data['voltage']:.2f}V, I: {data['current']:.2f}A")
        
        # Update chart
        # self.voltage_data.append(data['voltage'])
        self.current_data.append(data['current'])
        
        # Keep only recent data points
        if len(self.current_data) > self.max_points:
            # self.voltage_data.pop(0)
            self.current_data.pop(0)
        
        # Update plot with time in seconds (100 packets/second)
        x = [i / 100 for i in range(len(self.current_data))]
        # self.voltage_curve.setData(x, self.voltage_data)
        self.current_curve.setData(x, self.current_data)

    def on_connection_status(self, status):
        """Handle connection status updates"""
        self.statusBar().showMessage(status)
        if "Connected" in status:
            self.status_label.setText("Status: Connected")
        elif "Error" in status or "Connection" in status:
            self.status_label.setText("Status: Error")

    def start_processing(self):
        self.statusBar().showMessage("Processing...")

    def stop_processing(self):
        self.statusBar().showMessage("Stopped")

    def clear_data(self):
        self.data_display.clear()
        self.voltage_data.clear()
        self.current_data.clear()
        self.voltage_curve.setData([], [])
        self.current_curve.setData([], [])

    def export_chart(self):
        """Export chart as PNG image"""
        try:
            exporter = pg.exporters.ImageExporter(self.plot_widget.plotItem)
            exporter.export('chart.png')
            self.statusBar().showMessage("Chart exported to chart.png")
            print("Chart exported to chart.png")
        except Exception as e:
            self.statusBar().showMessage(f"Export failed: {e}")

    def open_settings(self):
        # This would open a QDialog
        pass

    def closeEvent(self, event):
        """Clean up when closing the app"""
        self.disconnect_usb()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = USBDataProcessorApp()
    window.show()
    sys.exit(app.exec())