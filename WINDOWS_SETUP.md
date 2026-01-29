# Windows Setup Guide

This guide provides detailed instructions for setting up the OPREL Laser Measurement Suite on Windows.

## Prerequisites

1. **Windows 10 or later** (Windows 11 recommended)
2. **Administrator privileges** (for installation)

## Step-by-Step Installation

### Step 1: Install Python

1. Download Python 3.11 or higher from [python.org](https://www.python.org/downloads/)
   - Choose the latest stable version (3.11, 3.12, or 3.13)
   - Download the "Windows installer (64-bit)" for your system

2. Run the installer:
   - **IMPORTANT**: Check "Add Python to PATH" at the bottom of the first screen
   - **IMPORTANT**: On the "Optional Features" screen, ensure "tcl/tk and IDLE" is checked (this includes tkinter)
   - Click "Install Now" or "Customize installation"

3. Verify installation:
   - Open Command Prompt (Win + R, type `cmd`, press Enter)
   - Run: `python --version`
   - You should see: `Python 3.x.x`

### Step 2: Open Terminal

You can use either:
- **Command Prompt**: Press `Win + R`, type `cmd`, press Enter
- **PowerShell**: Press `Win + X`, select "Windows PowerShell" or "Terminal"

### Step 3: Navigate to Project Directory

```cmd
cd path\to\ece-capstone
```

For example:
```cmd
cd C:\Users\YourName\Documents\ece-capstone
```

### Step 4: Create Virtual Environment

**In Command Prompt:**
```cmd
python -m venv venv
```

**In PowerShell:**
```powershell
python -m venv venv
```

If you get an error about execution policy in PowerShell, run:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Step 5: Activate Virtual Environment

**In Command Prompt:**
```cmd
venv\Scripts\activate
```

**In PowerShell:**
```powershell
venv\Scripts\Activate.ps1
```

You should see `(venv)` at the beginning of your command prompt.

### Step 6: Install Dependencies

```cmd
python -m pip install --upgrade pip
pip install -r requirements.txt
```

This will install:
- pyvisa
- pyvisa-py
- numpy
- matplotlib
- and their dependencies

### Step 7: Test the Setup

```cmd
python test_setup.py
```

You should see all tests passing:
```
✓ Package imports: PASS
✓ GUI functionality: PASS
✓ Application modules: PASS
✓ VISA backend: PASS
```

## Running the Application

### Method 1: Using the Batch Script (Easiest)

1. Double-click `run.bat` in Windows Explorer
2. Or run from Command Prompt:
   ```cmd
   run.bat
   ```

### Method 2: Manual Activation

**Command Prompt:**
```cmd
venv\Scripts\activate
python "OPREL Laser Measurement Suite.py"
```

**PowerShell:**
```powershell
venv\Scripts\Activate.ps1
python "OPREL Laser Measurement Suite.py"
```

## Troubleshooting

### "python is not recognized"

**Solution**: Python is not in your PATH
1. Reinstall Python and ensure "Add Python to PATH" is checked
2. Or use the Python launcher: `py -m venv venv`
3. Or manually add Python to PATH:
   - Search "Environment Variables" in Windows
   - Edit "Path" variable
   - Add: `C:\Users\YourName\AppData\Local\Programs\Python\Python3xx\`
   - Add: `C:\Users\YourName\AppData\Local\Programs\Python\Python3xx\Scripts\`

### "tkinter module not found"

**Solution**: tkinter was not installed
1. Reinstall Python
2. On "Optional Features" screen, check "tcl/tk and IDLE"
3. Or install manually: Download tcl/tk from ActiveState or use conda

### "Execution Policy" error in PowerShell

**Solution**: Change PowerShell execution policy
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### "Could not locate a VISA implementation"

**Solution**: Install pyvisa-py backend
```cmd
pip install pyvisa-py
```

### GUI window doesn't appear

**Solution**: Check if tkinter is working
```cmd
python -c "import tkinter; tkinter.Tk().mainloop()"
```
A blank window should appear. Close it to continue.

## Using with Instruments

### USB/Serial Instruments

The `pyvisa-py` backend supports:
- USB instruments (via libusb)
- Serial/COM port instruments
- TCP/IP instruments

### GPIB Instruments

For GPIB instruments, you may need:
- NI-VISA (National Instruments)
- Keysight IO Libraries Suite

Install the appropriate driver and configure it in your system.

## Additional Resources

- [Python Windows Installation Guide](https://docs.python.org/3/using/windows.html)
- [PyVISA Documentation](https://pyvisa.readthedocs.io/)
- [Virtual Environments Guide](https://docs.python.org/3/tutorial/venv.html)

