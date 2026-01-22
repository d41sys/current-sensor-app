# coding: utf-8
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, 
                                QGridLayout, QGroupBox, QSplitter, QFrame)
from qfluentwidgets import (ScrollArea, PushButton, ComboBox, PrimaryPushButton, 
                            InfoBar, InfoBarPosition, CheckBox, LineEdit, CardWidget,
                            StrongBodyLabel, BodyLabel)
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
    """USB Data Processor Interface - Real-time Monitoring"""
    
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName('usbDataInterface')
        
        self.data_reader = None
        self.is_windows = platform.system() == 'Windows'
        
        # Data structures for 9 sensors
        self.num_sensors = 9
        self.voltage_data = [[] for _ in range(self.num_sensors)]
        self.current_data = [[] for _ in range(self.num_sensors)]
        self.max_points = 400
        
        # Colors for each sensor
        self.colors = [
            (231, 76, 60),    # Red
            (52, 152, 219),   # Blue
            (241, 196, 15),   # Yellow
            (26, 188, 156),   # Teal
            (155, 89, 182),   # Purple
            (230, 126, 34),   # Orange
            (46, 204, 113),   # Green
            (142, 68, 173),   # Violet
            (52, 73, 94),     # Dark Blue
        ]
        
        self.view = QWidget(self)
        self.vBoxLayout = QVBoxLayout(self.view)
        self.vBoxLayout.setContentsMargins(20, 20, 20, 20)
        self.vBoxLayout.setSpacing(15)
        
        self.__initWidget()
    
    def __initWidget(self):
        """Initialize widgets"""
        self.view.setObjectName('view')
        
        # ===== TOP CONTROL BAR =====
        control_card = CardWidget(self)
        control_layout = QHBoxLayout(control_card)
        control_layout.setSpacing(20)
        
        # --- Connection Section ---
        conn_section = QVBoxLayout()
        conn_section.setSpacing(8)
        
        conn_header = StrongBodyLabel("Connection")
        conn_section.addWidget(conn_header)
        
        # Mode + IP/Port in one row
        conn_row1 = QHBoxLayout()
        conn_row1.setSpacing(10)
        
        self.mode_combo = ComboBox()
        self.mode_combo.addItem("🔌 Serial" if not self.is_windows else "🔌 COM")
        self.mode_combo.addItem("🌐 Socket")
        self.mode_combo.setCurrentIndex(1 if self.is_windows else 0)
        self.mode_combo.currentIndexChanged.connect(self.on_mode_changed)
        self.mode_combo.setFixedWidth(120)
        conn_row1.addWidget(self.mode_combo)
        
        self.ip_label = BodyLabel("IP:")
        conn_row1.addWidget(self.ip_label)
        self.ip_input = LineEdit()
        self.ip_input.setText("192.168.50.2")
        self.ip_input.setFixedWidth(120)
        conn_row1.addWidget(self.ip_input)
        
        self.port_label = BodyLabel("Port:")
        conn_row1.addWidget(self.port_label)
        self.port_input = LineEdit()
        self.port_input.setText("5000")
        self.port_input.setFixedWidth(60)
        conn_row1.addWidget(self.port_input)
        
        conn_section.addLayout(conn_row1)
        
        # Buttons row
        conn_row2 = QHBoxLayout()
        conn_row2.setSpacing(8)
        
        self.connect_btn = PrimaryPushButton("▶ Connect")
        self.connect_btn.clicked.connect(self.connect_data_source)
        self.connect_btn.setFixedWidth(120)
        conn_row2.addWidget(self.connect_btn)
        
        self.disconnect_btn = PushButton("⏹ Disconnect")
        self.disconnect_btn.clicked.connect(self.disconnect_data_source)
        self.disconnect_btn.setEnabled(False)
        self.disconnect_btn.setFixedWidth(120)
        conn_row2.addWidget(self.disconnect_btn)
        
        self.status_indicator = QFrame()
        self.status_indicator.setFixedSize(12, 12)
        self.status_indicator.setStyleSheet("background-color: #95a5a6; border-radius: 6px;")
        conn_row2.addWidget(self.status_indicator)
        
        self.status_label = BodyLabel("Disconnected")
        conn_row2.addWidget(self.status_label)
        conn_row2.addStretch()
        
        conn_section.addLayout(conn_row2)
        control_layout.addLayout(conn_section)
        
        # Vertical separator
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.VLine)
        separator1.setStyleSheet("color: #ddd;")
        control_layout.addWidget(separator1)
        
        # --- Sensor Visibility Section ---
        sensor_section = QVBoxLayout()
        sensor_section.setSpacing(8)
        
        sensor_header = StrongBodyLabel("Sensors")
        sensor_section.addWidget(sensor_header)
        
        # Checkboxes in a row
        checkbox_row = QHBoxLayout()
        checkbox_row.setSpacing(15 if self.is_windows else 35)
        
        self.sensor_checkboxes = []
        for i in range(self.num_sensors):
            cb = CheckBox(f" E{i+1}")
            cb.setChecked(True)
            cb.stateChanged.connect(lambda state, idx=i: self.toggle_sensor(idx, state))
            color = self.colors[i]
            cb.setStyleSheet(f"CheckBox {{ color: rgb({color[0]}, {color[1]}, {color[2]}); font-weight: bold; }}")
            self.sensor_checkboxes.append(cb)
            checkbox_row.addWidget(cb)
        
        sensor_section.addLayout(checkbox_row)
        
        # All/None buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        
        self.select_all_btn = PushButton("All")
        self.select_all_btn.clicked.connect(self.select_all_sensors)
        self.select_all_btn.setFixedWidth(80)
        btn_row.addWidget(self.select_all_btn)
        
        self.deselect_all_btn = PushButton("None")
        self.deselect_all_btn.clicked.connect(self.deselect_all_sensors)
        self.deselect_all_btn.setFixedWidth(80)
        btn_row.addWidget(self.deselect_all_btn)
        btn_row.addStretch()
        
        sensor_section.addLayout(btn_row)
        control_layout.addLayout(sensor_section)
        
        # Vertical separator
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.VLine)
        separator2.setStyleSheet("color: #ddd;")
        control_layout.addWidget(separator2)
        
        # --- Actions Section ---
        actions_section = QVBoxLayout()
        actions_section.setSpacing(8)
        
        actions_header = StrongBodyLabel("Actions")
        actions_section.addWidget(actions_header)
        
        actions_row = QHBoxLayout()
        actions_row.setSpacing(10)
        
        self.clear_btn = PushButton("🗑️ Clear")
        self.clear_btn.clicked.connect(self.clear_data)
        self.clear_btn.setFixedWidth(120)
        actions_row.addWidget(self.clear_btn)
        
        self.export_btn = PushButton("💾 Export")
        self.export_btn.clicked.connect(self.export_chart)
        self.export_btn.setFixedWidth(120)
        actions_row.addWidget(self.export_btn)
        
        actions_section.addLayout(actions_row)
        actions_section.addStretch()
        
        control_layout.addLayout(actions_section)
        control_layout.addStretch()
        
        self.vBoxLayout.addWidget(control_card)
        
        # Update visibility based on mode
        self.on_mode_changed(self.mode_combo.currentIndex())
        
        # ===== MAIN CONTENT: Chart + Log (Horizontal Split) =====
        main_splitter = QSplitter(Qt.Horizontal)
        main_splitter.setHandleWidth(8)
        
        # --- Chart (Left side - bigger) ---
        chart_container = QWidget()
        chart_layout = QVBoxLayout(chart_container)
        chart_layout.setContentsMargins(0, 0, 0, 0)
        
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('#fafafa')
        self.plot_widget.setTitle("Real-time Current Monitor", color="#2c3e50", size="16pt")
        self.plot_widget.setLabel('left', 'Current (A)', color='#2c3e50')
        self.plot_widget.setLabel('bottom', 'Time (s)', color='#2c3e50')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.2)
        self.plot_widget.addLegend(offset=(10, 10))
        self.plot_widget.setMinimumWidth(500)
        
        # Create curves
        self.current_curves = []
        for i in range(self.num_sensors):
            curve = self.plot_widget.plot(
                pen=pg.mkPen(color=self.colors[i], width=2),
                name=f"S{i+1}"
            )
            self.current_curves.append(curve)
        
        chart_layout.addWidget(self.plot_widget)
        main_splitter.addWidget(chart_container)
        
        # --- Log Panel (Right side) ---
        log_container = CardWidget()
        log_layout = QVBoxLayout(log_container)
        log_layout.setContentsMargins(15, 15, 15, 15)
        
        log_header = StrongBodyLabel("📋 Data Log")
        log_layout.addWidget(log_header)
        
        self.data_display = QTextEdit()
        self.data_display.setReadOnly(True)
        self.data_display.setPlaceholderText("Waiting for data...")
        self.data_display.setStyleSheet("""
            QTextEdit {
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 11px;
                background-color: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        self.data_display.setMinimumWidth(280)
        log_layout.addWidget(self.data_display)
        
        main_splitter.addWidget(log_container)
        
        # Set initial sizes (70% chart, 30% log)
        main_splitter.setSizes([700, 300])
        
        self.vBoxLayout.addWidget(main_splitter, 1)  # stretch=1 to fill space
        
        self.setWidget(self.view)
        self.setWidgetResizable(True)
    
    # ===== METHODS =====
    
    def on_mode_changed(self, index):
        """Handle connection mode change"""
        is_socket = index == 1
        self.ip_label.setVisible(is_socket)
        self.ip_input.setVisible(is_socket)
        self.port_label.setVisible(is_socket)
        self.port_input.setVisible(is_socket)
    
    def connect_data_source(self):
        """Connect to data source"""
        if self.data_reader is not None:
            return
        
        is_socket = self.mode_combo.currentIndex() == 1
        
        if is_socket:
            host = self.ip_input.text().strip()
            try:
                port = int(self.port_input.text().strip())
            except ValueError:
                InfoBar.error(title="Invalid Port", content="Please enter a valid port number", 
                             parent=self, position=InfoBarPosition.TOP, duration=3000)
                return
            if not host:
                InfoBar.error(title="Invalid IP", content="Please enter a valid IP address", 
                             parent=self, position=InfoBarPosition.TOP, duration=3000)
                return
            
            self.data_reader = SocketReaderThread(host=host, port=port)
            InfoBar.info(title="Connecting...", content=f"Connecting to {host}:{port}", 
                        parent=self, position=InfoBarPosition.TOP, duration=2000)
        else:
            serial_port = "/dev/serial0"
            self.data_reader = SerialReaderThread(port=serial_port, baudrate=115200)
            InfoBar.info(title="Connecting...", content=f"Opening {serial_port}", 
                        parent=self, position=InfoBarPosition.TOP, duration=2000)
        
        self.data_reader.data_received.connect(self.on_data_received)
        self.data_reader.connection_status.connect(self.on_connection_status)
        self.data_reader.start()
        
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
            
            self.status_label.setText("Disconnected")
            self.status_indicator.setStyleSheet("background-color: #95a5a6; border-radius: 6px;")
            
            self.connect_btn.setEnabled(True)
            self.disconnect_btn.setEnabled(False)
            self.mode_combo.setEnabled(True)
            self.ip_input.setEnabled(True)
            self.port_input.setEnabled(True)
            
            InfoBar.success(title="Disconnected", content="Connection closed successfully", 
                           parent=self, position=InfoBarPosition.TOP, duration=2000)
    
    def on_data_received(self, data):
        """Handle received data"""
        # Format log message
        if 'currents' in data and data['currents']:
            seq = data.get('seq', 0)
            power = data.get('power', 0)
            avg_i = sum(data['currents']) / len(data['currents'])
            message = f"[{data['timestamp']}] #{seq:05d} | Avg I: {avg_i:.4f}A | P: {power:.3f}W"
        else:
            message = f"[{data['timestamp']}] {data.get('raw', 'No data')}"
        
        self.data_display.append(message)
        
        # Limit log size
        if self.data_display.document().blockCount() > 500:
            cursor = self.data_display.textCursor()
            cursor.movePosition(cursor.Start)
            cursor.movePosition(cursor.Down, cursor.KeepAnchor, 100)
            cursor.removeSelectedText()
        
        # Update chart data
        if 'currents' in data:
            for i in range(self.num_sensors):
                if i < len(data['currents']):
                    self.current_data[i].append(data['currents'][i])
                    if len(self.current_data[i]) > self.max_points:
                        self.current_data[i].pop(0)
        
        if 'voltages' in data:
            for i in range(self.num_sensors):
                if i < len(data['voltages']):
                    self.voltage_data[i].append(data['voltages'][i])
                    if len(self.voltage_data[i]) > self.max_points:
                        self.voltage_data[i].pop(0)
        
        # Update curves
        for i in range(self.num_sensors):
            if self.current_data[i]:
                x = [j / 100 for j in range(len(self.current_data[i]))]
                self.current_curves[i].setData(x, self.current_data[i])
    
    def on_connection_status(self, status):
        """Handle connection status"""
        if "Connected" in status:
            self.status_label.setText("Connected")
            self.status_indicator.setStyleSheet("background-color: #27ae60; border-radius: 6px;")
            InfoBar.success(title="Connected!", content=status, 
                           parent=self, position=InfoBarPosition.TOP, duration=3000)
        elif "Error" in status:
            self.status_label.setText("Error")
            self.status_indicator.setStyleSheet("background-color: #e74c3c; border-radius: 6px;")
            InfoBar.error(title="Connection Error", content=status, 
                         parent=self, position=InfoBarPosition.TOP, duration=5000)
        else:
            self.status_label.setText(status[:20] + "..." if len(status) > 20 else status)
            self.status_indicator.setStyleSheet("background-color: #f39c12; border-radius: 6px;")
    
    def toggle_sensor(self, idx, state):
        """Toggle sensor visibility"""
        visible = state == Qt.Checked.value if hasattr(Qt.Checked, 'value') else state == 2
        self.current_curves[idx].setVisible(visible)
    
    def select_all_sensors(self):
        for cb in self.sensor_checkboxes:
            cb.setChecked(True)
    
    def deselect_all_sensors(self):
        for cb in self.sensor_checkboxes:
            cb.setChecked(False)
    
    def clear_data(self):
        """Clear all data"""
        self.data_display.clear()
        for i in range(self.num_sensors):
            self.current_data[i].clear()
            self.voltage_data[i].clear()
            self.current_curves[i].setData([], [])
        InfoBar.info(title="Cleared", content="All data has been cleared", 
                    parent=self, position=InfoBarPosition.TOP, duration=2000)
    
    def export_chart(self):
        """Export chart as PNG"""
        try:
            exporter = pg.exporters.ImageExporter(self.plot_widget.plotItem)
            filename = f"monitoring_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            exporter.export(filename)
            InfoBar.success(title="Exported", content=f"Chart saved as {filename}", 
                           parent=self, position=InfoBarPosition.TOP, duration=3000)
        except Exception as e:
            InfoBar.error(title="Export Failed", content=str(e), 
                         parent=self, position=InfoBarPosition.TOP, duration=3000)