#!/bin/bash
# Management script for eth_sender service
# Usage: ./manage.sh [start|stop|restart|status|logs|health]

SERVICE_NAME="eth_sender"
INSTALL_DIR="/home/pi/eth_sender"
LOG_DIR="$INSTALL_DIR/logs"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}=========================================="
    echo -e " Pico Data Relay - Management"
    echo -e "==========================================${NC}"
}

check_service_status() {
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        echo -e "${GREEN}●${NC} Service is ${GREEN}RUNNING${NC}"
        return 0
    else
        echo -e "${RED}●${NC} Service is ${RED}STOPPED${NC}"
        return 1
    fi
}

show_status() {
    print_header
    echo ""
    
    # Service status
    echo -e "${YELLOW}Service Status:${NC}"
    check_service_status
    echo ""
    
    # Detailed systemctl status
    systemctl status "$SERVICE_NAME" --no-pager -l 2>/dev/null | head -15
    echo ""
    
    # Network status
    echo -e "${YELLOW}Network Status:${NC}"
    PORT=$(grep -oP 'FORWARD_PORT=\K\d+' /etc/systemd/system/${SERVICE_NAME}.service 2>/dev/null || echo "5000")
    if netstat -tuln 2>/dev/null | grep -q ":$PORT "; then
        echo -e "  TCP Port $PORT: ${GREEN}LISTENING${NC}"
    elif ss -tuln 2>/dev/null | grep -q ":$PORT "; then
        echo -e "  TCP Port $PORT: ${GREEN}LISTENING${NC}"
    else
        echo -e "  TCP Port $PORT: ${RED}NOT LISTENING${NC}"
    fi
    
    # Check connected clients
    CLIENTS=$(ss -tn 2>/dev/null | grep ":$PORT " | wc -l)
    echo -e "  Connected clients: ${BLUE}$CLIENTS${NC}"
    echo ""
    
    # Serial port status
    echo -e "${YELLOW}Serial Port:${NC}"
    SERIAL_PORT=$(grep -oP 'PICO_SERIAL_PORT=\K[^\s"]+' /etc/systemd/system/${SERVICE_NAME}.service 2>/dev/null || echo "/dev/serial0")
    if [ -e "$SERIAL_PORT" ]; then
        echo -e "  $SERIAL_PORT: ${GREEN}EXISTS${NC}"
    else
        echo -e "  $SERIAL_PORT: ${RED}NOT FOUND${NC}"
    fi
    echo ""
    
    # Log files
    echo -e "${YELLOW}Recent Log Files:${NC}"
    if [ -d "$LOG_DIR" ]; then
        ls -lht "$LOG_DIR"/*.csv 2>/dev/null | head -5 || echo "  No CSV logs found"
    else
        echo "  Log directory not found"
    fi
    echo ""
    
    # Memory and CPU
    echo -e "${YELLOW}Resource Usage:${NC}"
    PID=$(systemctl show -p MainPID "$SERVICE_NAME" 2>/dev/null | cut -d= -f2)
    if [ "$PID" != "0" ] && [ -n "$PID" ]; then
        ps -p "$PID" -o pid,ppid,%cpu,%mem,etime,cmd --no-headers 2>/dev/null || echo "  Process info unavailable"
    else
        echo "  Service not running"
    fi
}

show_logs() {
    echo -e "${YELLOW}Live logs (Ctrl+C to exit):${NC}"
    sudo journalctl -u "$SERVICE_NAME" -f --no-pager
}

show_recent_logs() {
    echo -e "${YELLOW}Last 50 log lines:${NC}"
    sudo journalctl -u "$SERVICE_NAME" -n 50 --no-pager
}

health_check() {
    print_header
    echo ""
    echo -e "${YELLOW}Running Health Check...${NC}"
    echo ""
    
    ERRORS=0
    
    # Check 1: Service running
    echo -n "1. Service running: "
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        echo -e "${GREEN}OK${NC}"
    else
        echo -e "${RED}FAIL${NC}"
        ((ERRORS++))
    fi
    
    # Check 2: Serial port exists
    SERIAL_PORT=$(grep -oP 'PICO_SERIAL_PORT=\K[^\s"]+' /etc/systemd/system/${SERVICE_NAME}.service 2>/dev/null || echo "/dev/serial0")
    echo -n "2. Serial port ($SERIAL_PORT): "
    if [ -e "$SERIAL_PORT" ]; then
        echo -e "${GREEN}OK${NC}"
    else
        echo -e "${RED}FAIL${NC}"
        ((ERRORS++))
    fi
    
    # Check 3: TCP port listening
    PORT=$(grep -oP 'FORWARD_PORT=\K\d+' /etc/systemd/system/${SERVICE_NAME}.service 2>/dev/null || echo "5000")
    echo -n "3. TCP port $PORT listening: "
    if ss -tuln 2>/dev/null | grep -q ":$PORT "; then
        echo -e "${GREEN}OK${NC}"
    else
        echo -e "${RED}FAIL${NC}"
        ((ERRORS++))
    fi
    
    # Check 4: Log directory writable
    echo -n "4. Log directory writable: "
    if [ -w "$LOG_DIR" ]; then
        echo -e "${GREEN}OK${NC}"
    else
        echo -e "${YELLOW}WARN${NC} (not writable)"
    fi
    
    # Check 5: Recent data (check if log file modified in last 5 min)
    echo -n "5. Recent data activity: "
    RECENT_LOG=$(find "$LOG_DIR" -name "*.csv" -mmin -5 2>/dev/null | head -1)
    if [ -n "$RECENT_LOG" ]; then
        echo -e "${GREEN}OK${NC}"
    else
        echo -e "${YELLOW}WARN${NC} (no recent logs)"
    fi
    
    # Check 6: Disk space
    echo -n "6. Disk space: "
    DISK_USAGE=$(df "$LOG_DIR" 2>/dev/null | tail -1 | awk '{print $5}' | tr -d '%')
    if [ -n "$DISK_USAGE" ] && [ "$DISK_USAGE" -lt 90 ]; then
        echo -e "${GREEN}OK${NC} (${DISK_USAGE}% used)"
    else
        echo -e "${YELLOW}WARN${NC} (${DISK_USAGE}% used)"
    fi
    
    echo ""
    if [ $ERRORS -eq 0 ]; then
        echo -e "${GREEN}✅ All critical checks passed${NC}"
    else
        echo -e "${RED}❌ $ERRORS critical check(s) failed${NC}"
    fi
}

case "$1" in
    start)
        echo "Starting $SERVICE_NAME..."
        sudo systemctl start "$SERVICE_NAME"
        sleep 2
        check_service_status
        ;;
    stop)
        echo "Stopping $SERVICE_NAME..."
        sudo systemctl stop "$SERVICE_NAME"
        check_service_status
        ;;
    restart)
        echo "Restarting $SERVICE_NAME..."
        sudo systemctl restart "$SERVICE_NAME"
        sleep 2
        check_service_status
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    recent)
        show_recent_logs
        ;;
    health)
        health_check
        ;;
    enable)
        echo "Enabling $SERVICE_NAME to start on boot..."
        sudo systemctl enable "$SERVICE_NAME"
        echo -e "${GREEN}Done${NC}"
        ;;
    disable)
        echo "Disabling $SERVICE_NAME from starting on boot..."
        sudo systemctl disable "$SERVICE_NAME"
        echo -e "${GREEN}Done${NC}"
        ;;
    *)
        print_header
        echo ""
        echo "Usage: $0 {start|stop|restart|status|logs|recent|health|enable|disable}"
        echo ""
        echo "Commands:"
        echo "  start    - Start the service"
        echo "  stop     - Stop the service"
        echo "  restart  - Restart the service"
        echo "  status   - Show detailed status"
        echo "  logs     - Show live logs (follow mode)"
        echo "  recent   - Show last 50 log lines"
        echo "  health   - Run health check"
        echo "  enable   - Enable auto-start on boot"
        echo "  disable  - Disable auto-start on boot"
        echo ""
        exit 1
        ;;
esac
