import sys
import serial
import platform
import subprocess
import time
import random
import os
from datetime import datetime
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtCore import Qt, QThread, Signal

class USBDataReader(QThread):
    """Thread for reading USB serial data"""
    data_received = Signal(dict)
    connection_status = Signal(str)
    
    def __init__(self, port=None, baudrate=115200, mock_mode=False):
        super().__init__()
        self.mock_mode = mock_mode or os.getenv('MOCK_USB', 'false').lower() == 'true'
        self.port = port or self.find_pico_port()
        self.baudrate = baudrate
        self.serial_connection = None
        self.running = False
    
    @staticmethod
    def get_os():
        """Detect operating system"""
        return platform.system()
    
    @staticmethod
    def find_pico_port():
        """Auto-detect Raspberry Pi Pico port"""
        os_type = platform.system()
        
        try:
            if os_type == 'Windows':
                import winreg
                ports = []
                try:
                    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'HARDWARE\DEVICEMAP\SERIALCOMM')
                    for i in range(winreg.QueryInfoKey(key)[1]):
                        name, value, _ = winreg.EnumValue(key, i)
                        ports.append(value)
                except:
                    pass
                for port in ports + [f'COM{i}' for i in range(1, 10)]:
                    try:
                        ser = serial.Serial(port, timeout=0.5)
                        ser.close()
                        return port
                    except:
                        pass
            
            elif os_type == 'Darwin':  # macOS
                import glob
                # Check for virtual port first (socat simulation)
                if os.path.exists('/tmp/pico_virtual'):
                    return '/tmp/pico_virtual'
                
                # Real Pico ports
                ports = glob.glob('/dev/tty.usbmodem*') + glob.glob('/dev/tty.SLAB_USBtoUART*')
                if ports:
                    return ports[0]
            
            elif os_type == 'Linux':
                import glob
                ports = glob.glob('/dev/ttyACM*') + glob.glob('/dev/ttyUSB*')
                if ports:
                    return ports[0]
        
        except Exception as e:
            print(f"Error detecting port: {e}")
        
        # Defaults
        if os_type == 'Windows':
            return 'COM3'
        elif os_type == 'Darwin':
            return '/dev/tty.usbmodem14201'
        else:
            return '/dev/ttyACM0'
    
    def run(self):
        """Run the data reader"""
        if self.mock_mode:
            self.run_mock()
        else:
            self.run_real()
    
    def run_mock(self):
        """Simulate USB data with random values"""
        self.running = True
        self.connection_status.emit("Mock Mode: Simulating Pico data...")
        
        try:
            while self.running:
                # Simulate realistic sensor readings
                voltage = 12.5 + random.uniform(-0.5, 0.5)
                current = 3.2 + random.uniform(-0.2, 0.2)
                
                data = {
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
                    'voltage': round(voltage, 2),
                    'current': round(current, 2)
                }
                self.data_received.emit(data)
                time.sleep(1)  # Send data every 1 second
        except Exception as e:
            self.connection_status.emit(f"Mock Error: {e}")
    
    def run_real(self):
        """Real USB serial connection"""
        try:
            self.connection_status.emit(f"Connecting to {self.port} ({self.get_os()})...")
            self.serial_connection = serial.Serial(self.port, self.baudrate, timeout=1)
            self.running = True
            self.connection_status.emit(f"Connected to {self.port} at {self.baudrate} baud")
            
            while self.running:
                if self.serial_connection.in_waiting:
                    line = self.serial_connection.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        data = self.parse_data(line)
                        if data:
                            self.data_received.emit(data)
        except serial.SerialException as e:
            self.connection_status.emit(f"Connection Error: {e}")
            time.sleep(2)
        except Exception as e:
            self.connection_status.emit(f"Error: {e}")
    
    def parse_data(self, line):
        """Parse Pico data format: voltage,current"""
        try:
            parts = line.split(',')
            if len(parts) >= 2:
                voltage = float(parts[0].strip())
                current = float(parts[1].strip())
                return {
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
                    'voltage': voltage,
                    'current': current
                }
        except ValueError:
            pass
        return None
    
    def stop(self):
        self.running = False
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()