#!/usr/bin/env python3
"""
Simulate Pico sending voltage and current data for testing the monitoring interface.

Expected format: timestamp,i1,i2,...,i9,vbus,cycle_us
Total: 12 values (timestamp + 9 currents in mA + voltage in V + cycle_us)

Usage:
  Serial mode (requires socat):
    Terminal 1: socat -d -d pty,raw,echo=0,link=/tmp/pico_virtual pty,raw,echo=0,link=/tmp/pico_host
    Terminal 2: python simulator.py serial
    
  Socket mode (for Windows/network testing):
    python simulator.py socket [host] [port]
    python simulator.py socket 0.0.0.0 5000
"""
import time
import random
import sys
import math
import socket
import threading

DEFAULT_SERIAL_PORT = '/tmp/pico_host'
DEFAULT_SOCKET_HOST = '0.0.0.0'
DEFAULT_SOCKET_PORT = 5000
BAUDRATE = 115200


def generate_data_line(sample_count, start_time):
    """Generate a single line of simulated sensor data"""
    elapsed_us = int((time.time() - start_time) * 1_000_000)
    
    # Base currents for each of 9 electrodes (in mA)
    base_currents = [50.0, 55.0, 48.0, 52.0, 47.0, 53.0, 49.0, 51.0, 46.0]
    
    # Simulate 9 current readings (in mA) with sine wave variation + noise
    currents = []
    for i, base in enumerate(base_currents):
        phase = sample_count * 0.05 + i * 0.5
        variation = math.sin(phase) * 10  # ±10 mA sine wave
        noise = random.uniform(-2, 2)  # ±2 mA noise
        current_ma = base + variation + noise
        currents.append(f"{current_ma:.2f}")
    
    # Simulate voltage in V (monitoring expects V, not mV)
    voltage_v = 12.0 + random.uniform(-0.1, 0.1)
    
    # Cycle time in microseconds (around 10ms = 10000us)
    cycle_us = 10000 + random.randint(-100, 100)
    
    # Format: timestamp,i1,i2,...,i9,vbus,cycle_us
    return f"{elapsed_us},{','.join(currents)},{voltage_v:.3f},{cycle_us}\n"


def run_serial_mode(port=DEFAULT_SERIAL_PORT):
    """Run simulator in serial mode using virtual serial port"""
    try:
        import serial
    except ImportError:
        print("Error: pyserial not installed. Run: pip install pyserial")
        sys.exit(1)
    
    print(f"=== Serial Mode ===")
    print(f"Make sure to run socat first:")
    print(f"  socat -d -d pty,raw,echo=0,link=/tmp/pico_virtual pty,raw,echo=0,link=/tmp/pico_host")
    print()
    
    try:
        print(f"Opening {port} at {BAUDRATE} baud...")
        ser = serial.Serial(port, BAUDRATE, timeout=1)
        print("Connected! Sending simulated data...\n")
        
        start_time = time.time()
        sample_count = 0
        
        try:
            while True:
                data = generate_data_line(sample_count, start_time)
                ser.write(data.encode())
                
                sample_count += 1
                if sample_count % 100 == 0:
                    parts = data.strip().split(',')
                    avg_i = sum(float(parts[i]) for i in range(1, 10)) / 9
                    print(f"Sent {sample_count} samples | avg_i={avg_i:.1f}mA, V={parts[10]}V")
                
                time.sleep(0.01)  # 100 Hz
                
        except KeyboardInterrupt:
            print(f"\nStopped. Total samples sent: {sample_count}")
        finally:
            ser.close()
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def handle_socket_client(client_socket, client_address):
    """Handle a single socket client connection"""
    print(f"Client connected: {client_address}")
    
    start_time = time.time()
    sample_count = 0
    
    try:
        while True:
            data = generate_data_line(sample_count, start_time)
            client_socket.sendall(data.encode())
            
            sample_count += 1
            if sample_count % 100 == 0:
                parts = data.strip().split(',')
                avg_i = sum(float(parts[i]) for i in range(1, 10)) / 9
                print(f"[{client_address}] Sent {sample_count} samples | avg_i={avg_i:.1f}mA, V={parts[10]}V")
            
            time.sleep(0.01)  # 100 Hz
            
    except (BrokenPipeError, ConnectionResetError):
        print(f"Client disconnected: {client_address}")
    except Exception as e:
        print(f"Error with client {client_address}: {e}")
    finally:
        client_socket.close()


def run_socket_mode(host=DEFAULT_SOCKET_HOST, port=DEFAULT_SOCKET_PORT):
    """Run simulator as a socket server"""
    print(f"=== Socket Mode ===")
    print(f"Starting server on {host}:{port}")
    print(f"Connect with monitoring app using Socket mode, Host: {host}, Port: {port}")
    print()
    
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server_socket.bind((host, port))
        server_socket.listen(5)
        print(f"Listening on {host}:{port}...")
        print("Press Ctrl+C to stop\n")
        
        while True:
            client_socket, client_address = server_socket.accept()
            client_thread = threading.Thread(
                target=handle_socket_client,
                args=(client_socket, client_address),
                daemon=True
            )
            client_thread.start()
            
    except KeyboardInterrupt:
        print("\nServer stopped.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        server_socket.close()


def print_usage():
    print("Usage:")
    print("  python simulator.py serial [port]")
    print("  python simulator.py socket [host] [port]")
    print()
    print("Examples:")
    print("  python simulator.py serial                    # Use /tmp/pico_host")
    print("  python simulator.py serial /dev/ttyUSB0       # Use specific port")
    print("  python simulator.py socket                    # Listen on 0.0.0.0:5000")
    print("  python simulator.py socket 127.0.0.1 5000     # Listen on localhost:5000")


def main():
    if len(sys.argv) < 2:
        print_usage()
        print()
        # Default to socket mode for easier testing
        print("No mode specified, defaulting to socket mode...")
        run_socket_mode()
        return
    
    mode = sys.argv[1].lower()
    
    if mode == 'serial':
        port = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_SERIAL_PORT
        run_serial_mode(port)
    elif mode == 'socket':
        host = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_SOCKET_HOST
        port = int(sys.argv[3]) if len(sys.argv) > 3 else DEFAULT_SOCKET_PORT
        run_socket_mode(host, port)
    else:
        print(f"Unknown mode: {mode}")
        print_usage()
        sys.exit(1)


if __name__ == '__main__':
    main()