# Electrochemical Current Monitoring System

A real-time 9-electrode current monitoring and data preprocessing application built with PySide6 and PyQt-Fluent-Widgets. Designed for electrochemical experiments, water electrolysis research, and multi-channel current sensor data acquisition.

## Features

### Real-time Monitoring
- **9-Electrode Current Monitoring**: Real-time visualization of 9 independent current channels with individual sensor cards
- **Voltage Monitoring**: Simultaneous bus voltage tracking
- **Dual View Modes**: Line chart for time-series analysis and 3×3 heatmap for spatial visualization
- **Connection Options**: Support for both Serial (USB) and Socket (TCP) connections
- **Configurable Window Length**: Adjustable monitoring window from 1-60 seconds
- **Average Mode**: Toggle between instant readings and 100-sample batch averaging for noise reduction
- **Gas Production Calculation**: Real-time H₂ and O₂ production estimation using Faraday's law
- **Data Export**: Export charts and heatmaps as high-resolution PNG images (3x scale)

### Data Preprocessing
- **Flexible Data Loading**: Load data from folder (9 CSV files) or single combined file (11 columns)
- **Signal Filtering**: Butterworth filters (low-pass, high-pass, bandpass) with configurable cutoff and order
- **Temporal Windowing**: Split data into overlapping time windows for segment-by-segment analysis
- **Multi-Tab Visualization**:
  - Current Signals (3×3 grid with raw + filtered overlay)
  - H₂ Production (cumulative line + bar chart)
  - O₂ Production (cumulative line + bar chart)
  - Heatmaps (H₂, O₂, Mean Current, Std)
  - Statistics (summary table + bar charts)
- **Data Export**: Export as single 11-column file or 9 separate segment files

### UI/UX
- **Fluent Design**: Modern Microsoft Fluent Design interface with PyQt-Fluent-Widgets
- **Tailwind CSS Colors**: Consistent color palette (600 shades) for electrode identification
- **Responsive Layout**: Adaptive grid layouts for different window sizes
- **Non-blocking Operations**: Smooth disconnect handling with status feedback

## Prerequisites

- **Python**: 3.8 or higher
- **Operating System**: Windows, macOS, or Linux
- **Hardware**: USB Serial device or network connection for real-time monitoring

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd team-assignment-current-meansurement
```

### 2. Create a Virtual Environment (Recommended)

#### On macOS/Linux:
```bash
python3 -m venv venv
source venv/bin/activate
```

#### On Windows:
```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

## Project Structure

```
team-assignment-current-meansurement/
├── app/                          # Main application package
│   ├── common/                   # Common utilities
│   │   ├── config.py            # Configuration management
│   │   ├── icon.py              # Icon definitions
│   │   ├── translator.py        # Translation utilities
│   │   └── usb_reader.py        # USB data reader utilities
│   ├── view/                     # UI views
│   │   ├── main_window.py       # Main application window
│   │   ├── monitoring.py        # Real-time monitoring interface
│   │   └── preprocessing.py     # Data preprocessing & visualization
│   ├── download/                 # Download resources
│   └── resource/                 # Application resources
│       └── images/              # Image assets
├── core/                         # Core framework components
│   ├── common/                   # Core utilities (animation, color, fonts, etc.)
│   ├── components/               # Reusable UI components
│   ├── window/                   # Window management
│   └── _rc/                      # Resource compilation
├── dataset/                      # Sample datasets
│   └── *.csv                    # Sample current measurement CSV files
├── test_data/                    # Test data files
├── flu_main.py                   # Main entry point
├── visualization.py              # Visualization & signal processing utilities
├── simulator.py                  # Data simulator for testing
├── requirements.txt              # Project dependencies
└── README.md                     # This file
```

## Usage

### Running the Application

```bash
python flu_main.py
```

### Data Simulator

For testing without physical hardware, use the simulator:

#### Socket Mode (Recommended for testing):
```bash
python simulator.py socket
# or with custom host/port
python simulator.py socket 0.0.0.0 5000
```

#### Serial Mode (requires socat on macOS/Linux):
```bash
# Terminal 1: Create virtual serial ports
socat -d -d pty,raw,echo=0,link=/tmp/pico_virtual pty,raw,echo=0,link=/tmp/pico_host

# Terminal 2: Run simulator
python simulator.py serial
```

### Data Format

The application expects data in the following format:

**Serial/Socket Input**: `timestamp,i1,i2,...,i9,vbus,cycle_us`
- `timestamp`: Microseconds since start
- `i1-i9`: 9 current readings in mA
- `vbus`: Bus voltage in V
- `cycle_us`: Cycle time in microseconds

**CSV File (11 columns)**: `timestamp,i1,i2,...,i9,voltage`
- First column: Time in seconds
- Columns 2-10: Current readings (A)
- Column 11: Voltage (V)

## Key Features Usage

### 1. Real-time Monitoring

1. Navigate to the **Monitoring** tab
2. Select connection mode: **Serial** or **Socket**
3. For Serial: Select port and baud rate (default: 115200)
4. For Socket: Enter host (e.g., `localhost`) and port (e.g., `5000`)
5. Click **Connect** to start data acquisition
6. Use **Pivot** tabs to switch between Line Chart and Heatmap views
7. Adjust **Window Length** (1-60 sec) to change the display window
8. Toggle **Average Mode** for smoothed heatmap display (averages 100 samples)
9. Export charts/heatmaps using the export buttons

### 2. Data Preprocessing

1. Navigate to the **Preprocessing** tab
2. Click **Load Data** and select:
   - **Load Folder**: 9 separate CSV files (one per electrode)
   - **Load File**: Single CSV with 11 columns
3. Preview loaded data in the Data Preview section
4. Configure **Window Settings**:
   - Window Length (auto-fills with data duration)
   - Overlap (for sliding window analysis)
5. Click **Calculate Windows** to create time windows
6. Select a window index and click **Open Visualization**
7. In the visualization popup:
   - Adjust filter settings (type, cutoff, order)
   - Click **Apply Filter** to update visualizations
   - Navigate tabs to view different analyses
   - Export data or charts as needed

## Configuration

### Application Settings

Edit `app/common/config.py` to configure:
- Serial port settings
- Default connection parameters
- UI preferences (theme, language, DPI scaling)

### Signal Processing

The `visualization.py` module provides:
- `load_signals_from_folder()`: Load 9 CSV files from a folder
- `get_temporal_windows()`: Create overlapping time windows
- `apply_filter_to_df()`: Apply Butterworth filters
- `compute_stats()`: Calculate mean and standard deviation
- `compute_h2_from_current()`: Estimate H₂ production via Faraday's law
- `compute_o2_from_current()`: Estimate O₂ production via Faraday's law

## Dependencies

### Core UI
- **PySide6**: Qt6 framework for Python
- **PySide6-Fluent-Widgets**: Microsoft Fluent Design components
- **PySideSix-Frameless-Window**: Frameless window support

### Data Processing
- **pandas**: Data manipulation and analysis
- **numpy**: Numerical computing
- **scipy**: Signal processing (Butterworth filters)

### Visualization
- **pyqtgraph**: High-performance real-time plotting
- **matplotlib**: Static plotting and export

### Hardware Interface
- **pyserial**: Serial port communication

### Utilities
- **Pillow**: Image processing
- **darkdetect**: System theme detection

## Troubleshooting

### USB Device Not Detected

- Verify the device is connected
- Check device permissions (Linux/macOS: add user to `dialout` group)
- Try the socket mode simulator for testing

### Socket Connection Failed

- Ensure the simulator is running first
- Check firewall settings
- Verify the host and port are correct

### Import Errors

```bash
pip install --upgrade -r requirements.txt
```

### Qt Platform Plugin Error (Linux)

```bash
sudo apt-get install libxcb-xinerama0 libxcb-cursor0
```

### Permission Denied on Serial Port

```bash
# Linux: Add user to dialout group
sudo usermod -a -G dialout $USER
# Log out and back in

# macOS: Change port permissions
sudo chmod 666 /dev/tty.usbserial*
```

## Development

### Running with Simulator

For full testing without hardware:

```bash
# Terminal 1: Start simulator
python simulator.py socket

# Terminal 2: Run application
python flu_main.py
# Connect using Socket mode to localhost:5000
```

### Running with connection from Electrolyze

For full testing with hardware (Make sure the ethernet cable is connected and configured that adaapter on your PC/Laptop - IPv4 Address to `192.168.50.1`):

```bash
# Step 1: Connect to the PI 5 using ssh
ssh engdpi@192.168.50.2 -y
# then password is 12341234

# Step 2: Go to the right folder
cd /coding/current-sensor-app/

# Step 3: Run the sender python script
python3 eth_sender.py

# Step 4: Run application from executable file or python file
# You can download the executable file from release tag on GitHub
# If you want to run the python file
python flu_main.py
```

### Copy log files from PI 5 to PC/Laptop

```bash
# Step 1: Copy pico_logs folder to this current path
scp -r engdpi@192.168.50.2:~/pico_logs .
# then password is 12341234
```

### Code Style

- Follow PEP 8 guidelines
- Use type hints where applicable
- Document complex functions with docstrings

## Production Deployment

### Building Executables

#### Using the Build Script (Recommended)

```bash
# Build for current platform
python build.py

# Build with debug console (for troubleshooting)
python build.py --debug

# Build and create release package (ZIP/DMG)
python build.py --package

# Clean build artifacts
python build.py --clean
```

#### Platform-Specific Scripts

**macOS:**
```bash
./build_macos.sh
```
Output: `dist/CurrentMonitor.app`

**Note for macOS**: After building, you may need to remove the quarantine attribute:
```bash
xattr -cr dist/CurrentMonitor.app
```

**Windows:**
```batch
build_windows.bat
```
Output: `dist\CurrentMonitor\CurrentMonitor.exe` and `dist\CurrentMonitor-Windows.zip`

### GitHub Actions CI/CD

The project includes a GitHub Actions workflow for automated builds:

1. **Push a tag** to trigger a release build:
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```

2. **Artifacts produced**:
   - Windows: `CurrentMonitor-Windows.zip`
   - macOS: `CurrentMonitor-macOS.zip`

3. **Manual trigger**: Go to Actions → Build and Release → Run workflow

## License

This project is developed for the Team Assignment course at TU/e with VDL.

---

**Note**: This project is designed for electrochemical research and current monitoring applications. The 9-electrode configuration is optimized for 3×3 electrode array experiments.
