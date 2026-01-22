#!/usr/bin/env python3
import os
import csv
import time
import socket
import threading
from datetime import datetime, timezone

import serial

# ---- Config ----
SERIAL_PORT = os.environ.get("PICO_SERIAL_PORT", "/dev/serial0")  # or /dev/ttyACM0, /dev/ttyUSB0
BAUDRATE = int(os.environ.get("PICO_BAUDRATE", "921600"))

TCP_HOST = "0.0.0.0"
TCP_PORT = int(os.environ.get("FORWARD_PORT", "5000"))

LOG_DIR = os.environ.get("LOG_DIR", "/home/pi/pico_logs")
ROTATE_SECONDS = int(os.environ.get("ROTATE_SECONDS", str(30 * 60)))  # 30 minutes

# Expected CSV fields in each line after parsing:
# PICO: timestamp, i1..i9, voltage, checksum (total = 12 values after prefix)
EXPECTED_FIELDS = 12
CHECKSUM_THRESHOLD = 10000

# ---- TCP client management ----
clients = set()
clients_lock = threading.Lock()


def tcp_server():
    """Accept PC connections and keep a set of client sockets."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((TCP_HOST, TCP_PORT))
        srv.listen(5)
        print(f"[TCP] Listening on {TCP_HOST}:{TCP_PORT}")

        while True:
            conn, addr = srv.accept()
            conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            with clients_lock:
                clients.add(conn)
            print(f"[TCP] Client connected: {addr}")


def broadcast(line: bytes):
    """Send to all connected PCs; drop dead connections."""
    dead = []
    with clients_lock:
        for c in clients:
            try:
                c.sendall(line)
            except OSError:
                dead.append(c)
        for c in dead:
            try:
                c.close()
            except OSError:
                pass
            clients.discard(c)


# ---- CSV logging with rotation ----
class RotatingCSVLogger:
    def __init__(self, log_dir: str, rotate_seconds: int):
        self.log_dir = log_dir
        self.rotate_seconds = rotate_seconds
        self.current_path = None
        self.current_file = None
        self.csv_writer = None
        self.period_start = None

        os.makedirs(self.log_dir, exist_ok=True)

    def _period_floor(self, t: float) -> int:
        return int(t // self.rotate_seconds) * self.rotate_seconds

    def _open_new_file(self, t: float):
        if self.current_file:
            self.current_file.flush()
            self.current_file.close()

        self.period_start = self._period_floor(t)
        dt = datetime.fromtimestamp(self.period_start, tz=timezone.utc)
        # Filename includes start time of the 30-min window (UTC)
        name = dt.strftime("pico_%Y%m%d_%H%M%S_UTC.csv")
        self.current_path = os.path.join(self.log_dir, name)

        is_new = not os.path.exists(self.current_path)
        self.current_file = open(self.current_path, "a", newline="")
        self.csv_writer = csv.writer(self.current_file)

        if is_new:
            # Header - timestamp, 9 currents, voltage
            header = ["timestamp", 
                      *[f"i{i}" for i in range(1, 10)],
                      "voltage"]
            self.csv_writer.writerow(header)
            self.current_file.flush()

        print(f"[LOG] Writing to {self.current_path}")

    def write_row(self, row: list):
        """Write a parsed row to CSV"""
        now = time.time()
        if (self.current_file is None) or (self._period_floor(now) != self.period_start):
            self._open_new_file(now)

        self.csv_writer.writerow(row)
        # Flush so you don't lose data if power is cut
        self.current_file.flush()


def parse_pico_line(line_str: str):
    """
    Parse Pico serial line format:
    PICO: timestamp,i1,i2,i3,i4,i5,i6,i7,i8,i9,voltage,checksum
    
    Returns: (parsed_data, checksum, is_valid)
    parsed_data: [timestamp, i1..i9, voltage] (11 values)
    """
    # Remove "PICO: " prefix if present
    if line_str.startswith("PICO:"):
        line_str = line_str[5:].strip()
    
    parts = [p.strip() for p in line_str.split(",")]
    
    if len(parts) != EXPECTED_FIELDS:
        return None, None, False
    
    try:
        timestamp = parts[0]
        currents = parts[1:10]  # i1-i9
        voltage = parts[10]
        checksum = int(parts[11])
        
        # Check checksum threshold
        if checksum > CHECKSUM_THRESHOLD:
            print(f"[WARN] Checksum {checksum} exceeds threshold {CHECKSUM_THRESHOLD}")
        
        # Build output: timestamp, i1-i9, voltage (11 values)
        parsed_data = [timestamp] + currents + [voltage]
        return parsed_data, checksum, True
        
    except (ValueError, IndexError) as e:
        print(f"[WARN] Parse error: {e}")
        return None, None, False


def main():
    # Start TCP acceptor thread
    threading.Thread(target=tcp_server, daemon=True).start()

    logger = RotatingCSVLogger(LOG_DIR, ROTATE_SECONDS)

    # Serial loop with auto-reconnect
    while True:
        try:
            print(f"[SER] Opening {SERIAL_PORT} @ {BAUDRATE}...")
            with serial.Serial(SERIAL_PORT, BAUDRATE, timeout=1) as ser:
                # Read line-by-line from Pico
                while True:
                    raw = ser.readline()
                    if not raw:
                        continue

                    try:
                        line_str = raw.decode("utf-8", errors="replace").strip()
                    except Exception:
                        continue
                    
                    # Skip empty lines
                    if not line_str:
                        continue

                    # Parse Pico line
                    parsed_data, checksum, is_valid = parse_pico_line(line_str)
                    
                    if not is_valid:
                        print(f"[WARN] Invalid line: {line_str[:60]}...")
                        continue
                    
                    # 1) Log to CSV (timestamp, i1-i9, voltage)
                    logger.write_row(parsed_data)
                    
                    # 2) Forward parsed data to PC via TCP (CSV format with newline)
                    # Format: timestamp,i1,i2,...,i9,voltage\n
                    tcp_line = ",".join(parsed_data) + "\n"
                    broadcast(tcp_line.encode("utf-8"))

        except serial.SerialException as e:
            print(f"[SER] Serial error: {e}. Reconnecting in 2s...")
            time.sleep(2)
        except Exception as e:
            print(f"[ERR] {e}. Continuing in 2s...")
            time.sleep(2)


if __name__ == "__main__":
    main()
