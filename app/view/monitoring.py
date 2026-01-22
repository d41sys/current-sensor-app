# coding: utf-8
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QGridLayout, QGroupBox
from qfluentwidgets import ScrollArea, PushButton, ComboBox, PrimaryPushButton, InfoBar, InfoBarPosition, CheckBox, LineEdit
import pyqtgraph as pg
import sys
import os
import platform
import socket
import serial
from datetime import datetime


class SerialReaderThread(QThread):
    """Thread for reading serial data"""
    data_received = Signal(dict)
    connection_status = Signal(str)
    
    def __init__(self, port="/dev/serial0", baudrate=115200):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.serial_connection = None
        self.running = False
    
    def run(self):
        """Read data from serial port"""
        try:
            self.serial_connection = serial.Serial(self.port, self.baudrate, timeout=1)
            self.running = True
            self.connection_status.emit(f"Connected to {self.port} at {self.baudrate} baud")
            
            while self.running:
                try:
                    line = self.serial_connection.readline().decode(errors="ignore").strip()
                    if line:
                        # Parse the data - expecting format like "V:12.5,A:0.45" or similar
                        data = self.parse_data(line)
                        if data:
                            self.data_received.emit(data)
                except Exception as e:
                    if self.running:  # Only emit error if we're still supposed to be running
                        self.connection_status.emit(f"Error reading data: {str(e)}")
                        
        except Exception as e:
            self.connection_status.emit(f"Error: Could not open {self.port} - {str(e)}")
        finally:
            if self.serial_connection and self.serial_connection.is_open:
                self.serial_connection.close()
    
    def parse_data(self, line):
        """Parse incoming serial data from Pico
        Expected format: seq,timestamp,v1,v2,...,v9,i1,i2,...,i9,power
        Total: 2 + 9 + 9 + 1 = 21 values
        """
        try:
            parts = line.strip().split(',')
            
            # Expected 21 values: seq, timestamp, 9 voltages, 9 currents, power
            if len(parts) >= 21:
                seq = int(parts[0])
                pico_timestamp = int(parts[1])
                
                # Parse 9 voltages (indices 2-10)
                voltages = [float(parts[i]) for i in range(2, 11)]
                
                # Parse 9 currents (indices 11-19)
                currents = [float(parts[i]) for i in range(11, 20)]
                
                # Power is at index 20
                power = float(parts[20])
                
                return {
                    'timestamp': datetime.now().strftime("%H:%M:%S.%f")[:-3],
                    'seq': seq,
                    'pico_time': pico_timestamp,
                    'voltages': voltages,
                    'currents': currents,
                    'power': power,
                    'raw': line
                }
        except Exception as e:
            # Log parsing error
            print(f"Parse error: {e} for line: {line}")
        
        # If parsing fails, just return raw data
        return {
            'timestamp': datetime.now().strftime("%H:%M:%S.%f")[:-3],
            'voltages': [0.0] * 9,
            'currents': [0.0] * 9,
            'power': 0.0,
            'raw': line
        }
    
    def stop(self):
        """Stop the reader thread"""
        self.running = False


class SocketReaderThread(QThread):
    """Thread for reading data via socket (Windows)"""
    data_received = Signal(dict)
    connection_status = Signal(str)
    
    def __init__(self, host="192.168.50.2", port=5000):
        super().__init__()
        self.host = host
        self.port = port
        self.socket_connection = None
        self.running = False
    
    def run(self):
        """Read data from socket"""
        try:
            self.socket_connection = socket.create_connection((self.host, self.port), timeout=10)
            self.running = True
            self.connection_status.emit(f"Connected to {self.host}:{self.port}")
            
            buf = b""
            while self.running:
                try:
                    chunk = self.socket_connection.recv(4096)
                    if not chunk:
                        if self.running:
                            self.connection_status.emit("Disconnected by server")
                        break
                    buf += chunk
                    
                    # Process complete lines
                    while b"\n" in buf:
                        line, buf = buf.split(b"\n", 1)
                        line_str = line.decode("utf-8", errors="replace").strip()
                        if line_str:
                            data = self.parse_data(line_str)
                            if data:
                                self.data_received.emit(data)
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        self.connection_status.emit(f"Error reading data: {str(e)}")
                        
        except Exception as e:
            self.connection_status.emit(f"Error: Could not connect to {self.host}:{self.port} - {str(e)}")
        finally:
            if self.socket_connection:
                try:
                    self.socket_connection.close()
                except:
                    pass
    
    def parse_data(self, line):
        """Parse incoming data from socket
        Expected format: seq,timestamp,v1,v2,...,v9,i1,i2,...,i9,power
        Total: 2 + 9 + 9 + 1 = 21 values
        """
        try:
            parts = line.strip().split(',')
            
            # Expected 21 values: seq, timestamp, 9 voltages, 9 currents, power
            if len(parts) >= 21:
                seq = int(parts[0])
                pico_timestamp = int(parts[1])
                
                # Parse 9 voltages (indices 2-10)
                voltages = [float(parts[i]) for i in range(2, 11)]
                
                # Parse 9 currents (indices 11-19)
                currents = [float(parts[i]) for i in range(11, 20)]
                
                # Power is at index 20
                power = float(parts[20])
                
                return {
                    'timestamp': datetime.now().strftime("%H:%M:%S.%f")[:-3],
                    'seq': seq,
                    'pico_time': pico_timestamp,
                    'voltages': voltages,
                    'currents': currents,
                    'power': power,
                    'raw': line
                }
        except Exception as e:
            print(f"Parse error: {e} for line: {line}")
        
        return {
            'timestamp': datetime.now().strftime("%H:%M:%S.%f")[:-3],
            'voltages': [0.0] * 9,
            'currents': [0.0] * 9,
            'power': 0.0,
            'raw': line
        }
    
    def stop(self):
        """Stop the reader thread"""
        self.running = False
        if self.socket_connection:
            try:
                self.socket_connection.close()
            except:
                pass


class USBDataInterface(ScrollArea):
    """USB Data Processor Interface - Real USB Connection"""
    
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName('usbDataInterface')
        
        self.data_reader = None  # Can be SerialReaderThread or SocketReaderThread
        self.is_windows = platform.system() == 'Windows'
        
        # Initialize data structures for 9 sensors
        self.num_sensors = 9
        self.voltage_data = [[] for _ in range(self.num_sensors)]
        self.current_data = [[] for _ in range(self.num_sensors)]
        self.max_points = 400
        
        # Colors for each sensor line
        self.colors = [
            (255, 99, 132),   # Red
            (54, 162, 235),   # Blue
            (255, 206, 86),   # Yellow
            (75, 192, 192),   # Teal
            (153, 102, 255),  # Purple
            (255, 159, 64),   # Orange
            (46, 204, 113),   # Green
            (142, 68, 173),   # Violet
            (52, 73, 94),     # Dark Blue
        ]
        
        self.view = QWidget(self)
        self.vBoxLayout = QVBoxLayout(self.view)
        
        self.__initWidget()
    
    def __initWidget(self):
        """Initialize widgets"""
        self.view.setObjectName('view')
        
        # Connection settings group
        connection_group = QGroupBox("Connection Settings")
        connection_layout = QVBoxLayout(connection_group)
        
        # Connection mode row
        mode_layout = QHBoxLayout()
        
        self.mode_label = QLabel("Mode:")
        self.mode_label.setStyleSheet("font-weight: bold;")
        mode_layout.addWidget(self.mode_label)
        
        self.mode_combo = ComboBox()
        self.mode_combo.addItem("🔌 Serial (/dev/serial0)" if not self.is_windows else "🔌 Serial (COM port)")
        self.mode_combo.addItem("🌐 Socket (TCP/IP)")
        self.mode_combo.setCurrentIndex(1 if self.is_windows else 0)  # Default: Socket for Windows, Serial for others
        self.mode_combo.currentIndexChanged.connect(self.on_mode_changed)
        mode_layout.addWidget(self.mode_combo)
        
        mode_layout.addStretch()
        connection_layout.addLayout(mode_layout)
        
        # Socket settings row (IP and Port)
        socket_layout = QHBoxLayout()
        
        self.ip_label = QLabel("IP Address:")
        socket_layout.addWidget(self.ip_label)
        
        self.ip_input = LineEdit()
        self.ip_input.setText("192.168.50.2")
        self.ip_input.setPlaceholderText("Enter Pi IP address")
        self.ip_input.setMinimumWidth(150)
        socket_layout.addWidget(self.ip_input)
        
        self.port_label = QLabel("Port:")
        socket_layout.addWidget(self.port_label)
        
        self.port_input = LineEdit()
        self.port_input.setText("5000")
        self.port_input.setPlaceholderText("Port")
        self.port_input.setMaximumWidth(80)
        socket_layout.addWidget(self.port_input)
        
        socket_layout.addStretch()
        connection_layout.addLayout(socket_layout)
        
        self.vBoxLayout.addWidget(connection_group)
        
        # Control bar
        control_layout = QHBoxLayout()
        
        # Connect/Disconnect buttons
        self.connect_btn = PrimaryPushButton("▶ Connect")
        self.connect_btn.clicked.connect(self.connect_data_source)
        control_layout.addWidget(self.connect_btn)
        
        self.disconnect_btn = PushButton("⏹ Disconnect")
        self.disconnect_btn.clicked.connect(self.disconnect_data_source)
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
        
        # Status display
        status_container = QWidget()
        status_layout = QHBoxLayout(status_container)
        status_layout.setContentsMargins(5, 5, 5, 5)
        
        self.status_label = QLabel("Status: Disconnected - Select connection mode and click Connect")
        self.status_label.setStyleSheet("font-weight: bold; padding: 5px;")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        
        self.vBoxLayout.addWidget(status_container)
        
        # Update UI based on initial mode
        self.on_mode_changed(self.mode_combo.currentIndex())
        
        # Sensor visibility checkboxes
        checkbox_group = QGroupBox("Sensor Visibility")
        checkbox_layout = QGridLayout(checkbox_group)
        
        self.sensor_checkboxes = []
        for i in range(self.num_sensors):
            cb = CheckBox(f"Sensor {i + 1}")
            cb.setChecked(True)
            cb.stateChanged.connect(lambda state, idx=i: self.toggle_sensor(idx, state))
            # Set checkbox text color to match line color
            color = self.colors[i]
            cb.setStyleSheet(f"color: rgb({color[0]}, {color[1]}, {color[2]}); font-weight: bold;")
            self.sensor_checkboxes.append(cb)
            checkbox_layout.addWidget(cb, i // 5, i % 5)  # 5 columns
        
        # Add Select All / Deselect All buttons
        self.select_all_btn = PushButton("Select All")
        self.select_all_btn.clicked.connect(self.select_all_sensors)
        checkbox_layout.addWidget(self.select_all_btn, 2, 0)
        
        self.deselect_all_btn = PushButton("Deselect All")
        self.deselect_all_btn.clicked.connect(self.deselect_all_sensors)
        checkbox_layout.addWidget(self.deselect_all_btn, 2, 1)
        
        self.vBoxLayout.addWidget(checkbox_group)
        
        # Chart widget
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('w')
        self.plot_widget.setTitle("Real-time Current Monitor (9 Sensors)", color="k", size="14pt")
        self.plot_widget.setLabel('left', 'Current (A)', color='k')
        self.plot_widget.setLabel('bottom', 'Time', units='s', color='k')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.addLegend()
        
        # Create 9 chart curves
        self.current_curves = []
        for i in range(self.num_sensors):
            curve = self.plot_widget.plot(
                pen=pg.mkPen(color=self.colors[i], width=2),
                name=f"Sensor {i + 1}"
            )
            self.current_curves.append(curve)
        
        self.vBoxLayout.addWidget(self.plot_widget)
        
        # Data display
        self.data_display = QTextEdit()
        self.data_display.setReadOnly(True)
        self.data_display.setMaximumHeight(150)
        self.data_display.setPlaceholderText("Data log will appear here once connected...")
        self.vBoxLayout.addWidget(self.data_display)
        
        self.setWidget(self.view)
        self.setWidgetResizable(True)
    
    def on_mode_changed(self, index):
        """Handle connection mode change"""
        is_socket_mode = index == 1
        
        # Show/hide socket settings based on mode
        self.ip_label.setVisible(is_socket_mode)
        self.ip_input.setVisible(is_socket_mode)
        self.port_label.setVisible(is_socket_mode)
        self.port_input.setVisible(is_socket_mode)
        
        if is_socket_mode:
            self.status_label.setText("Status: Disconnected - Enter IP and Port, then click Connect")
        else:
            self.status_label.setText("Status: Disconnected - Click Connect to start reading from serial port")
    
    def connect_data_source(self):
        """Connect to data source (Serial or Socket based on mode)"""
        if self.data_reader is not None:
            return
        
        is_socket_mode = self.mode_combo.currentIndex() == 1
        
        if is_socket_mode:
            # Socket mode (Windows or manual selection)
            host = self.ip_input.text().strip()
            try:
                port = int(self.port_input.text().strip())
            except ValueError:
                InfoBar.error(
                    title="Invalid Port",
                    content="Please enter a valid port number",
                    parent=self,
                    position=InfoBarPosition.TOP,
                    duration=3000
                )
                return
            
            if not host:
                InfoBar.error(
                    title="Invalid IP",
                    content="Please enter a valid IP address",
                    parent=self,
                    position=InfoBarPosition.TOP,
                    duration=3000
                )
                return
            
            self.data_reader = SocketReaderThread(host=host, port=port)
            
            InfoBar.info(
                title="Connecting...",
                content=f"Connecting to {host}:{port}",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=2000
            )
        else:
            # Serial mode (Linux/macOS)
            serial_port = "/dev/serial0"
            self.data_reader = SerialReaderThread(port=serial_port, baudrate=115200)
            
            InfoBar.info(
                title="Connecting...",
                content=f"Opening {serial_port} at 115200 baud",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=2000
            )
        
        # Connect signals
        self.data_reader.data_received.connect(self.on_data_received)
        self.data_reader.connection_status.connect(self.on_connection_status)
        self.data_reader.start()
        
        # Update UI
        self.connect_btn.setEnabled(False)
        self.disconnect_btn.setEnabled(True)
        self.mode_combo.setEnabled(False)
        self.ip_input.setEnabled(False)
        self.port_input.setEnabled(False)
    
    def disconnect_data_source(self):
        """Disconnect from data source"""
        if self.data_reader:
            self.data_reader.stop()
            self.data_reader.wait()
            self.data_reader = None
            self.status_label.setText("Status: Disconnected")
            self.status_label.setStyleSheet("font-weight: bold; padding: 5px;")
            
            # Update UI
            self.connect_btn.setEnabled(True)
            self.disconnect_btn.setEnabled(False)
            self.mode_combo.setEnabled(True)
            self.ip_input.setEnabled(True)
            self.port_input.setEnabled(True)
            
            InfoBar.success(
                title="Disconnected",
                content="Connection closed",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=2000
            )
    
    def on_data_received(self, data):
        """Handle received data from serial port"""
        # Build log message
        if 'voltages' in data and 'currents' in data:
            seq = data.get('seq', 0)
            power = data.get('power', 0)
            # Show summary of all sensors
            avg_v = sum(data['voltages']) / len(data['voltages'])
            avg_i = sum(data['currents']) / len(data['currents'])
            message = f"[{data['timestamp']}] #{seq} Avg V:{avg_v:.3f}V Avg I:{avg_i:.4f}A P:{power:.3f}W"
        else:
            message = f"[{data['timestamp']}] Raw: {data['raw']}"
        self.data_display.append(message)
        
        # Update chart data for all 9 sensors
        if 'currents' in data:
            for i in range(self.num_sensors):
                self.current_data[i].append(data['currents'][i])
                
                # Keep only recent data points
                if len(self.current_data[i]) > self.max_points:
                    self.current_data[i].pop(0)
        
        # Update voltage data
        if 'voltages' in data:
            for i in range(self.num_sensors):
                self.voltage_data[i].append(data['voltages'][i])
                
                # Keep only recent data points
                if len(self.voltage_data[i]) > self.max_points:
                    self.voltage_data[i].pop(0)
        
        # Update all curves
        for i in range(self.num_sensors):
            if len(self.current_data[i]) > 0:
                x = [j / 100 for j in range(len(self.current_data[i]))]
                self.current_curves[i].setData(x, self.current_data[i])
    
    def on_connection_status(self, status):
        """Handle connection status updates"""
        if "Connected" in status:
            self.status_label.setText(f"Status: ✓ {status}")
            self.status_label.setStyleSheet("font-weight: bold; padding: 5px; color: green;")
            
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
    
    def toggle_sensor(self, sensor_idx, state):
        """Toggle visibility of a sensor curve"""
        visible = state == Qt.Checked.value if hasattr(Qt.Checked, 'value') else state == 2
        self.current_curves[sensor_idx].setVisible(visible)
    
    def select_all_sensors(self):
        """Select all sensor checkboxes"""
        for cb in self.sensor_checkboxes:
            cb.setChecked(True)
    
    def deselect_all_sensors(self):
        """Deselect all sensor checkboxes"""
        for cb in self.sensor_checkboxes:
            cb.setChecked(False)
    
    def clear_data(self):
        """Clear all data"""
        self.data_display.clear()
        
        # Clear all sensor data
        for i in range(self.num_sensors):
            self.current_data[i].clear()
            self.voltage_data[i].clear()
            self.current_curves[i].setData([], [])
        
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