#!/usr/bin/env python3
"""
Cross-platform build script for Current Monitor Application
Supports building for Windows and macOS using PyInstaller

Usage:
    python build.py                 # Build for current platform
    python build.py --clean         # Clean build artifacts
    python build.py --debug         # Build with console window for debugging
"""

import os
import sys
import shutil
import subprocess
import platform
import argparse
from pathlib import Path

# Application metadata
APP_NAME = "CurrentMonitor"
APP_VERSION = "1.0.0"
MAIN_SCRIPT = "flu_main.py"

# Directories
ROOT_DIR = Path(__file__).parent.absolute()
BUILD_DIR = ROOT_DIR / "build"
DIST_DIR = ROOT_DIR / "dist"
VENV_DIR = ROOT_DIR / "venv_build"


def print_header(text: str):
    """Print a formatted header"""
    print("\n" + "=" * 50)
    print(f" {text}")
    print("=" * 50)


def print_success(text: str):
    """Print success message"""
    print(f"✅ {text}")


def print_error(text: str):
    """Print error message"""
    print(f"❌ {text}")


def print_info(text: str):
    """Print info message"""
    print(f"ℹ️  {text}")


def clean_build():
    """Remove build artifacts"""
    print_header("Cleaning build artifacts")
    
    dirs_to_clean = [BUILD_DIR, DIST_DIR]
    for dir_path in dirs_to_clean:
        if dir_path.exists():
            print_info(f"Removing {dir_path}")
            shutil.rmtree(dir_path)
    
    # Clean __pycache__ directories
    for pycache in ROOT_DIR.rglob("__pycache__"):
        if pycache.is_dir():
            shutil.rmtree(pycache)
    
    # Clean .pyc files
    for pyc in ROOT_DIR.rglob("*.pyc"):
        pyc.unlink()
    
    print_success("Build artifacts cleaned")


def check_dependencies():
    """Check if required dependencies are installed"""
    print_header("Checking dependencies")
    
    try:
        import PyInstaller
        print_success(f"PyInstaller {PyInstaller.__version__} found")
    except ImportError:
        print_info("Installing PyInstaller...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
    
    try:
        import PySide6
        print_success(f"PySide6 {PySide6.__version__} found")
    except ImportError:
        print_error("PySide6 not found. Please install requirements: pip install -r requirements.txt")
        sys.exit(1)
    
    try:
        import qfluentwidgets
        print_success("qfluentwidgets found")
    except ImportError:
        print_error("qfluentwidgets not found. Please install requirements: pip install -r requirements.txt")
        sys.exit(1)


def get_hidden_imports():
    """Get list of hidden imports for PyInstaller"""
    return [
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'PySide6.QtSvg',
        'PySide6.QtSvgWidgets',
        'qfluentwidgets',
        'qfluentwidgets.common',
        'qfluentwidgets.components',
        'qfluentwidgets.window',
        'qfluentwidgets._rc',
        'pyqtgraph',
        'pyqtgraph.exporters',
        'numpy',
        'pandas',
        'scipy',
        'scipy.signal',
        'scipy.ndimage',
        'PIL',
        'serial',
        'darkdetect',
    ]


def get_data_files():
    """Get list of data files to include"""
    data_files = []
    
    # Add app directory
    if (ROOT_DIR / "app").exists():
        data_files.append(("app", "app"))
    
    # Add core directory
    if (ROOT_DIR / "core").exists():
        data_files.append(("core", "core"))
    
    # Add visualization.py
    if (ROOT_DIR / "visualization.py").exists():
        data_files.append(("visualization.py", "."))
    
    return data_files


def build_application(debug: bool = False):
    """Build the application using PyInstaller"""
    print_header(f"Building {APP_NAME} for {platform.system()}")
    
    check_dependencies()
    
    # Determine icon file
    icon_file = None
    if platform.system() == "Windows":
        icon_path = ROOT_DIR / "app" / "resource" / "images" / "logo.ico"
        if icon_path.exists():
            icon_file = str(icon_path)
    elif platform.system() == "Darwin":
        icon_path = ROOT_DIR / "app" / "resource" / "images" / "logo.icns"
        if icon_path.exists():
            icon_file = str(icon_path)
    
    # Build PyInstaller command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", APP_NAME,
        "--clean",
        "--noconfirm",
    ]
    
    # Add windowed mode (no console) unless debug
    if not debug:
        cmd.append("--windowed")
    else:
        cmd.append("--console")
    
    # Add icon if available
    if icon_file:
        cmd.extend(["--icon", icon_file])
    
    # Add hidden imports
    for hidden_import in get_hidden_imports():
        cmd.extend(["--hidden-import", hidden_import])
    
    # Add data files
    for src, dst in get_data_files():
        cmd.extend(["--add-data", f"{src}{os.pathsep}{dst}"])
    
    # Collect qfluentwidgets data
    cmd.extend(["--collect-data", "qfluentwidgets"])
    cmd.extend(["--collect-submodules", "qfluentwidgets"])
    
    # Exclude unnecessary modules
    for exclude in ["tkinter", "matplotlib", "PyQt5", "PyQt6"]:
        cmd.extend(["--exclude-module", exclude])
    
    # Add main script
    cmd.append(MAIN_SCRIPT)
    
    print_info(f"Running: {' '.join(cmd)}")
    
    # Run PyInstaller
    result = subprocess.run(cmd, cwd=ROOT_DIR)
    
    if result.returncode != 0:
        print_error("Build failed!")
        sys.exit(1)
    
    # macOS: Create .app bundle info
    if platform.system() == "Darwin":
        app_path = DIST_DIR / f"{APP_NAME}.app"
        if app_path.exists():
            print_success(f"macOS app bundle created: {app_path}")
    
    # Windows: Create info
    if platform.system() == "Windows":
        exe_path = DIST_DIR / APP_NAME / f"{APP_NAME}.exe"
        if exe_path.exists():
            print_success(f"Windows executable created: {exe_path}")
    
    print_header("Build complete!")
    print_info(f"Output directory: {DIST_DIR}")


def create_release_package():
    """Create a release package (ZIP or DMG)"""
    print_header("Creating release package")
    
    if platform.system() == "Windows":
        # Create ZIP archive
        import zipfile
        zip_path = DIST_DIR / f"{APP_NAME}-{APP_VERSION}-Windows.zip"
        app_dir = DIST_DIR / APP_NAME
        
        if app_dir.exists():
            print_info(f"Creating {zip_path}")
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file in app_dir.rglob("*"):
                    if file.is_file():
                        arcname = file.relative_to(app_dir)
                        zipf.write(file, arcname)
            print_success(f"ZIP created: {zip_path}")
    
    elif platform.system() == "Darwin":
        # Check if create-dmg is available
        if shutil.which("create-dmg"):
            dmg_path = DIST_DIR / f"{APP_NAME}-{APP_VERSION}-macOS.dmg"
            app_path = DIST_DIR / f"{APP_NAME}.app"
            
            if app_path.exists():
                print_info(f"Creating {dmg_path}")
                subprocess.run([
                    "create-dmg",
                    "--volname", APP_NAME,
                    "--window-size", "600", "400",
                    "--icon-size", "100",
                    "--app-drop-link", "425", "120",
                    str(dmg_path),
                    str(app_path)
                ], check=True)
                print_success(f"DMG created: {dmg_path}")
        else:
            print_info("Tip: Install create-dmg for DMG creation: brew install create-dmg")
            # Fallback to ZIP
            import zipfile
            zip_path = DIST_DIR / f"{APP_NAME}-{APP_VERSION}-macOS.zip"
            app_path = DIST_DIR / f"{APP_NAME}.app"
            
            if app_path.exists():
                print_info(f"Creating {zip_path}")
                shutil.make_archive(
                    str(zip_path).replace('.zip', ''),
                    'zip',
                    DIST_DIR,
                    f"{APP_NAME}.app"
                )
                print_success(f"ZIP created: {zip_path}")


def main():
    parser = argparse.ArgumentParser(description=f"Build {APP_NAME} application")
    parser.add_argument("--clean", action="store_true", help="Clean build artifacts")
    parser.add_argument("--debug", action="store_true", help="Build with console for debugging")
    parser.add_argument("--package", action="store_true", help="Create release package after build")
    
    args = parser.parse_args()
    
    if args.clean:
        clean_build()
        return
    
    build_application(debug=args.debug)
    
    if args.package:
        create_release_package()


if __name__ == "__main__":
    main()
