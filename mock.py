# Add to test.py at the top
import os
from PySide6.QtCore import Qt, QThread, Signal
import serial
from datetime import datetime  # Import datetime module
import time

MOCK_MODE = os.getenv('MOCK_USB', 'false').lower() == 'true'

class USBDataReader(QThread):
    """Thread for reading USB serial data"""
    data_received = Signal(dict)
    connection_status = Signal(str)
    
    def __init__(self, port=None, baudrate=115200):
        super().__init__()
        self.port = port or self.find_pico_port()
        self.baudrate = baudrate
        self.serial_connection = None
        self.running = False
    
    def run(self):
        if MOCK_MODE:
            self.run_mock()
        else:
            self.run_real()
    
    def run_mock(self):
        """Simulate USB data"""
        import random
        self.running = True
        self.connection_status.emit("Mock Mode: Connected to /dev/mock")
        
        counter = 0
        while self.running:
            voltage = 12.5 + random.uniform(-0.5, 0.5)
            current = 3.2 + random.uniform(-0.2, 0.2)
            
            data = {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
                'voltage': voltage,
                'current': current
            }
            self.data_received.emit(data)
            counter += 1
            time.sleep(1)
    
    def run_real(self):
        """Original run method"""
        try:
            self.connection_status.emit(f"Connecting to {self.port} ({self.get_os()})...")
            self.serial_connection = serial.Serial(self.port, self.baudrate, timeout=1)
            self.running = True
            self.connection_status.emit(f"Connected to {self.port}")
            
            while self.running:
                if self.serial_connection.in_waiting:
                    line = self.serial_connection.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        data = self.parse_data(line)
                        if data:
                            self.data_received.emit(data)
        except serial.SerialException as e:
            self.connection_status.emit(f"Connection Error: {e}")
        except Exception as e:
            self.connection_status.emit(f"Error: {e}")