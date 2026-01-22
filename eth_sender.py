#!/usr/bin/env python3
import os
import csv
import time
import socket
import threading
from datetime import datetime, timezone
 
import serial
 
# ---- Config ----
SERIAL_PORT = os.environ.get("PICO_SERIAL_PORT", "/dev/serial0")
BAUDRATE = int(os.environ.get("PICO_BAUDRATE", "921600"))
 
TCP_HOST = "0.0.0.0"
TCP_PORT = int(os.environ.get("FORWARD_PORT", "5000"))
 
LOG_DIR = os.environ.get("LOG_DIR", "/home/engdpi/pico_logs")
ROTATE_SECONDS = int(os.environ.get("ROTATE_SECONDS", str(30 * 60)))
 
# Turn these on only if you need them:
ENABLE_PARSE = False
ENABLE_LOG   = False
 
EXPECTED_FIELDS = 12
CHECKSUM_THRESHOLD = 10000
 
# ---- TCP client management ----
clients = set()
clients_lock = threading.Lock()
 
def tcp_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((TCP_HOST, TCP_PORT))
        srv.listen(5)
        while True:
            conn, addr = srv.accept()
            conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            with clients_lock:
                clients.add(conn)
 
def broadcast(line: bytes):
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
        name = dt.strftime("pico_%Y%m%d_%H%M%S_UTC.csv")
        self.current_path = os.path.join(self.log_dir, name)
 
        is_new = not os.path.exists(self.current_path)
        self.current_file = open(self.current_path, "a", newline="")
        self.csv_writer = csv.writer(self.current_file)
 
        if is_new:
            header = ["t_us"] + [f"i{i}_mA" for i in range(1, 10)] + ["vbus_mV", "cycle_us"]
            self.csv_writer.writerow(header)
            self.current_file.flush()
 
    def write_row(self, row: list):
        now = time.time()
        if (self.current_file is None) or (self._period_floor(now) != self.period_start):
            self._open_new_file(now)
        self.csv_writer.writerow(row)
        # Don't flush every line; flush periodically from main loop.
 
def parse_pico_line(line_str: str):
    parts = [p.strip() for p in line_str.split(",")]
    if len(parts) != EXPECTED_FIELDS:
        return None, None, False
    try:
        t_us = parts[0]
        # i1..i9 in mA ints, vbus_mV int, cycle_us int
        checksum = int(parts[-1])
        print("CHECK: {checksum} at {t_us}")
        if checksum > CHECKSUM_THRESHOLD:
            # Avoid printing in hot path if you're chasing latency
            print("WARNING: {checksum} at {t_us}")
            pass
        return parts, checksum, True
    except Exception:
        return None, None, False
 
def main():
    threading.Thread(target=tcp_server, daemon=True).start()
    logger = RotatingCSVLogger(LOG_DIR, ROTATE_SECONDS) if ENABLE_LOG else None
 
    while True:
        try:
            with serial.Serial(
                SERIAL_PORT,
                BAUDRATE,
                timeout=0,          # non-blocking
                rtscts=False,
                dsrdtr=False,
                write_timeout=0
            ) as ser:
                # Increase RX buffer if supported
                try:
                    ser.set_buffer_size(rx_size=262144, tx_size=8192)
                except Exception:
                    pass
 
                buf = bytearray()
                last_flush = time.time()
 
                while True:
                    n = ser.in_waiting
                    chunk = ser.read(n if n else 4096)
                    if not chunk:
                        time.sleep(0.0005)
                        continue
 
                    buf.extend(chunk)
 
                    # Split into complete lines
                    while True:
                        nl = buf.find(b"\n")
                        if nl < 0:
                            break
                        line = buf[:nl+1]
                        del buf[:nl+1]
 
                        # FAST PATH: forward raw line to clients
                        broadcast(line)
 
                        if ENABLE_PARSE or ENABLE_LOG:
                            s = line.decode("utf-8", errors="replace").strip()
                            if not s:
                                continue
                            parts, checksum, ok = parse_pico_line(s)
                            if ok and ENABLE_LOG:
                                logger.write_row(parts)
 
                    # Periodic flush (if logging)
                    if ENABLE_LOG and logger and (time.time() - last_flush) > 1.0:
                        try:
                            logger.current_file.flush()
                        except Exception:
                            pass
                        last_flush = time.time()
 
        except serial.SerialException as e:
            print(f"[SER] Serial error: {e}. Reconnecting in 1s...")
            time.sleep(1)
        except Exception as e:
            print(f"[ERR] {e}. Continuing in 1s...")
            time.sleep(1)
 
if __name__ == "__main__":
    main()
