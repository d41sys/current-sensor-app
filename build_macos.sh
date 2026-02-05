#!/bin/bash
# Build script for macOS
# Usage: ./build_macos.sh

set -e

echo "=========================================="
echo "Building Current Monitor for macOS"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo -e "${RED}Error: This script must be run on macOS${NC}"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
echo -e "${YELLOW}Python version: $PYTHON_VERSION${NC}"

# Create virtual environment if it doesn't exist
# if [ ! -d "venv_build" ]; then
#     echo -e "${YELLOW}Creating virtual environment...${NC}"
#     python3 -m venv venv_build
# fi

# Activate virtual environment
source /Users/d41sy/coding/team-assignment-current-meansurement/PyQt-Fluent-Widgets/teas/bin/activate

# Upgrade pip
echo -e "${YELLOW}Upgrading pip...${NC}"
pip install --upgrade pip

# Install dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
pip install -r requirements.txt
pip install pyinstaller

# Clean previous builds
echo -e "${YELLOW}Cleaning previous builds...${NC}"
rm -rf build dist

# Create app icons directory if not exists
mkdir -p app/resource/images

# Create a simple icon if not exists (placeholder)
if [ ! -f "app/resource/images/logo.icns" ]; then
    echo -e "${YELLOW}Warning: logo.icns not found, building without custom icon${NC}"
fi

# Build with PyInstaller
echo -e "${YELLOW}Building application...${NC}"
pyinstaller CurrentMonitor.spec --clean --noconfirm

# Check if build succeeded
if [ -d "dist/CurrentMonitor.app" ]; then
    echo -e "${GREEN}=========================================="
    echo "Build successful!"
    echo "Application: dist/CurrentMonitor.app"
    echo "==========================================${NC}"
    
    # Create DMG (optional)
    if command -v create-dmg &> /dev/null; then
        echo -e "${YELLOW}Creating DMG installer...${NC}"
        create-dmg \
            --volname "Current Monitor" \
            --window-pos 200 120 \
            --window-size 600 400 \
            --icon-size 100 \
            --icon "CurrentMonitor.app" 175 120 \
            --hide-extension "CurrentMonitor.app" \
            --app-drop-link 425 120 \
            "dist/CurrentMonitor-macOS.dmg" \
            "dist/CurrentMonitor.app"
        echo -e "${GREEN}DMG created: dist/CurrentMonitor-macOS.dmg${NC}"
    else
        echo -e "${YELLOW}Tip: Install create-dmg for DMG creation: brew install create-dmg${NC}"
    fi
else
    echo -e "${RED}Build failed! Check the output above for errors.${NC}"
    exit 1
fi

# Deactivate virtual environment
deactivate

echo -e "${GREEN}Done!${NC}"
