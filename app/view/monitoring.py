# coding: utf-8
import numpy as np
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QTextCursor, QColor, QFont
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, 
                                QGridLayout, QGroupBox, QSplitter, QFrame, QStackedWidget,
                                QSizePolicy, QSpacerItem, QFileDialog)
from qfluentwidgets import (ScrollArea, PushButton, ComboBox, PrimaryPushButton, 
                            InfoBar, InfoBarPosition, CheckBox, LineEdit, CardWidget,
                            StrongBodyLabel, BodyLabel, CaptionLabel, SubtitleLabel,
                            ToolButton, TransparentToolButton, ToggleButton,
                            Slider, ProgressRing, IconWidget, SegmentedWidget,
                            SimpleCardWidget, ElevatedCardWidget, FlowLayout,
                            Pivot, SegmentedToggleToolWidget, PillPushButton,
                            TransparentPushButton, PrimaryToolButton, SpinBox,
                            SwitchButton)
from qfluentwidgets import FluentIcon as FIF
import pyqtgraph as pg
from pyqtgraph.exporters import ImageExporter
import sys
import os
import platform
import socket
import serial
from datetime import datetime

# Constants for gas production calculation (Faraday's law)
FARADAY = 96485.0          # C/mol
MOLAR_VOLUME_STP = 22.414  # L/mol at STP


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
        Expected format: timestamp,i1,i2,...,i9,vbus,cycle_us
        Total: 12 values (timestamp + 9 currents + voltage + cycle_us)
        """
        try:
            parts = line.strip().split(',')
            
            # Expected 12 values: timestamp, 9 currents, voltage, cycle_us
            if len(parts) >= 11:  # At least timestamp + 9 currents + voltage
                pico_timestamp = int(parts[0])
                
                # Parse 9 currents (indices 1-9) - values in mA, convert to A
                currents = [float(parts[i]) / 1000.0 for i in range(1, 10)]
                
                # Voltage at index 10 - value in mV, convert to V
                voltage = float(parts[10]) if len(parts) > 10 else 0.0
                
                # Cycle time at index 11 (optional)
                cycle_us = int(parts[11]) if len(parts) > 11 else 0
                
                return {
                    'timestamp': datetime.now().strftime("%H:%M:%S.%f")[:-3],
                    'pico_time': pico_timestamp,
                    'currents': currents,
                    'voltage': voltage,
                    'cycle_us': cycle_us,
                    'raw': line
                }
        except Exception as e:
            # Log parsing error
            print(f"Parse error: {e} for line: {line}")
        
        # If parsing fails, just return raw data
        return {
            'timestamp': datetime.now().strftime("%H:%M:%S.%f")[:-3],
            'currents': [0.0] * 9,
            'voltage': 0.0,
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
        """Parse incoming data from socket (eth_sender.py)
        Expected format: timestamp,i1,i2,...,i9,vbus,cycle_us
        Total: 12 values (timestamp + 9 currents + voltage + cycle_us)
        """
        try:
            parts = line.strip().split(',')
            
            # Expected 12 values: timestamp, 9 currents, voltage, cycle_us
            if len(parts) >= 11:  # At least timestamp + 9 currents + voltage
                pico_timestamp = int(parts[0])
                
                # Parse 9 currents (indices 1-9) - values in mA, convert to A
                currents = [float(parts[i]) / 1000.0 for i in range(1, 10)]
                
                # Voltage at index 10 - value in mV, convert to V
                voltage = float(parts[10]) if len(parts) > 10 else 0.0
                
                # Cycle time at index 11 (optional)
                cycle_us = int(parts[11]) if len(parts) > 11 else 0
                
                return {
                    'timestamp': datetime.now().strftime("%H:%M:%S.%f")[:-3],
                    'pico_time': pico_timestamp,
                    'currents': currents,
                    'voltage': voltage,
                    'cycle_us': cycle_us,
                    'raw': line
                }
        except Exception as e:
            print(f"Parse error: {e} for line: {line}")
        
        return {
            'timestamp': datetime.now().strftime("%H:%M:%S.%f")[:-3],
            'currents': [0.0] * 9,
            'voltage': 0.0,
            'raw': line
        }
    
    def stop(self):
        """Stop the reader thread"""
        self.running = False
        if self.socket_connection:
            try:
                print("Closing socket connection...")
                self.socket_connection.close()
            except:
                pass


# ============================================================================
# SENSOR CARD WIDGET - Compact sensor display with click support
# ============================================================================
class SensorCard(QFrame):
    """Compact sensor display card with toggle support"""
    sensor_clicked = Signal(int)
    
    def __init__(self, index, color, parent=None):
        super().__init__(parent)
        self.index = index
        self.color = color
        self.is_active = True
        self.setFixedSize(92, 76)
        self.setCursor(Qt.PointingHandCursor)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(3)
        
        # Sensor name with color indicator
        self.name_label = CaptionLabel(f"E{index + 1}")
        layout.addWidget(self.name_label, alignment=Qt.AlignCenter)
        
        # Current value
        self.value_label = StrongBodyLabel("0.00")
        layout.addWidget(self.value_label, alignment=Qt.AlignCenter)
        
        # Unit
        self.unit_label = CaptionLabel("mA")
        layout.addWidget(self.unit_label, alignment=Qt.AlignCenter)
        
        # Apply initial style after labels are created
        self._update_style()
    
    def mousePressEvent(self, event):
        """Handle mouse press to emit clicked signal"""
        if event.button() == Qt.LeftButton:
            self.sensor_clicked.emit(self.index)
        super().mousePressEvent(event)
    
    def _update_style(self):
        """Update card style based on active state"""
        if self.is_active:
            # Darker shade for hover
            hover_r = max(0, self.color[0] - 25)
            hover_g = max(0, self.color[1] - 25)
            hover_b = max(0, self.color[2] - 25)
            self.setStyleSheet(f"""
                SensorCard {{
                    background-color: rgb({self.color[0]}, {self.color[1]}, {self.color[2]});
                    border-radius: 6px;
                    border: none;
                }}
                SensorCard:hover {{
                    background-color: rgb({hover_r}, {hover_g}, {hover_b});
                }}
            """)
            # White text on colored background
            self.name_label.setStyleSheet("background: transparent; color: #ffffff; font-weight: 600; font-size: 11px;")
            self.value_label.setStyleSheet("background: transparent; font-size: 15px; font-weight: 600; color: #ffffff;")
            self.unit_label.setStyleSheet("background: transparent; color: rgba(255,255,255,0.85); font-size: 10px;")
        else:
            self.setStyleSheet("""
                SensorCard {
                    background-color: #f3f4f6;
                    border-radius: 6px;
                    border: none;
                }
                SensorCard:hover {
                    background-color: #e5e7eb;
                }
            """)
            # Colored name on gray background
            self.name_label.setStyleSheet(f"background: transparent; color: rgb({self.color[0]}, {self.color[1]}, {self.color[2]}); font-weight: 600; font-size: 11px;")
            self.value_label.setStyleSheet("background: transparent; font-size: 15px; font-weight: 600; color: #9ca3af;")
            self.unit_label.setStyleSheet("background: transparent; color: #d1d5db; font-size: 10px;")
    
    def setActive(self, active):
        """Set active state"""
        self.is_active = active
        self._update_style()
    
    def setValue(self, value):
        self.value_label.setText(f"{value:.2f}")


# ============================================================================
# HEATMAP CARD - Individual heatmap display
# ============================================================================
class HeatmapCard(CardWidget):
    """Heatmap display with title and stats"""
    
    def __init__(self, title, colormap_colors, bg_color="#fafafa", value_color="#333", parent=None):
        super().__init__(parent)
        self.value_color = value_color
        self.setStyleSheet("CardWidget { border: 1px solid #dcdcdc; border-radius: 6px; }")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)
        
        # Header
        self.title_label = StrongBodyLabel(title)
        layout.addWidget(self.title_label)
        
        # Heatmap container - no border, just background
        heatmap_container = QFrame()
        heatmap_container.setStyleSheet(f"""
            QFrame {{
                background: {bg_color};
                border-radius: 8px;
                border: none;
            }}
        """)
        heatmap_layout = QVBoxLayout(heatmap_container)
        heatmap_layout.setContentsMargins(4, 4, 4, 4)
        
        # Heatmap
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground(bg_color)
        self.plot_widget.setAspectLocked(True)
        self.plot_widget.hideAxis('bottom')
        self.plot_widget.hideAxis('left')
        self.plot_widget.setMinimumSize(200, 200)
        
        self.image_item = pg.ImageItem()
        self.plot_widget.addItem(self.image_item)
        
        # Colormap
        positions = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
        self.colormap = pg.ColorMap(positions, colormap_colors)
        self.image_item.setLookupTable(self.colormap.getLookupTable(0.0, 1.0, 256))
        
        # Text overlays - use dark color for visibility
        self.texts = []
        for row in range(3):
            row_texts = []
            for col in range(3):
                text = pg.TextItem(text="0.00", color=(15, 23, 42), anchor=(0.5, 0.5))  # Dark slate
                text.setPos(col + 0.5, row + 0.5)
                font = QFont()
                font.setBold(True)
                font.setPointSize(11)
                text.setFont(font)
                self.plot_widget.addItem(text)
                row_texts.append(text)
            self.texts.append(row_texts)
        
        self.plot_widget.setXRange(0, 3, padding=0.05)
        self.plot_widget.setYRange(0, 3, padding=0.05)
        
        heatmap_layout.addWidget(self.plot_widget)
        layout.addWidget(heatmap_container)
        
        # Total value with styled container
        total_container = QFrame()
        total_container.setStyleSheet(f"""
            QFrame {{
                background: {bg_color};
                border-radius: 8px;
                padding: 8px;
            }}
        """)
        total_layout = QVBoxLayout(total_container)
        total_layout.setContentsMargins(12, 8, 12, 8)
        
        self.total_label = SubtitleLabel("Total: 0.00")
        self.total_label.setStyleSheet(f"color: {value_color}; font-size: 18px; font-weight: 600;")
        total_layout.addWidget(self.total_label, alignment=Qt.AlignCenter)
        
        layout.addWidget(total_container)
    
    def setValues(self, values, unit="", decimal=2):
        """Update heatmap with 9 values"""
        matrix = np.array(values[:9]).reshape(3, 3)
        max_val = max(matrix.max(), 0.001)
        
        self.image_item.setImage(matrix, levels=(0, max_val))
        
        total = sum(values[:9])
        self.total_label.setText(f"Total: {total:.{decimal}f} {unit}")
        
        for i in range(9):
            row, col = i // 3, i % 3
            val = values[i]
            self.texts[row][col].setText(f"{val:.{decimal}f}")
            # Always use dark text for better readability
            self.texts[row][col].setColor((15, 23, 42))  # Dark slate


# ============================================================================
# MAIN INTERFACE
# ============================================================================
class USBDataInterface(ScrollArea):
    """Real-time Current Monitoring Dashboard"""
    
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName('usbDataInterface')
        
        self.data_reader = None
        self.is_windows = platform.system() == 'Windows'
        
        # Data structures
        self.num_sensors = 9
        self.voltage_data = []
        self.voltage_time_data = []  # Time data for voltage
        self.current_data = [[] for _ in range(self.num_sensors)]
        self.time_data = [[] for _ in range(self.num_sensors)]
        self.max_points = 400
        
        # Gas production
        self.h2_production = [0.0] * self.num_sensors
        self.o2_production = [0.0] * self.num_sensors
        self.sample_count = 0
        self.gas_update_interval = 100
        self.last_gas_time = None
        
        # Heatmap averaging mode
        self.use_average_mode = False
        self.current_buffer = [[] for _ in range(self.num_sensors)]  # Buffer for averaging
        self.average_window = 100  # Number of samples to average
        
        # Sensor colors (9 electrodes + 1 voltage) - Tailwind CSS Colors (600 shades)
        self.colors = [
            (220, 38, 38),    # red-600
            (37, 99, 235),    # blue-600
            (22, 163, 74),    # green-600
            (202, 138, 4),    # yellow-600
            (147, 51, 234),   # purple-600
            (234, 88, 12),    # orange-600
            (8, 145, 178),    # cyan-600
            (79, 70, 229),    # indigo-600
            (219, 39, 119),   # pink-600
            (37, 99, 235),    # Voltage - blue-600
        ]
        
        self.view = QWidget(self)
        self.view.setObjectName('monitoringView')
        self.mainLayout = QVBoxLayout(self.view)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.mainLayout.setSpacing(0)
        
        self._initUI()
        
        self.setWidget(self.view)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # Apply border radius to match application style
        self.setStyleSheet("""
            ScrollArea {
                background: transparent;
                border: none;
                border-top-left-radius: 10px;
            }
            #monitoringView {
                background: transparent;
                border-top-left-radius: 10px;
            }
        """)
    
    def _initUI(self):
        """Initialize the UI"""
        
        # =====================================================================
        # CONNECTION BAR - Minimal & Clean
        # =====================================================================
        conn_bar = QWidget()
        conn_bar.setFixedHeight(56)
        conn_bar.setStyleSheet("""
            QWidget {
                background: #ffffff;
                border-top-left-radius: 12px;
            }
        """)
        conn_layout = QHBoxLayout(conn_bar)
        conn_layout.setContentsMargins(24, 12, 24, 12)
        conn_layout.setSpacing(12)
        
        # Connection Mode - track state with variable since currentItem() can be unreliable
        self.connection_mode = "socket" if self.is_windows else "serial"
        self.mode_toggle = SegmentedWidget()
        self.mode_toggle.addItem(routeKey="serial", text="Serial")
        self.mode_toggle.addItem(routeKey="socket", text="Socket")
        self.mode_toggle.setCurrentItem(self.connection_mode)
        self.mode_toggle.setFixedWidth(180)
        self.mode_toggle.currentItemChanged.connect(self._on_mode_changed)
        conn_layout.addWidget(self.mode_toggle)
        
        conn_layout.addSpacing(8)
        
        # IP & Port inputs
        self.ip_label = CaptionLabel("Host")
        self.ip_label.setStyleSheet("color: #6b7280; font-weight: 500;")
        conn_layout.addWidget(self.ip_label)
        
        self.ip_input = LineEdit()
        self.ip_input.setText("192.168.50.2")
        self.ip_input.setFixedWidth(130)
        self.ip_input.setFixedHeight(34)
        # self.ip_input.setStyleSheet("""
        #     LineEdit {
        #         background: #6b7280;
        #         border: 1px solid #e2e8f0;
        #         border-radius: 8px;
        #         padding: 0 12px;
        #     }
        #     LineEdit:hover {
        #         border: 1px solid #cbd5e1;
        #     }
        #     LineEdit:focus {
        #         border: 1px solid #94a3b8;
        #         background: #ffffff;
        #     }
        # """)
        conn_layout.addWidget(self.ip_input)
        
        self.port_label = CaptionLabel("Port")
        self.port_label.setStyleSheet("color: #6b7280; font-weight: 500;")
        conn_layout.addWidget(self.port_label)
        
        self.port_input = LineEdit()
        self.port_input.setText("5000")
        self.port_input.setFixedWidth(70)
        self.port_input.setFixedHeight(34)
        # self.port_input.setStyleSheet("""
        #     LineEdit {
        #         background: #f8fafc;
        #         border: 1px solid #e2e8f0;
        #         border-radius: 8px;
        #         padding: 0 12px;
        #     }
        #     LineEdit:hover {
        #         border: 1px solid #cbd5e1;
        #     }
        #     LineEdit:focus {
        #         border: 1px solid #94a3b8;
        #         background: #ffffff;
        #     }
        # """)
        conn_layout.addWidget(self.port_input)
        
        conn_layout.addStretch()
        
        # Status Pill - wrapped in a styled container
        status_container = QWidget()
        status_container.setStyleSheet("""
            QWidget {
                background: #e5e7eb;
                border-radius: 16px;
            }
        """)
        status_layout = QHBoxLayout(status_container)
        status_layout.setContentsMargins(12, 6, 12, 6)
        status_layout.setSpacing(6)
        
        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet("color: #9ca3af; font-size: 10px; background: transparent;")
        status_layout.addWidget(self.status_dot)
        
        self.status_label = CaptionLabel("Disconnected")
        self.status_label.setStyleSheet("color: #6b7280; font-weight: 500; background: transparent;")
        status_layout.addWidget(self.status_label)
        
        conn_layout.addWidget(status_container)
        
        conn_layout.addSpacing(12)
        
        # Connect Button - Use default fluent style
        self.connect_btn = PrimaryPushButton("Connect")
        self.connect_btn.setFixedSize(100, 34)
        self.connect_btn.clicked.connect(self._toggle_connection)
        conn_layout.addWidget(self.connect_btn)
        
        self.mainLayout.addWidget(conn_bar)
        
        # Update visibility based on initial mode
        self._update_mode_visibility()
        
        # =====================================================================
        # TAB NAVIGATION - Clean Tab Style
        # =====================================================================
        pivot_bar = QWidget()
        pivot_bar.setFixedHeight(44)
        pivot_bar.setStyleSheet("""
            QWidget {
                background: #ffffff;
                border-bottom: 1px solid #dcdcdc;
            }
        """)
        pivot_layout = QHBoxLayout(pivot_bar)
        pivot_layout.setContentsMargins(24, 0, 24, 0)
        pivot_layout.setSpacing(0)
        
        # Pivot - clean fluent style navigation with custom styling
        self.pivot = Pivot()
        self.pivot.addItem(routeKey="chartView", text="Line Chart")
        self.pivot.addItem(routeKey="heatmapView", text="Heatmaps")
        self.pivot.setCurrentItem("chartView")
        self.pivot.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        # Custom pivot styling
        self.pivot.setStyleSheet("""
            Pivot {
                background: transparent;
                border: none;
            }
            Pivot::pane {
                border: none;
                background: transparent;
            }
            PivotItem {
                background: transparent;
                padding: 10px 24px;
                font-size: 13px;
                font-weight: 500;
                color: #6b7280;
                border: none;
            }
            PivotItem:hover {
                background: rgba(0, 0, 0, 0.04);
                border-radius: 6px;
            }
            PivotItem:checked {
                color: #0f172a;
                font-weight: 600;
                border-bottom: 2px solid #0f172a;
            }
        """)
        
        pivot_layout.addWidget(self.pivot, 1)
        
        self.mainLayout.addWidget(pivot_bar)
        
        # =====================================================================
        # STACKED CONTENT
        # =====================================================================
        self.stack = QStackedWidget()
        
        # ----- TAB 1: LINE CHART VIEW -----
        chart_view = QWidget()
        chart_view.setObjectName("chartView")  # For pivot navigation
        # chart_view.setStyleSheet("background: #f8fafa;")
        chart_view_layout = QVBoxLayout(chart_view)
        chart_view_layout.setContentsMargins(20, 20, 20, 20)
        chart_view_layout.setSpacing(16)
        
        # Use QSplitter for resizable panels
        chart_main = QSplitter(Qt.Horizontal)
        chart_main.setHandleWidth(10)  # Hide the splitter handle
        chart_main.setChildrenCollapsible(False)  # Prevent panels from being collapsed
        
        # Left: Chart + Sensors
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)
        
        # Chart Card
        chart_card = CardWidget()
        chart_card.setStyleSheet("CardWidget { border: 1px solid #dcdcdc; border-radius: 6px; }")
        # chart_card.setStyleSheet("""
        #     CardWidget {
        #         background: #ffffff;
        #         border: none;
        #         border-radius: 12px;
        #     }
        # """)
        chart_card_layout = QVBoxLayout(chart_card)
        chart_card_layout.setContentsMargins(16, 16, 16, 16)
        chart_card_layout.setSpacing(12)
        
        # Chart Header
        chart_header = QHBoxLayout()
        chart_title = StrongBodyLabel("Real-time Current Monitor")
        chart_header.addWidget(chart_title)
        chart_header.addStretch()
        
        # Window length control
        window_label = CaptionLabel("Window")
        window_label.setStyleSheet("color: #6b7280; font-weight: 500;")
        chart_header.addWidget(window_label)
        
        self.window_spin = SpinBox()
        self.window_spin.setRange(1, 300)
        self.window_spin.setValue(4)
        self.window_spin.setSuffix(" sec")
        self.window_spin.setFixedWidth(150)
        self.window_spin.setToolTip("Chart window length in seconds")
        self.window_spin.valueChanged.connect(self._on_window_changed)
        chart_header.addWidget(self.window_spin)
        
        chart_header.addSpacing(16)
        
        self.clear_btn = TransparentToolButton(FIF.DELETE)
        self.clear_btn.setToolTip("Clear Data")
        self.clear_btn.clicked.connect(self._clear_data)
        chart_header.addWidget(self.clear_btn)
        
        self.export_btn = TransparentToolButton(FIF.SAVE)
        self.export_btn.setToolTip("Export Chart")
        self.export_btn.clicked.connect(self._export_chart)
        chart_header.addWidget(self.export_btn)
        
        chart_card_layout.addLayout(chart_header)
        
        # PyQtGraph
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('#fafbfa')
        self.plot_widget.setLabel('left', 'Current (A)/Voltage (V)', color='#4b5563')
        self.plot_widget.setLabel('bottom', 'Time (s)', color='#4b5563')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.12)
        self.plot_widget.setMinimumHeight(300)
        self.plot_widget.getAxis('left').setTextPen('#6b7280')
        self.plot_widget.getAxis('bottom').setTextPen('#6b7280')
        self.plot_widget.getAxis('left').setPen(pg.mkPen('#d1d5db', width=1))
        self.plot_widget.getAxis('bottom').setPen(pg.mkPen('#d1d5db', width=1))
        
        self.current_curves = []
        for i in range(self.num_sensors):
            pen = pg.mkPen(color=self.colors[i], width=2)
            curve = self.plot_widget.plot(pen=pen, name=f"E{i+1}")
            self.current_curves.append(curve)
        
        self.current_curves.append(
            self.plot_widget.plot(pen=pg.mkPen(color=self.colors[9], width=2), name="Voltage")
        )
        
        chart_card_layout.addWidget(self.plot_widget)
        left_layout.addWidget(chart_card, stretch=1)
        
        # Sensor Cards Row
        sensor_card = CardWidget()
        sensor_card.setStyleSheet("CardWidget { border: 1px solid #dcdcdc; border-radius: 6px; }")
        sensor_layout = QVBoxLayout(sensor_card)
        sensor_layout.setContentsMargins(16, 14, 16, 14)
        sensor_layout.setSpacing(10)
        
        sensor_header = QHBoxLayout()
        sensor_title = StrongBodyLabel("Electrode Currents")
        sensor_title.setStyleSheet("background: transparent;")
        sensor_header.addWidget(sensor_title)
        sensor_header.addStretch()
        
        self.toggle_all_btn = TransparentToolButton(FIF.VIEW)
        self.toggle_all_btn.setToolTip("Toggle All Sensors")
        self.toggle_all_btn.clicked.connect(self._toggle_all_sensors)
        sensor_header.addWidget(self.toggle_all_btn)
        
        sensor_layout.addLayout(sensor_header)
        
        sensor_grid = QHBoxLayout()
        sensor_grid.setSpacing(6)
        
        self.sensor_cards = []
        self.sensor_visible = [True] * 10  # 9 electrodes + 1 voltage
        for i in range(9):
            card = SensorCard(i, self.colors[i])
            card.sensor_clicked.connect(self._toggle_sensor)
            self.sensor_cards.append(card)
            sensor_grid.addWidget(card)
        
        # Add voltage card
        self.voltage_card = SensorCard(9, self.colors[9])
        self.voltage_card.name_label.setText("mV")
        self.voltage_card.unit_label.setText("mV")
        self.voltage_card.sensor_clicked.connect(self._toggle_sensor)
        self.sensor_cards.append(self.voltage_card)
        sensor_grid.addWidget(self.voltage_card)
        
        sensor_layout.addLayout(sensor_grid)
        left_layout.addWidget(sensor_card)
        
        chart_main.addWidget(left_panel)
        
        # Right: Log Panel
        right_panel = CardWidget()
        right_panel.setStyleSheet("CardWidget { border: 1px solid #dcdcdc; border-radius: 6px; }")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(16, 16, 16, 16)
        right_layout.setSpacing(10)
        
        log_header = QHBoxLayout()
        log_title = StrongBodyLabel("Data Log")
        log_title.setStyleSheet("background: transparent;")
        log_header.addWidget(log_title)
        log_header.addStretch()
        
        self.clear_log_btn = TransparentToolButton(FIF.DELETE)
        self.clear_log_btn.setToolTip("Clear Log")
        self.clear_log_btn.clicked.connect(lambda: self.log_text.clear())
        log_header.addWidget(self.clear_log_btn)
        
        right_layout.addLayout(log_header)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setPlaceholderText("Waiting for data...")
        self.log_text.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)  # Disable text wrapping
        self.log_text.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # Hide horizontal scroll
        self.log_text.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)  # Show vertical only when needed
        self.log_text.setStyleSheet("""
            QTextEdit {
                font-family: 'SF Mono', 'Menlo', 'Monaco', 'Consolas', monospace;
                font-size: 11px;
                background: #f1f5f9;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 10px;
                line-height: 1.5;
            }
            QTextEdit:hover {
                border: 1px solid #cbd5e1;
            }
            QScrollBar:vertical {
                width: 6px;
                background: transparent;
                border-radius: 3px;
                margin: 2px;
            }
            QScrollBar::handle:vertical {
                background: #cbd5e1;
                border-radius: 3px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #94a3b8;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: transparent;
            }
        """)
        right_layout.addWidget(self.log_text)
        
        chart_main.addWidget(right_panel)
        
        # Set initial splitter sizes (3:1 ratio)
        chart_main.setSizes([900, 450])
        
        chart_view_layout.addWidget(chart_main)
        
        self.stack.addWidget(chart_view)
        
        # ----- TAB 2: HEATMAP VIEW -----
        heatmap_view = QWidget()
        heatmap_view.setObjectName("heatmapView")  # For pivot navigation
        # heatmap_view.setStyleSheet("background: #f8fafc;")
        heatmap_main = QVBoxLayout(heatmap_view)
        heatmap_main.setContentsMargins(20, 20, 20, 20)
        heatmap_main.setSpacing(16)
        
        # Heatmap header with export button and average mode switch
        heatmap_header = QHBoxLayout()
        heatmap_title = StrongBodyLabel("Electrode Heatmaps")
        heatmap_header.addWidget(heatmap_title)
        heatmap_header.addStretch()
        
        # Average mode switch
        avg_label = CaptionLabel("Instant")
        avg_label.setStyleSheet("color: #6b7280; font-weight: 500;")
        heatmap_header.addWidget(avg_label)
        
        self.avg_switch = SwitchButton()
        self.avg_switch.setToolTip("Toggle between instant values and 100-sample average")
        self.avg_switch.checkedChanged.connect(self._on_average_mode_changed)
        heatmap_header.addWidget(self.avg_switch)
        
        self.avg_mode_label = CaptionLabel("Avg (100)")
        self.avg_mode_label.setStyleSheet("color: #9ca3af; font-weight: 500;")
        heatmap_header.addWidget(self.avg_mode_label)
        
        heatmap_header.addSpacing(16)
        
        self.export_heatmap_btn = TransparentToolButton(FIF.SAVE)
        self.export_heatmap_btn.setToolTip("Export Heatmaps")
        self.export_heatmap_btn.clicked.connect(self._export_heatmaps)
        heatmap_header.addWidget(self.export_heatmap_btn)
        
        heatmap_main.addLayout(heatmap_header)
        
        # Top Row: 3 Heatmaps
        heatmap_row = QHBoxLayout()
        heatmap_row.setSpacing(12)
        
        # Current Heatmap - Solid red gradient
        current_colors = [
            (255, 245, 245),  # Very light red
            (254, 178, 178),  # Light red
            (252, 129, 129),  # Medium light
            (239, 68, 68),    # Red
            (220, 38, 38),    # Dark red
            (185, 28, 28),    # Very dark red
        ]
        self.current_heatmap = HeatmapCard("Current (mA)", current_colors, "#fff5f5", "#dc2626")
        heatmap_row.addWidget(self.current_heatmap)
        
        # H2 Heatmap - Solid blue gradient
        h2_colors = [
            (239, 246, 255),  # Very light blue
            (191, 219, 254),  # Light blue
            (147, 197, 253),  # Medium light
            (59, 130, 246),   # Blue
            (37, 99, 235),    # Dark blue
            (29, 78, 216),    # Very dark blue
        ]
        self.h2_heatmap = HeatmapCard("H₂ Production (L)", h2_colors, "#eff6ff", "#2563eb")
        heatmap_row.addWidget(self.h2_heatmap)
        
        # O2 Heatmap - Solid green gradient
        o2_colors = [
            (236, 253, 245),  # Very light green
            (167, 243, 208),  # Light green
            (110, 231, 183),  # Medium light
            (52, 211, 153),   # Green
            (16, 185, 129),   # Dark green
            (5, 150, 105),    # Very dark green
        ]
        self.o2_heatmap = HeatmapCard("O₂ Production (L)", o2_colors, "#ecfdf5", "#059669")
        heatmap_row.addWidget(self.o2_heatmap)
        
        heatmap_main.addLayout(heatmap_row, stretch=2)
        
        # Bottom Row: Stats & Controls
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(12)
        
        # Gas Production Summary Card
        gas_card = CardWidget()
        gas_card.setStyleSheet("CardWidget { border: 1px solid #dcdcdc; border-radius: 6px; }")
        gas_layout = QVBoxLayout(gas_card)
        gas_layout.setContentsMargins(20, 18, 20, 18)
        gas_layout.setSpacing(14)
        
        gas_header = QHBoxLayout()
        gas_title = StrongBodyLabel("Gas Production Summary")
        gas_title.setStyleSheet("background: transparent;")
        gas_header.addWidget(gas_title)
        gas_header.addStretch()
        
        self.reset_gas_btn = TransparentToolButton(FIF.SYNC)
        self.reset_gas_btn.setToolTip("Reset Calculations")
        self.reset_gas_btn.clicked.connect(self._reset_gas_production)
        gas_header.addWidget(self.reset_gas_btn)
        
        gas_layout.addLayout(gas_header)
        
        # Gas stats grid - simple solid colors
        gas_grid = QGridLayout()
        gas_grid.setSpacing(12)
        
        # H2 Stats
        h2_frame = QFrame()
        h2_frame.setStyleSheet("""
            QFrame {
                background: #dbeafe;
                border-radius: 8px;
            }
        """)
        h2_inner = QVBoxLayout(h2_frame)
        h2_inner.setContentsMargins(16, 12, 16, 12)
        h2_inner.setSpacing(4)
        h2_icon = SubtitleLabel("H₂")
        h2_icon.setStyleSheet("color: #1e40af; font-size: 13px; font-weight: 600;")
        h2_inner.addWidget(h2_icon)
        self.h2_total_label = SubtitleLabel("0.0000 L")
        self.h2_total_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #1d4ed8;")
        h2_inner.addWidget(self.h2_total_label)
        self.h2_rate_label = CaptionLabel("Rate: 0.0000 L/min")
        self.h2_rate_label.setStyleSheet("color: #3b82f6;")
        h2_inner.addWidget(self.h2_rate_label)
        gas_grid.addWidget(h2_frame, 0, 0)
        
        # O2 Stats
        o2_frame = QFrame()
        o2_frame.setStyleSheet("""
            QFrame {
                background: #dcfce7;
                border-radius: 8px;
            }
        """)
        o2_inner = QVBoxLayout(o2_frame)
        o2_inner.setContentsMargins(16, 12, 16, 12)
        o2_inner.setSpacing(4)
        o2_icon = SubtitleLabel("O₂")
        o2_icon.setStyleSheet("color: #166534; font-size: 13px; font-weight: 600;")
        o2_inner.addWidget(o2_icon)
        self.o2_total_label = SubtitleLabel("0.0000 L")
        self.o2_total_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #16a34a;")
        o2_inner.addWidget(self.o2_total_label)
        self.o2_rate_label = CaptionLabel("Rate: 0.0000 L/min")
        self.o2_rate_label.setStyleSheet("color: #22c55e;")
        o2_inner.addWidget(self.o2_rate_label)
        gas_grid.addWidget(o2_frame, 0, 1)
        
        gas_layout.addLayout(gas_grid)
        bottom_row.addWidget(gas_card, stretch=1)
        
        # Electrode Details Card
        electrode_card = CardWidget()
        electrode_card.setStyleSheet("CardWidget { border: 1px solid #dcdcdc; border-radius: 6px; }")
        electrode_layout = QVBoxLayout(electrode_card)
        electrode_layout.setContentsMargins(20, 18, 20, 18)
        electrode_layout.setSpacing(12)
        
        electrode_header = StrongBodyLabel("Electrode Details")
        electrode_header.setStyleSheet("background: transparent;")
        electrode_layout.addWidget(electrode_header)
        
        # Electrode grid
        self.electrode_grid = QGridLayout()
        self.electrode_grid.setSpacing(8)
        
        self.electrode_labels = []
        for i in range(9):
            row, col = i // 3, i % 3
            label = BodyLabel(f"E{i+1}: 0.00 mA")
            label.setStyleSheet(f"""
                padding: 8px 12px;
                border-radius: 6px;
                font-family: 'SF Mono', 'Menlo', 'Monaco', 'Consolas', monospace;
                font-size: 12px;
                color: rgb({self.colors[i][0]}, {self.colors[i][1]}, {self.colors[i][2]});
            """)
            self.electrode_labels.append(label)
            self.electrode_grid.addWidget(label, row, col)
        
        electrode_layout.addLayout(self.electrode_grid)
        electrode_layout.addStretch()
        
        bottom_row.addWidget(electrode_card, stretch=1)
        
        heatmap_main.addLayout(bottom_row, stretch=1)
        
        self.stack.addWidget(heatmap_view)
        
        self.mainLayout.addWidget(self.stack, stretch=1)
        
        # Connect pivot to stacked widget
        self.stack.setCurrentWidget(chart_view)
        self.pivot.currentItemChanged.connect(
            lambda routeKey: self.stack.setCurrentWidget(self.stack.findChild(QWidget, routeKey))
        )
    
    # =========================================================================
    # UI ACTIONS
    # =========================================================================
    
    def _on_pivot_changed(self, routeKey):
        """Handle pivot navigation"""
        widget = self.stack.findChild(QWidget, routeKey)
        if widget:
            self.stack.setCurrentWidget(widget)
    
    def _on_mode_changed(self, routeKey):
        """Handle connection mode change from signal"""
        self.connection_mode = routeKey
        self._update_mode_visibility()
    
    def _on_window_changed(self, value):
        """Handle window length change"""
        # 100 samples per second, so multiply by 100
        self.max_points = value * 100
        # Clear existing data to apply new window
        for i in range(self.num_sensors):
            while len(self.current_data[i]) > self.max_points:
                self.current_data[i].pop(0)
                self.time_data[i].pop(0)
    
    def _on_average_mode_changed(self, checked):
        """Handle average mode toggle"""
        self.use_average_mode = checked
        # Update label styling to show active state
        if checked:
            self.avg_mode_label.setStyleSheet("color: #0f172a; font-weight: 600;")
        else:
            self.avg_mode_label.setStyleSheet("color: #9ca3af; font-weight: 500;")
        # Clear buffer when switching modes
        self.current_buffer = [[] for _ in range(self.num_sensors)]
    
    def _update_mode_visibility(self):
        """Update visibility of socket input fields"""
        is_socket = self.connection_mode == "socket"
        self.ip_label.setVisible(is_socket)
        self.ip_input.setVisible(is_socket)
        self.port_label.setVisible(is_socket)
        self.port_input.setVisible(is_socket)
    
    def _toggle_connection(self):
        """Toggle connection state"""
        if self.data_reader is None:
            self._connect()
        else:
            self._disconnect()
    
    def _connect(self):
        """Connect to data source"""
        is_socket = self.connection_mode == "socket"
        
        if is_socket:
            host = self.ip_input.text().strip()
            try:
                port = int(self.port_input.text().strip())
            except ValueError:
                InfoBar.error(title="Error", content="Invalid port number",
                             parent=self, position=InfoBarPosition.TOP, duration=3000)
                return
            # print("Connecting to socket:", host, port)
            self.data_reader = SocketReaderThread(host=host, port=port)
        else:
            self.data_reader = SerialReaderThread(port="/dev/serial0", baudrate=115200)
        
        self.data_reader.data_received.connect(self._on_data_received)
        self.data_reader.connection_status.connect(self._on_connection_status)
        self.data_reader.start()
        
        self.connect_btn.setText("Stop")
        self.mode_toggle.setEnabled(False)
        self.ip_input.setEnabled(False)
        self.port_input.setEnabled(False)
        
        # Update status
        self.status_dot.setText("●")
        self.status_dot.setStyleSheet("color: #f59e0b; font-size: 10px;")
        self.status_label.setText("Connecting...")
        self.status_label.setStyleSheet("color: #f59e0b; font-weight: 500;")
    
    def _disconnect(self):
        """Disconnect from data source"""
        if self.data_reader:
            # Show disconnecting status immediately
            self.status_dot.setText("●")
            self.status_dot.setStyleSheet("color: #f59e0b; font-size: 10px;")
            self.status_label.setText("Disconnecting...")
            self.status_label.setStyleSheet("color: #f59e0b; font-weight: 500;")
            self.connect_btn.setEnabled(False)
            
            # Stop the reader
            self.data_reader.stop()
            
            # Use a timer to wait for thread without blocking UI
            self._disconnect_timer = QTimer()
            self._disconnect_timer.setSingleShot(True)
            self._disconnect_timer.timeout.connect(self._finish_disconnect)
            self._disconnect_timer.start(100)  # Check every 100ms
        else:
            self._finish_disconnect()
    
    def _finish_disconnect(self):
        """Finish the disconnect process after thread stops"""
        if self.data_reader:
            if self.data_reader.isRunning():
                # Still running, check again later
                self._disconnect_timer.start(100)
                return
            self.data_reader = None
        
        self.connect_btn.setText("Connect")
        self.connect_btn.setEnabled(True)
        self.mode_toggle.setEnabled(True)
        self.ip_input.setEnabled(True)
        self.port_input.setEnabled(True)
        
        self.status_dot.setText("●")
        self.status_dot.setStyleSheet("color: #9ca3af; font-size: 10px;")
        self.status_label.setText("Disconnected")
        self.status_label.setStyleSheet("color: #6b7280; font-weight: 500;")
    
    def _on_connection_status(self, status):
        """Handle connection status update"""
        if "Connected" in status:
            self.status_dot.setText("●")
            self.status_dot.setStyleSheet("color: #22c55e; font-size: 10px;")
            self.status_label.setText("Connected")
            self.status_label.setStyleSheet("color: #16a34a; font-weight: 500;")
            InfoBar.success(title="Connected", content=status,
                           parent=self, position=InfoBarPosition.TOP, duration=2000)
        elif "Error" in status or "Disconnected" in status:
            self.status_dot.setText("●")
            self.status_dot.setStyleSheet("color: #ef4444; font-size: 10px;")
            self.status_label.setText("Error")
            self.status_label.setStyleSheet("color: #dc2626; font-weight: 500;")
            InfoBar.error(title="Connection Error", content=status,
                         parent=self, position=InfoBarPosition.TOP, duration=4000)
            
            # Auto-reset UI when connection fails
            if self.data_reader:
                self.data_reader.stop()
                self.data_reader = None
            
            self.connect_btn.setText("Connect")
            self.connect_btn.setEnabled(True)
            self.mode_toggle.setEnabled(True)
            self.ip_input.setEnabled(True)
            self.port_input.setEnabled(True)
    
    def _on_data_received(self, data):
        """Handle received data"""
        currents = data.get('currents', [0.0] * 9)
        voltage = data.get('voltage', 0.0)
        pico_time = data.get('pico_time', 0)
        
        # Update log
        avg_i = sum(currents) / len(currents) if currents else 0
        log_msg = f"[{data['timestamp']}] Sum: {sum(currents)*1000:.2f}mA | Avg: {avg_i*1000:.2f}mA | V: {voltage:.3f}V"
        self.log_text.append(log_msg)
        if self.log_text.document().blockCount() > 200:
            cursor = self.log_text.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            cursor.movePosition(QTextCursor.MoveOperation.Down, QTextCursor.MoveMode.KeepAnchor, 50)
            cursor.removeSelectedText()
        
        # Update sensor cards
        total_current = 0
        current_ma = []
        for i, current in enumerate(currents[:9]):
            ma_val = current * 1000
            current_ma.append(ma_val)
            self.sensor_cards[i].setValue(ma_val)
            self.electrode_labels[i].setText(f"E{i+1}: {ma_val:.2f} mA")
            total_current += ma_val
        
        # Update voltage card (index 9)
        self.sensor_cards[9].setValue(voltage)
        
        # Update sample count
        self.sample_count += 1
        
        # Store data
        for i in range(self.num_sensors):
            if i < len(currents):
                self.current_data[i].append(currents[i])
                self.time_data[i].append(pico_time / 1e6)
                if len(self.current_data[i]) > self.max_points:
                    self.current_data[i].pop(0)
                    self.time_data[i].pop(0)
        
        # Store voltage data
        self.voltage_data.append(voltage)
        self.voltage_time_data.append(pico_time / 1e6)
        if len(self.voltage_data) > self.max_points:
            self.voltage_data.pop(0)
            self.voltage_time_data.pop(0)
        
        # Update chart
        for i in range(self.num_sensors):
            if self.current_data[i] and self.sensor_visible[i]:
                x = [j / 100 for j in range(len(self.current_data[i]))]
                self.current_curves[i].setData(x, self.current_data[i])
        
        # Update voltage curve
        if self.voltage_data and self.sensor_visible[9]:
            x_voltage = [j / 100 for j in range(len(self.voltage_data))]
            self.current_curves[9].setData(x_voltage, self.voltage_data)
        
        # Update heatmaps with average mode support
        if self.use_average_mode:
            # Buffer current values for batch averaging
            for i in range(self.num_sensors):
                self.current_buffer[i].append(current_ma[i] if i < len(current_ma) else 0)
            
            # Only update heatmap when we have collected 100 packets
            if len(self.current_buffer[0]) >= self.average_window:
                # Calculate averages from the batch
                avg_values = []
                for i in range(self.num_sensors):
                    avg_values.append(sum(self.current_buffer[i]) / len(self.current_buffer[i]))
                self.current_heatmap.setValues(avg_values, "mA", 2)
                # Clear buffer for next batch
                self.current_buffer = [[] for _ in range(self.num_sensors)]
        else:
            self.current_heatmap.setValues(current_ma, "mA", 2)
        
        # Update gas production every N samples
        if self.sample_count % self.gas_update_interval == 0:
            self._update_gas_production()
    
    def _update_gas_production(self):
        """Calculate gas production using Faraday's law"""
        current_time = datetime.now()
        
        for i in range(self.num_sensors):
            if len(self.current_data[i]) >= 2:
                currents = np.array(self.current_data[i][-self.gas_update_interval:])
                times = np.array(self.time_data[i][-self.gas_update_interval:])
                
                if len(currents) >= 2:
                    dt = np.diff(times)
                    i_mid = 0.5 * (currents[1:] + currents[:-1])
                    Q = np.sum(i_mid * dt)
                    
                    self.h2_production[i] += (Q / (2 * FARADAY)) * MOLAR_VOLUME_STP
                    self.o2_production[i] += (Q / (4 * FARADAY)) * MOLAR_VOLUME_STP
        
        h2_total = sum(self.h2_production)
        o2_total = sum(self.o2_production)
        
        # Calculate rates
        h2_rate, o2_rate = 0, 0
        if self.last_gas_time:
            elapsed = (current_time - self.last_gas_time).total_seconds() / 60
            if elapsed > 0:
                h2_rate = h2_total / max(elapsed, 0.001)
                o2_rate = o2_total / max(elapsed, 0.001)
        
        # Update heatmaps
        self.h2_heatmap.setValues(self.h2_production, "L", 4)
        self.o2_heatmap.setValues(self.o2_production, "L", 4)
        
        # Update summary labels
        self.h2_total_label.setText(f"{h2_total:.4f} L")
        self.h2_rate_label.setText(f"Rate: {h2_rate:.4f} L/min")
        self.o2_total_label.setText(f"{o2_total:.4f} L")
        self.o2_rate_label.setText(f"Rate: {o2_rate:.4f} L/min")
        
        self.last_gas_time = current_time
    
    def _toggle_sensor(self, idx):
        """Toggle sensor visibility"""
        self.sensor_visible[idx] = not self.sensor_visible[idx]
        # Toggle curve visibility for all sensors including voltage (index 9)
        self.current_curves[idx].setVisible(self.sensor_visible[idx])
        self.sensor_cards[idx].setActive(self.sensor_visible[idx])
    
    def _toggle_all_sensors(self):
        """Toggle all sensors visibility"""
        all_visible = all(self.sensor_visible)
        for i in range(10):  # 9 electrodes + 1 voltage
            self.sensor_visible[i] = not all_visible
            # Toggle curves for all sensors including voltage
            self.current_curves[i].setVisible(self.sensor_visible[i])
            self.sensor_cards[i].setActive(self.sensor_visible[i])
    
    def _clear_data(self):
        """Clear all data"""
        self.log_text.clear()
        for i in range(self.num_sensors):
            self.current_data[i].clear()
            self.time_data[i].clear()
            self.current_curves[i].setData([], [])
        
        # Clear voltage data
        self.voltage_data.clear()
        self.voltage_time_data.clear()
        self.current_curves[9].setData([], [])  # Clear voltage curve
        
        self._reset_gas_production()
        
        for card in self.sensor_cards:
            card.setValue(0)
        
        self.current_heatmap.setValues([0]*9, "mA", 2)
        
        InfoBar.info(title="Cleared", content="All data cleared",
                    parent=self, position=InfoBarPosition.TOP, duration=2000)
    
    def _reset_gas_production(self):
        """Reset gas production"""
        self.h2_production = [0.0] * self.num_sensors
        self.o2_production = [0.0] * self.num_sensors
        self.sample_count = 0
        self.last_gas_time = None
        
        self.h2_heatmap.setValues([0]*9, "L", 4)
        self.o2_heatmap.setValues([0]*9, "L", 4)
        self.h2_total_label.setText("0.0000 L")
        self.h2_rate_label.setText("Rate: 0.0000 L/min")
        self.o2_total_label.setText("0.0000 L")
        self.o2_rate_label.setText("Rate: 0.0000 L/min")
        
        InfoBar.info(title="Reset", content="Gas calculations reset",
                    parent=self, position=InfoBarPosition.TOP, duration=2000)
    
    def _export_chart(self):
        """Export chart as PNG"""
        try:
            default_name = f"monitoring_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Save Chart",
                default_name,
                "PNG Image (*.png);;All Files (*)"
            )
            if not filename:
                return  # User cancelled
            
            exporter = ImageExporter(self.plot_widget.plotItem)
            # Set high resolution export (3x scale for better quality)
            exporter.parameters()['width'] = int(self.plot_widget.width() * 3)
            exporter.parameters()['height'] = int(self.plot_widget.height() * 3)
            exporter.parameters()['antialias'] = True
            exporter.export(filename)
            InfoBar.success(title="Exported", content=f"Saved as {filename}",
                           parent=self, position=InfoBarPosition.TOP, duration=3000)
        except Exception as e:
            InfoBar.error(title="Export Failed", content=str(e),
                         parent=self, position=InfoBarPosition.TOP, duration=3000)
    
    def _export_heatmaps(self):
        """Export all heatmaps as PNG images"""
        try:
            folder = QFileDialog.getExistingDirectory(
                self,
                "Select Folder to Save Heatmaps",
                ""
            )
            if not folder:
                return  # User cancelled
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            heatmaps = [
                (self.current_heatmap.plot_widget, "current"),
                (self.h2_heatmap.plot_widget, "h2_production"),
                (self.o2_heatmap.plot_widget, "o2_production"),
            ]
            
            exported_count = 0
            for plot_widget, name in heatmaps:
                exporter = ImageExporter(plot_widget.plotItem)
                exporter.parameters()['width'] = int(plot_widget.width() * 3)
                exporter.parameters()['height'] = int(plot_widget.height() * 3)
                exporter.parameters()['antialias'] = True
                filename = os.path.join(folder, f"heatmap_{name}_{timestamp}.png")
                exporter.export(filename)
                exported_count += 1
            
            InfoBar.success(title="Exported", content=f"Saved {exported_count} heatmaps to {folder}",
                           parent=self, position=InfoBarPosition.TOP, duration=3000)
        except Exception as e:
            InfoBar.error(title="Export Failed", content=str(e),
                         parent=self, position=InfoBarPosition.TOP, duration=3000)