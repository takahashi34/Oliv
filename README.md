# LIV-IV-LI
 
The LIV-IV-LI Github repository supports the OPREL (Optics and Photonics REsearch Lab) at the Ohio State University. 
This repository stores tools used to test and record the LIV, IV, and LI characteristics of lasers.

## Quick Links

- **[Windows Setup Guide](WINDOWS_SETUP.md)** - Detailed Windows installation instructions
- [Requirements](#requirements) - System requirements and dependencies
- [Installation](#installation) - Platform-specific installation steps
- [Running the Software](#running-the-software) - How to launch the application

## Installation

### macOS Setup

1. **Install Python with tkinter support** (required for GUI):
   ```bash
   brew install python-tk
   ```
   This will install Python 3.14 with tkinter support.

2. Create and activate virtual environment:
   ```bash
   # Use Python 3.14 if available (has tkinter), otherwise use python3
   python3.14 -m venv venv
   # or
   python3 -m venv venv
   
   source venv/bin/activate
   ```

3. Install required dependencies:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. Test the setup:
   ```bash
   python test_setup.py
   ```

### Windows Setup

1. **Install Python 3.11 or higher**:
   - Download from [python.org](https://www.python.org/downloads/)
   - **Important**: During installation, check "Add Python to PATH"
   - **Important**: Check "tcl/tk and IDLE" (tkinter is included by default on Windows)

2. **Open Command Prompt or PowerShell**:
   - Press `Win + R`, type `cmd` or `powershell`, press Enter
   - Navigate to the project directory:
     ```cmd
     cd path\to\ece-capstone
     ```

3. **Create and activate virtual environment**:
   ```cmd
   python -m venv venv
   venv\Scripts\activate
   ```
   Or in PowerShell:
   ```powershell
   python -m venv venv
   venv\Scripts\Activate.ps1
   ```
   Note: If you get an execution policy error in PowerShell, run:
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```

4. **Install required dependencies**:
   ```cmd
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

5. **Test the setup**:
   ```cmd
   python test_setup.py
   ```

### Manual Installation (Without Virtual Environment)

**macOS:**
1. Install Python 3 (if not already installed)
2. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

**Windows:**
1. Install Python 3.11+ from [python.org](https://www.python.org/downloads/)
2. Open Command Prompt and install dependencies:
   ```cmd
   pip install -r requirements.txt
   ```

## Running the Software

### macOS / Linux

**Option 1: Using the run script** (recommended - automatically uses virtual environment)
```bash
./run.sh
```

**Option 2: Activate virtual environment manually, then run**
```bash
source venv/bin/activate
python "OPREL Laser Measurement Suite.py"
```

**Option 3: Using the activation helper script**
```bash
source activate_env.sh
python "OPREL Laser Measurement Suite.py"
```

### Windows

**Option 1: Using Command Prompt**
```cmd
venv\Scripts\activate
python "OPREL Laser Measurement Suite.py"
```

**Option 2: Using PowerShell**
```powershell
venv\Scripts\Activate.ps1
python "OPREL Laser Measurement Suite.py"
```

**Option 3: Double-click run script** (if created)
- Create a `run.bat` file (see below) and double-click it

**Note**: On Windows, you may need to use quotes around the filename:
```cmd
python "OPREL Laser Measurement Suite.py"
```

## Testing the Setup

Before running the application, you can verify everything is set up correctly:

**macOS / Linux:**
```bash
source venv/bin/activate
python test_setup.py
```

**Windows:**
```cmd
venv\Scripts\activate
python test_setup.py
```

This will test:
- ✓ All required packages are installed
- ✓ GUI (tkinter) is working
- ✓ Application modules can be imported
- ✓ VISA backend is configured

The application will open a GUI window where you can select the type of measurement (CW, Voltage Pulsed, or Current Pulsed) and the measurement type (L-I-V, I-V, or L-I).

## Requirements

- **Python 3.11 or higher**
  - macOS: Python 3.14 recommended (via `brew install python-tk`)
  - Windows: Python 3.11+ from [python.org](https://www.python.org/downloads/)
- **tkinter** (GUI framework)
  - macOS: Included with `python-tk` package
  - Windows: Included with Python installer (check "tcl/tk and IDLE" during install)
- **pyvisa** (for instrument communication)
- **pyvisa-py** (pure Python VISA backend - no drivers needed)
- **numpy** (for numerical computing)
- **matplotlib** (for plotting)

### Optional Dependencies

For enhanced VISA functionality (network discovery):
- `psutil` - for scanning all network interfaces
- `zeroconf` - for HiSLIP resource discovery

Install with: `pip install psutil zeroconf`

### Windows-Specific Notes

- **VISA Backend**: On Windows, you can use either:
  - `pyvisa-py` (pure Python, no drivers needed) - **Recommended**
  - NI-VISA or Keysight VISA (if you have instruments that require them)
- **tkinter**: Should be included by default with Python on Windows. If missing, reinstall Python and ensure "tcl/tk and IDLE" is checked.
- **Path Issues**: If `python` command is not found, ensure Python was added to PATH during installation, or use `py` launcher: `py -m venv venv`

This repository is under-development.
