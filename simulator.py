#!/usr/bin/env python3
"""
Simulate Pico sending voltage and current data over virtual serial port
Run this in another terminal while main.py is running
"""
import serial
import time
import random
import sys

PORT = '/tmp/pico_host'  # Pair to /tmp/pico_virtual used by main.py
BAUDRATE = 115200

def main():
    try:
        print(f"Opening {PORT} at {BAUDRATE} baud...")
        ser = serial.Serial(PORT, BAUDRATE, timeout=1)
        print("Connected! Sending simulated data...\n")
        
        try:
            while True:
                # Simulate realistic voltage and current readings
                voltage = 12.5 + random.uniform(-0.5, 0.5)
                current = 3.2 + random.uniform(-0.2, 0.2)
                
                # Send in Pico format (voltage,current)
                data = f"{voltage:.2f},{current:.2f}\n"
                ser.write(data.encode())
                
                print(f"Sent: {data.strip()}")
                time.sleep(0.01)  # Send every 1 second
                
        except KeyboardInterrupt:
            print("\nStopped by user")
        finally:
            ser.close()
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()