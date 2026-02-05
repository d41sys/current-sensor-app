#!/bin/bash
# Installation script for eth_sender service on Raspberry Pi
# Run this script on your Pi: sudo bash install.sh

set -e

echo "=========================================="
echo " Pico Data Relay - Installation Script"
echo "=========================================="

# Configuration
INSTALL_DIR="/home/pi/eth_sender"
SERVICE_NAME="eth_sender"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Please run as root: sudo bash install.sh"
    exit 1
fi

# Check if Pi user exists
if ! id "pi" &>/dev/null; then
    echo "⚠️  User 'pi' not found. Using current user: $SUDO_USER"
    PI_USER="${SUDO_USER:-$(whoami)}"
    INSTALL_DIR="/home/$PI_USER/eth_sender"
else
    PI_USER="pi"
fi

echo "📁 Creating installation directory: $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
mkdir -p "$INSTALL_DIR/logs"

# Copy files
echo "📋 Copying files..."
cp "$SCRIPT_DIR/eth_sender.py" "$INSTALL_DIR/" 2>/dev/null || cp "$SCRIPT_DIR/../eth_sender.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/manage.sh" "$INSTALL_DIR/" 2>/dev/null || true

# Set ownership
chown -R "$PI_USER:$PI_USER" "$INSTALL_DIR"
chmod +x "$INSTALL_DIR"/*.sh 2>/dev/null || true

# Install Python dependencies
echo "📦 Installing Python dependencies..."
apt-get update -qq
apt-get install -y python3-pip python3-serial

# Install pyserial if not available via apt
pip3 install pyserial --break-system-packages 2>/dev/null || pip3 install pyserial

# Enable serial port
echo "🔧 Configuring serial port..."
if ! grep -q "enable_uart=1" /boot/config.txt 2>/dev/null && ! grep -q "enable_uart=1" /boot/firmware/config.txt 2>/dev/null; then
    # Try both locations (older Pi OS vs newer)
    if [ -f /boot/firmware/config.txt ]; then
        echo "enable_uart=1" >> /boot/firmware/config.txt
    else
        echo "enable_uart=1" >> /boot/config.txt
    fi
    echo "⚠️  UART enabled. Reboot required!"
fi

# Disable serial console (if needed)
systemctl stop serial-getty@ttyAMA0.service 2>/dev/null || true
systemctl disable serial-getty@ttyAMA0.service 2>/dev/null || true

# Add user to dialout group for serial access
usermod -a -G dialout "$PI_USER"

# Install systemd service
echo "⚙️  Installing systemd service..."
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

cat > "$SERVICE_FILE" << EOF
[Unit]
Description=Pico Current Monitor Data Relay Service
After=network.target

[Service]
Type=simple
User=$PI_USER
WorkingDirectory=$INSTALL_DIR
ExecStart=/usr/bin/python3 $INSTALL_DIR/eth_sender.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

# Environment variables
Environment="PICO_SERIAL_PORT=/dev/serial0"
Environment="PICO_BAUDRATE=921600"
Environment="FORWARD_PORT=5000"
Environment="ENABLE_LOG=true"
Environment="LOG_DIR=$INSTALL_DIR/logs"
Environment="ROTATE_SECONDS=1800"

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and enable service
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"

echo ""
echo "=========================================="
echo " ✅ Installation Complete!"
echo "=========================================="
echo ""
echo "📍 Installation directory: $INSTALL_DIR"
echo "📍 Log directory: $INSTALL_DIR/logs"
echo ""
echo "🚀 Commands:"
echo "   Start:   sudo systemctl start $SERVICE_NAME"
echo "   Stop:    sudo systemctl stop $SERVICE_NAME"
echo "   Status:  sudo systemctl status $SERVICE_NAME"
echo "   Logs:    sudo journalctl -u $SERVICE_NAME -f"
echo ""
echo "📝 Or use the management script:"
echo "   cd $INSTALL_DIR && ./manage.sh status"
echo ""
echo "⚠️  If this is first time enabling UART, please reboot:"
echo "   sudo reboot"
echo ""
