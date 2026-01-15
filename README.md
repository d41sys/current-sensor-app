# Current Sensor Application

A real-time USB data monitoring and preprocessing application built with PySide6 and PyQt-Fluent-Widgets, designed for current sensor data acquisition, visualization, and analysis.

## Features

- **Real-time USB Data Monitoring**: Capture and visualize voltage and current data from USB devices
- **Data Preprocessing**: Advanced signal processing with filtering, windowing, and statistical analysis
- **Interactive Visualization**: Dynamic plots using PyQtGraph and Matplotlib
- **Fluent Design UI**: Modern, user-friendly interface with PyQt-Fluent-Widgets
- **Data Export**: Save processed data with timestamps for further analysis
- **H₂ and O₂ Computation**: Calculate hydrogen and oxygen from current measurements

## Prerequisites

- **Python**: 3.8 or higher
- **Operating System**: Windows, macOS, or Linux
- **USB Serial Device**: For real-time data acquisition (optional for simulation mode)

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
│   │   └── usb_reader.py        # USB data reader
│   └── view/                     # UI views
│       ├── main_window.py       # Main application window
│       ├── monitoring.py        # Real-time monitoring interface
│       └── preprocessing.py     # Data preprocessing interface
├── core/                         # Core framework components
│   ├── common/                   # Core utilities
│   ├── components/               # UI components
│   └── window/                   # Window management
├── flu_main.py                   # Main entry point (Fluent UI)
├── main.py                       # Alternative entry point
├── visualization.py              # Visualization utilities
├── simulator.py                  # USB data simulator
├── test.py                       # Testing utilities
├── requirements.txt              # Project dependencies
└── README.md                     # This file
```

## Usage

### Running the Application

#### Main Application (Recommended):
```bash
python flu_main.py
```

#### Alternative Entry Point:
```bash
python main.py
```

### USB Data Simulator

For testing without a physical USB device:

```bash
python simulator.py
```

This will simulate a USB serial device on a virtual port.

### Key Features Usage

#### 1. Real-time Monitoring
- Navigate to the "Monitoring" tab
- Select your USB device from the dropdown
- Click "Start" to begin data acquisition
- View real-time voltage and current plots

#### 2. Data Preprocessing
- Navigate to the "Preprocessing" tab
- Load saved signal data from a folder
- Apply filters (Butterworth, etc.)
- Configure temporal windows
- Compute statistics and export results

## Configuration

### USB Device Settings

Edit [app/common/config.py](app/common/config.py) to configure:
- Serial port settings (baud rate, timeout)
- Data acquisition parameters
- UI preferences (theme, language)

### Visualization Settings

Edit [visualization.py](visualization.py) to adjust:
- Filter parameters
- Plot styles
- Statistical computations

## Dependencies

### Core Dependencies
- **PySide6**: Qt framework for Python
- **PyQt-Fluent-Widgets**: Modern Fluent Design widgets

### Data Processing
- **pandas**: Data manipulation and analysis
- **numpy**: Numerical computing
- **scipy**: Scientific computing (signal processing)

### Visualization
- **matplotlib**: Static plotting
- **pyqtgraph**: Real-time plotting

### Hardware Interface
- **pyserial**: Serial port communication

### Additional
- **Pillow**: Image processing
- **colorthief**: Color palette extraction
- **darkdetect**: System theme detection

## Troubleshooting

### Issue: USB Device Not Detected

**Solution:**
- Verify the device is connected
- Check device permissions (especially on Linux/macOS)
- Try running with elevated privileges
- Use the simulator for testing

### Issue: Import Errors

**Solution:**
```bash
pip install --upgrade -r requirements.txt
```

### Issue: Qt Platform Plugin Error

**Solution (Linux):**
```bash
sudo apt-get install libxcb-xinerama0
```

**Solution (macOS):**
```bash
pip uninstall PySide6
pip install PySide6
```

### Issue: Permission Denied on Serial Port (Linux/macOS)

**Solution:**
```bash
# Add user to dialout group (Linux)
sudo usermod -a -G dialout $USER

# Change port permissions (macOS)
sudo chmod 666 /dev/tty.usbserial*
```

## Development

### Running Tests

```bash
python test.py
```

### Building UI Forms

If you modify `.ui` files:

```bash
pyside6-uic form.ui -o ui_form.py
```

### Code Style

- Follow PEP 8 guidelines
- Use type hints where applicable
- Document complex functions

## License

[Add your license information here]

## Contributors

[Add contributor information here]

## Support

For issues, questions, or contributions, please [open an issue](https://github.com/your-repo/issues) or contact the development team.

## Changelog

### Version 1.0.0
- Initial release
- Real-time USB data monitoring
- Data preprocessing and visualization
- Fluent UI design

---

**Note**: This project is under active development. Features and documentation may change.
