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
BAUDRATE = int(os.environ.get("PICO_BAUDRATE", "115200"))

TCP_HOST = "0.0.0.0"
TCP_PORT = int(os.environ.get("FORWARD_PORT", "5000"))

LOG_DIR = os.environ.get("LOG_DIR", "/home/pi/pico_logs")
ROTATE_SECONDS = int(os.environ.get("ROTATE_SECONDS", str(30 * 60)))  # 30 minutes

# Expected CSV fields in each line:
# seq, timestamp, v1..v9, i1..i9, power (total = 21 values)
EXPECTED_FIELDS = 21

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
        # Filename includes start time of the 30-min window (UTC); adjust if you prefer local time.
        name = dt.strftime("pico_%Y%m%d_%H%M%S_UTC.csv")
        self.current_path = os.path.join(self.log_dir, name)

        is_new = not os.path.exists(self.current_path)
        self.current_file = open(self.current_path, "a", newline="")
        self.csv_writer = csv.writer(self.current_file)

        if is_new:
            # Header - seq, timestamp, 9 voltages, 9 currents, power
            header = ["seq", "timestamp", 
                      *[f"v{i}" for i in range(1, 10)],
                      *[f"i{i}" for i in range(1, 10)],
                      "power"]
            self.csv_writer.writerow(header)
            self.current_file.flush()

        print(f"[LOG] Writing to {self.current_path}")

    def write_row_from_line(self, line_str: str):
        now = time.time()
        if (self.current_file is None) or (self._period_floor(now) != self.period_start):
            self._open_new_file(now)

        # Parse CSV line; tolerate whitespace
        parts = [p.strip() for p in line_str.split(",")]
        if len(parts) != EXPECTED_FIELDS:
            # Log unexpected field count for debugging
            print(f"[WARN] Unexpected field count ({len(parts)}, expected {EXPECTED_FIELDS}): {line_str[:50]}...")
            return

        self.csv_writer.writerow(parts)
        # Flush so you don’t lose data if power is cut (small performance cost)
        self.current_file.flush()

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

                    # Ensure newline-delimited streaming over TCP
                    if not raw.endswith(b"\n"):
                        raw += b"\n"

                    try:
                        line_str = raw.decode("utf-8", errors="replace").strip()
                    except Exception:
                        continue

                    # 1) log to CSV (parsed)
                    logger.write_row_from_line(line_str)

                    # 2) forward raw line to PC (as bytes)
                    broadcast(raw)

        except serial.SerialException as e:
            print(f"[SER] Serial error: {e}. Reconnecting in 2s...")
            time.sleep(2)
        except Exception as e:
            print(f"[ERR] {e}. Continuing in 2s...")
            time.sleep(2)

if __name__ == "__main__":
    main()