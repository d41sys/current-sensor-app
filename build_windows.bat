@echo off
REM Build script for Windows
REM Usage: build_windows.bat

echo ==========================================
echo Building Current Monitor for Windows
echo ==========================================

REM Check Python installation
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python is not installed or not in PATH
    exit /b 1
)

REM Create virtual environment if it doesn't exist
if not exist "venv_build" (
    echo Creating virtual environment...
    python -m venv venv_build
)

REM Activate virtual environment
call venv_build\Scripts\activate.bat

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt
pip install pyinstaller

REM Clean previous builds
echo Cleaning previous builds...
if exist "build" rmdir /s /q build
if exist "dist" rmdir /s /q dist

REM Create app icons directory if not exists
if not exist "app\resource\images" mkdir app\resource\images

REM Build with PyInstaller
echo Building application...
pyinstaller CurrentMonitor.spec --clean --noconfirm

REM Check if build succeeded
if exist "dist\CurrentMonitor\CurrentMonitor.exe" (
    echo ==========================================
    echo Build successful!
    echo Application: dist\CurrentMonitor\CurrentMonitor.exe
    echo ==========================================
    
    REM Create zip archive
    echo Creating ZIP archive...
    powershell -Command "Compress-Archive -Path 'dist\CurrentMonitor\*' -DestinationPath 'dist\CurrentMonitor-Windows.zip' -Force"
    echo ZIP created: dist\CurrentMonitor-Windows.zip
) else (
    echo Build failed! Check the output above for errors.
    exit /b 1
)

REM Deactivate virtual environment
call deactivate

echo Done!
pause
