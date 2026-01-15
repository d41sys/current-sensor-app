# coding: utf-8
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit
from qfluentwidgets import ScrollArea, PushButton, ComboBox, PrimaryPushButton, InfoBar, InfoBarPosition
import pyqtgraph as pg
import sys
import os

from ..common.usb_reader import USBDataReader


class USBDataInterface(ScrollArea):
    """USB Data Processor Interface - Real USB Connection"""
    
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName('usbDataInterface')
        
        self.usb_reader = None
        
        # Initialize data structures
        self.voltage_data = []
        self.current_data = []
        self.max_points = 400
        
        self.view = QWidget(self)
        self.vBoxLayout = QVBoxLayout(self.view)
        
        self.__initWidget()
    
    def __initWidget(self):
        """Initialize widgets"""
        self.view.setObjectName('view')
        
        # Control bar
        control_layout = QHBoxLayout()
        
        # Port selection
        self.port_label = QLabel("Port:")
        control_layout.addWidget(self.port_label)
        
        self.port_combo = ComboBox()
        self.port_combo.setMinimumWidth(200)
        control_layout.addWidget(self.port_combo)
        
        # Refresh ports button
        self.refresh_btn = PushButton("🔄 Refresh")
        self.refresh_btn.clicked.connect(self.refresh_ports)
        control_layout.addWidget(self.refresh_btn)
        
        # Connect/Disconnect buttons
        self.connect_btn = PrimaryPushButton("▶ Connect")
        self.connect_btn.clicked.connect(self.connect_usb)
        control_layout.addWidget(self.connect_btn)
        
        self.disconnect_btn = PushButton("⏹ Disconnect")
        self.disconnect_btn.clicked.connect(self.disconnect_usb)
        self.disconnect_btn.setEnabled(False)
        control_layout.addWidget(self.disconnect_btn)
        
        # Clear button
        self.clear_btn = PushButton("🗑️ Clear")
        self.clear_btn.clicked.connect(self.clear_data)
        control_layout.addWidget(self.clear_btn)
        
        # Export button
        self.export_btn = PushButton("💾 Export")
        self.export_btn.clicked.connect(self.export_chart)
        control_layout.addWidget(self.export_btn)
        
        control_layout.addStretch()
        self.vBoxLayout.addLayout(control_layout)
        
        # Status display with port info
        status_container = QWidget()
        status_layout = QHBoxLayout(status_container)
        status_layout.setContentsMargins(5, 5, 5, 5)
        
        self.status_label = QLabel("Status: Disconnected - Select a USB port to connect")
        self.status_label.setStyleSheet("font-weight: bold; padding: 5px;")
        status_layout.addWidget(self.status_label)
        
        self.connection_info = QLabel("")
        self.connection_info.setStyleSheet("padding: 5px; color: gray;")
        status_layout.addWidget(self.connection_info)
        status_layout.addStretch()
        
        self.vBoxLayout.addWidget(status_container)
        
        # Chart widget
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('w')
        self.plot_widget.setTitle("Real-time Current Monitor", color="k", size="14pt")
        self.plot_widget.setLabel('left', 'Current (A)', color='k')
        self.plot_widget.setLabel('bottom', 'Time', units='s', color='k')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.addLegend()
        
        # Chart curve
        self.current_curve = self.plot_widget.plot(
            pen=pg.mkPen(color=(255, 99, 132), width=2),
            name="Current (A)"
        )
        
        self.vBoxLayout.addWidget(self.plot_widget)
        
        # Data display
        self.data_display = QTextEdit()
        self.data_display.setReadOnly(True)
        self.data_display.setMaximumHeight(150)
        self.data_display.setPlaceholderText("Data log will appear here once connected...")
        self.vBoxLayout.addWidget(self.data_display)
        
        self.setWidget(self.view)
        self.setWidgetResizable(True)
        
        # Refresh ports after all widgets are created
        self.refresh_ports()
    
    def refresh_ports(self):
        """Refresh available USB ports"""
        self.port_combo.clear()
        
        os_type = USBDataReader.get_os()
        real_ports_found = False
        
        try:
            if os_type == 'Windows':
                # Windows COM ports
                import serial.tools.list_ports
                ports = serial.tools.list_ports.comports()
                for port in ports:
                    self.port_combo.addItem(f"🔌 {port.device} - {port.description}")
                    real_ports_found = True
                    
            elif os_type == 'Darwin':
                # macOS ports
                import glob
                ports = (glob.glob('/dev/tty.usbmodem*') + 
                        glob.glob('/dev/tty.SLAB_USBtoUART*') + 
                        glob.glob('/dev/tty.usbserial*') +
                        glob.glob('/dev/cu.usbmodem*'))  # Add cu. ports
                
                for port in sorted(set(ports)):  # Remove duplicates
                    self.port_combo.addItem(f"🔌 {port}")
                    real_ports_found = True
                    
                # Add virtual port for testing if exists
                if os.path.exists('/tmp/pico_virtual'):
                    self.port_combo.addItem('🔧 /tmp/pico_virtual (Test Virtual Port)')
                    real_ports_found = True
                    
            else:
                # Linux ports
                import glob
                ports = glob.glob('/dev/ttyACM*') + glob.glob('/dev/ttyUSB*')
                for port in ports:
                    self.port_combo.addItem(f"🔌 {port}")
                    real_ports_found = True
        except Exception as e:
            print(f"Error scanning ports: {e}")
        
        # Add mock mode option at the end
        self.port_combo.addItem("🎮 Mock Mode (Simulated Data)")
        
        # Update connection info (check if widget exists first)
        if hasattr(self, 'connection_info'):
            real_count = self.port_combo.count() - 1  # Exclude mock mode
            if real_count > 0:
                self.connection_info.setText(f"Found {real_count} device(s)")
                self.connection_info.setStyleSheet("padding: 5px; color: green;")
            else:
                self.connection_info.setText("No USB devices found")
                self.connection_info.setStyleSheet("padding: 5px; color: orange;")
                
            # Show info bar only if no real ports found and widget is fully initialized
            if not real_ports_found and self.isVisible():
                InfoBar.warning(
                    title="No Real Ports Found",
                    content="No USB devices detected. Use Mock Mode or connect a device and click Refresh.",
                    parent=self,
                    position=InfoBarPosition.TOP,
                    duration=4000
                )
    
    def get_selected_port(self):
        """Get the selected port from combo box"""
        text = self.port_combo.currentText()
        
        # Check for mock mode
        if "Mock Mode" in text or "🎮" in text:
            return None  # Will use mock mode
        
        # Remove emoji and extra text
        text = text.replace("🔌 ", "").replace("🔧 ", "")
        
        # Windows format: "COM3 - USB Serial Port"
        if " - " in text:
            return text.split(" - ")[0].strip()
        
        # Test virtual port format
        if "(Test Virtual Port)" in text:
            return text.replace(" (Test Virtual Port)", "").strip()
        
        # macOS/Linux format: just the path
        return text.strip()
    
    def connect_usb(self):
        """Connect to Pico device"""
        if self.usb_reader is None:
            selected_port = self.get_selected_port()
            port_text = self.port_combo.currentText()
            
            # Determine if mock mode
            mock_mode = selected_port is None or "Mock Mode" in port_text or "🎮" in port_text
            
            if mock_mode:
                # Mock mode - simulated data
                port = USBDataReader.find_pico_port()
                self.usb_reader = USBDataReader(port=port, baudrate=115200, mock_mode=True)
                
                InfoBar.info(
                    title="Mock Mode Active",
                    content="Using simulated data for testing",
                    parent=self,
                    position=InfoBarPosition.TOP,
                    duration=3000
                )
            else:
                # Real USB connection
                try:
                    self.usb_reader = USBDataReader(port=selected_port, baudrate=115200, mock_mode=False)
                    
                    InfoBar.info(
                        title="Connecting...",
                        content=f"Attempting to connect to {selected_port}",
                        parent=self,
                        position=InfoBarPosition.TOP,
                        duration=2000
                    )
                except Exception as e:
                    InfoBar.error(
                        title="Connection Failed",
                        content=f"Could not open port {selected_port}: {str(e)}",
                        parent=self,
                        position=InfoBarPosition.TOP,
                        duration=5000
                    )
                    return
            
            # Connect signals
            self.usb_reader.data_received.connect(self.on_data_received)
            self.usb_reader.connection_status.connect(self.on_connection_status)
            self.usb_reader.start()
            
            # Update UI
            self.connect_btn.setEnabled(False)
            self.disconnect_btn.setEnabled(True)
            self.port_combo.setEnabled(False)
            self.refresh_btn.setEnabled(False)
    
    def disconnect_usb(self):
        """Disconnect from Pico device"""
        if self.usb_reader:
            self.usb_reader.stop()
            self.usb_reader.wait()
            self.usb_reader = None
            self.status_label.setText("Status: Disconnected")
            self.status_label.setStyleSheet("font-weight: bold; padding: 5px;")
            
            # Update UI
            self.connect_btn.setEnabled(True)
            self.disconnect_btn.setEnabled(False)
            self.port_combo.setEnabled(True)
            self.refresh_btn.setEnabled(True)
            
            InfoBar.success(
                title="Disconnected",
                content="USB connection closed",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=2000
            )
    
    def on_data_received(self, data):
        """Handle received data from Pico"""
        message = f"[{data['timestamp']}] Voltage: {data['voltage']:.2f}V, Current: {data['current']:.2f}A"
        self.data_display.append(message)
        
        # Update chart
        self.current_data.append(data['current'])
        
        # Keep only recent data points
        if len(self.current_data) > self.max_points:
            self.current_data.pop(0)
        
        # Update plot with time in seconds (100 packets/second)
        x = [i / 100 for i in range(len(self.current_data))]
        self.current_curve.setData(x, self.current_data)
    
    def on_connection_status(self, status):
        """Handle connection status updates"""
        if "Connected" in status:
            self.status_label.setText(f"Status: ✓ {status}")
            self.status_label.setStyleSheet("font-weight: bold; padding: 5px; color: green;")
            
            # Show success notification only for real connections
            if "Mock Mode" not in status:
                InfoBar.success(
                    title="Connected!",
                    content=status,
                    parent=self,
                    position=InfoBarPosition.TOP,
                    duration=3000
                )
        elif "Error" in status:
            self.status_label.setText(f"Status: ✗ {status}")
            self.status_label.setStyleSheet("font-weight: bold; padding: 5px; color: red;")
            
            InfoBar.error(
                title="Connection Error",
                content=status,
                parent=self,
                position=InfoBarPosition.TOP,
                duration=5000
            )
        else:
            self.status_label.setText(f"Status: {status}")
            self.status_label.setStyleSheet("font-weight: bold; padding: 5px; color: orange;")
    
    def clear_data(self):
        """Clear all data"""
        self.data_display.clear()
        self.current_data.clear()
        self.voltage_data.clear()
        self.current_curve.setData([], [])
        
        InfoBar.info(
            title="Data Cleared",
            content="Chart and log data cleared",
            parent=self,
            position=InfoBarPosition.TOP,
            duration=2000
        )
    
    def export_chart(self):
        """Export chart as PNG image"""
        try:
            exporter = pg.exporters.ImageExporter(self.plot_widget.plotItem)
            filename = 'chart.png'
            exporter.export(filename)
            
            InfoBar.success(
                title="Export Complete",
                content=f"Chart saved to {filename}",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3000
            )
        except Exception as e:
            InfoBar.error(
                title="Export Failed",
                content=str(e),
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3000
            )