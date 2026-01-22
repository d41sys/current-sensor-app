import serial

ser = serial.Serial("/dev/serial0", 115200, timeout=1)

while True:
    line = ser.readline().decode(errors="ignore").strip()
    if line:
        print("PICO:", line)