# Raspberry Pi Deployment for eth_sender

This folder contains scripts to deploy and manage the `eth_sender.py` data relay service on Raspberry Pi 5.

## Quick Start

### 1. Copy files to Pi

```bash
# From your development machine
scp -r pi_deploy/* pi@<PI_IP>:~/

# Or use rsync
rsync -avz pi_deploy/ pi@<PI_IP>:~/pi_deploy/
```

### 2. Run installation

```bash
# SSH into your Pi
ssh pi@<PI_IP>

# Run installer
cd ~/pi_deploy
sudo bash install.sh
```

### 3. Reboot (first time only)

```bash
sudo reboot
```

### 4. Start the service

```bash
sudo systemctl start eth_sender
```

## Management Commands

### Using systemctl (standard)

```bash
# Start service
sudo systemctl start eth_sender

# Stop service
sudo systemctl stop eth_sender

# Restart service
sudo systemctl restart eth_sender

# Check status
sudo systemctl status eth_sender

# View logs
sudo journalctl -u eth_sender -f

# Enable auto-start on boot
sudo systemctl enable eth_sender

# Disable auto-start
sudo systemctl disable eth_sender
```

### Using manage.sh (convenient)

```bash
cd /home/pi/eth_sender

./manage.sh status    # Detailed status with network info
./manage.sh start     # Start service
./manage.sh stop      # Stop service
./manage.sh restart   # Restart service
./manage.sh logs      # Live log view
./manage.sh recent    # Last 50 log lines
./manage.sh health    # Run health check
./manage.sh enable    # Enable auto-start
./manage.sh disable   # Disable auto-start
```

## Configuration

Edit the service file to change settings:

```bash
sudo nano /etc/systemd/system/eth_sender.service
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PICO_SERIAL_PORT` | `/dev/serial0` | Serial port for Pico |
| `PICO_BAUDRATE` | `921600` | Serial baud rate |
| `FORWARD_PORT` | `5000` | TCP port for clients |
| `ENABLE_LOG` | `true` | Enable CSV logging |
| `LOG_DIR` | `/home/pi/eth_sender/logs` | Log directory |
| `ROTATE_SECONDS` | `1800` | Log rotation (30 min) |

After editing, reload and restart:

```bash
sudo systemctl daemon-reload
sudo systemctl restart eth_sender
```

## Connecting from Desktop App

1. Start the service on Pi
2. Note the Pi's IP address: `hostname -I`
3. In CurrentMonitor app:
   - Select **Socket** connection mode
   - Enter Pi's IP (e.g., `192.168.1.100`)
   - Port: `5000`
   - Click **Connect**

## Troubleshooting

### Service won't start

```bash
# Check logs
sudo journalctl -u eth_sender -n 100

# Check serial port
ls -la /dev/serial0
ls -la /dev/ttyAMA0

# Verify UART is enabled
cat /boot/firmware/config.txt | grep uart
```

### No data received

```bash
# Check if port is listening
ss -tuln | grep 5000

# Test serial connection manually
python3 -c "import serial; s=serial.Serial('/dev/serial0', 921600); print(s.readline())"
```

### Permission denied

```bash
# Add user to dialout group
sudo usermod -a -G dialout pi
# Log out and back in
```

## Uninstall

```bash
sudo systemctl stop eth_sender
sudo systemctl disable eth_sender
sudo rm /etc/systemd/system/eth_sender.service
sudo systemctl daemon-reload
rm -rf /home/pi/eth_sender
```
