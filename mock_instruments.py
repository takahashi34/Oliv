"""
Mock Instruments Module for Testing Without Hardware

This module provides simulated VISA instruments for testing the Laser Measurement Suite
without actual oscilloscopes, pulsers, or power supplies connected.

Usage:
    Set the environment variable MOCK_INSTRUMENTS=1 before running the application,
    or modify the USE_MOCK_INSTRUMENTS flag below.

    Example (terminal):
        export MOCK_INSTRUMENTS=1
        python "OPREL Laser Measurement Suite.py"
    
    Example (Windows):
        set MOCK_INSTRUMENTS=1
        python "OPREL Laser Measurement Suite.py"
"""

import os
import random
import math
from time import sleep

# Set this to True to force mock mode, or use environment variable
USE_MOCK_INSTRUMENTS = os.environ.get('MOCK_INSTRUMENTS', '0') == '1'


class MockInstrument:
    """Base class for mock VISA instruments"""
    
    def __init__(self, address):
        self.address = address
        self._settings = {}
        self._output_on = False
        self._voltage = 0.0
        self._current = 0.0
        print(f"[MOCK] Connected to simulated instrument at {address}")
    
    def write(self, command):
        """Simulate writing a command to the instrument"""
        cmd_upper = command.upper()
        
        # Parse common commands
        if "*RST" in cmd_upper:
            self._reset()
        elif "*CLS" in cmd_upper:
            pass  # Clear status - no action needed
        elif "OUTPUT ON" in cmd_upper or "OUTP ON" in cmd_upper:
            self._output_on = True
        elif "OUTPUT OFF" in cmd_upper or "OUTP OFF" in cmd_upper:
            self._output_on = False
        elif "VOLT" in cmd_upper:
            # Extract voltage value
            try:
                parts = command.split()
                for i, p in enumerate(parts):
                    if 'VOLT' in p.upper():
                        if ':' in p or '=' in p:
                            val = p.split(':')[-1].split('=')[-1]
                        elif i + 1 < len(parts):
                            val = parts[i + 1]
                        else:
                            val = "0"
                        self._voltage = float(val.replace('V', ''))
                        break
            except (ValueError, IndexError):
                pass
        elif "CURR" in cmd_upper or "SOUR:CURR" in cmd_upper:
            # Extract current value
            try:
                parts = command.split()
                for i, p in enumerate(parts):
                    if 'CURR' in p.upper():
                        if i + 1 < len(parts):
                            self._current = float(parts[i + 1])
                        break
                # Also try format "sour:curr VALUE"
                if "SOUR:CURR" in cmd_upper:
                    val = command.split()[-1]
                    self._current = float(val)
            except (ValueError, IndexError):
                pass
        
        # Store setting for potential queries
        self._settings[command] = True
    
    def query(self, command):
        """Simulate querying the instrument - returns string"""
        cmd_upper = command.upper()
        
        if "*IDN?" in cmd_upper:
            return f"Mock Instrument,Model 1000,SN12345,1.0"
        elif "READ?" in cmd_upper:
            # Return simulated current reading for Keithley
            return str(self._current + random.gauss(0, 0.0001))
        
        return "0"
    
    def query_ascii_values(self, command):
        """Simulate querying numeric values from the instrument"""
        cmd_upper = command.upper()
        
        if "VAMPLITUDE" in cmd_upper or "VMAX" in cmd_upper:
            # Simulate oscilloscope amplitude measurement
            return [self._simulate_measurement()]
        elif "MEASURE" in cmd_upper:
            return [self._simulate_measurement()]
        
        return [0.0]
    
    def _reset(self):
        """Reset instrument to default state"""
        self._settings = {}
        self._output_on = False
        self._voltage = 0.0
        self._current = 0.0
    
    def _simulate_measurement(self):
        """Override in subclasses for specific measurement simulation"""
        return random.gauss(0.1, 0.01)
    
    def close(self):
        """Close the mock connection"""
        print(f"[MOCK] Disconnected from {self.address}")


class MockOscilloscope(MockInstrument):
    """Simulated oscilloscope with realistic laser diode responses"""
    
    def __init__(self, address):
        super().__init__(address)
        self._channel_scales = {1: 0.001, 2: 0.001, 3: 0.001, 4: 0.001}
        self._channel_impedance = {1: "FIFT", 2: "FIFT", 3: "FIFT", 4: "FIFT"}
        self._last_current = 0.0
        self._last_voltage = 0.0
        self._threshold_current = 0.015  # 15mA threshold current
        self._slope_efficiency = 0.8  # W/A above threshold
        
    def write(self, command):
        super().write(command)
        cmd_upper = command.upper()
        
        # Parse channel scale commands
        if ":CHANNEL" in cmd_upper and ":SCALE" in cmd_upper:
            try:
                # Extract channel number and scale value
                import re
                match = re.search(r':CHANNEL(\d+):SCALE\s+([\d.]+)', command, re.IGNORECASE)
                if match:
                    ch = int(match.group(1))
                    scale = float(match.group(2))
                    self._channel_scales[ch] = scale
            except (ValueError, AttributeError):
                pass
    
    def set_input_current(self, current):
        """Set the simulated input current (called by mock pulser/keithley)"""
        self._last_current = current
    
    def set_input_voltage(self, voltage):
        """Set the simulated input voltage"""
        self._last_voltage = voltage
        
    def _simulate_measurement(self):
        """Simulate realistic laser diode measurement"""
        # Simulate a laser diode L-I characteristic
        # Below threshold: minimal light output
        # Above threshold: linear increase with slope efficiency
        
        current = self._last_current
        
        if current < self._threshold_current:
            # Below threshold - just spontaneous emission noise
            light = current * 0.01 + random.gauss(0, 0.0005)
        else:
            # Above threshold - lasing
            light = (current - self._threshold_current) * self._slope_efficiency
            light += random.gauss(0, light * 0.02)  # 2% noise
        
        # Convert to voltage (assuming photodetector responsivity)
        voltage_out = abs(light) * 0.5  # 0.5 V/W responsivity
        
        # Add realistic noise floor
        voltage_out = max(voltage_out, random.gauss(0.0001, 0.00005))
        
        return voltage_out


class MockPulser(MockInstrument):
    """Simulated AVTECH voltage pulser"""
    
    def __init__(self, address, oscilloscope=None):
        super().__init__(address)
        self._pulse_width = 1.0  # us
        self._frequency = 1.0  # kHz
        self._oscilloscope = oscilloscope
        
    def write(self, command):
        super().write(command)
        cmd_upper = command.upper()
        
        # Parse pulse parameters
        if "PULSE:WIDTH" in cmd_upper or "PULS:WIDT" in cmd_upper:
            try:
                val = command.split()[-1].replace('us', '').replace('US', '')
                self._pulse_width = float(val)
            except ValueError:
                pass
        elif "FREQ" in cmd_upper:
            try:
                val = command.split()[-1].replace('kHz', '').replace('KHZ', '')
                self._frequency = float(val)
            except ValueError:
                pass
        elif "VOLT" in cmd_upper:
            # When voltage is set, update the connected oscilloscope
            if self._oscilloscope:
                # Simulate current based on voltage (rough laser diode model)
                # V = I*R + Vd, assume R=5 ohms, Vd=1.5V
                if self._voltage > 1.5:
                    current = (self._voltage - 1.5) / 50.0  # 50 ohm load
                else:
                    current = 0
                self._oscilloscope.set_input_current(current)
                self._oscilloscope.set_input_voltage(self._voltage)
    
    def set_oscilloscope(self, scope):
        """Link this pulser to an oscilloscope for coordinated simulation"""
        self._oscilloscope = scope


class MockKeithley(MockInstrument):
    """Simulated Keithley current source/measure unit"""
    
    def __init__(self, address, oscilloscope=None):
        super().__init__(address)
        self._oscilloscope = oscilloscope
        self._compliance = 10.0  # V
        self._source_mode = "CURR"
        
    def write(self, command):
        super().write(command)
        cmd_upper = command.upper()
        
        # Update oscilloscope when current is set
        if "SOUR:CURR" in cmd_upper or (self._source_mode == "CURR" and "CURR" in cmd_upper):
            if self._oscilloscope and self._output_on:
                self._oscilloscope.set_input_current(self._current)
        
        if "SOUR:FUNC" in cmd_upper:
            if "CURR" in cmd_upper:
                self._source_mode = "CURR"
            elif "VOLT" in cmd_upper:
                self._source_mode = "VOLT"
    
    def query(self, command):
        cmd_upper = command.upper()
        
        if "READ?" in cmd_upper:
            # Return the set current with small measurement noise
            if self._oscilloscope:
                self._oscilloscope.set_input_current(self._current)
            return str(self._current + random.gauss(0, abs(self._current) * 0.001 + 0.00001))
        
        return super().query(command)
    
    def set_oscilloscope(self, scope):
        """Link this Keithley to an oscilloscope for coordinated simulation"""
        self._oscilloscope = scope


class MockCurrentPulser(MockInstrument):
    """Simulated current pulser (for current-pulsed measurements)"""
    
    def __init__(self, address, oscilloscope=None):
        super().__init__(address)
        self._pulse_width = 1.0  # us
        self._frequency = 1.0  # kHz  
        self._oscilloscope = oscilloscope
        
    def write(self, command):
        super().write(command)
        cmd_upper = command.upper()
        
        # Parse current setting
        if "CURR" in cmd_upper:
            try:
                parts = command.split()
                for i, p in enumerate(parts):
                    if 'CURR' in p.upper() and i + 1 < len(parts):
                        self._current = float(parts[i + 1])
                        break
            except (ValueError, IndexError):
                pass
            
            # Update oscilloscope
            if self._oscilloscope and self._output_on:
                self._oscilloscope.set_input_current(self._current)
    
    def set_oscilloscope(self, scope):
        """Link this pulser to an oscilloscope for coordinated simulation"""
        self._oscilloscope = scope


class MockResourceManager:
    """Mock pyvisa ResourceManager"""
    
    def __init__(self, *args, **kwargs):
        self._instruments = {}
        self._oscilloscope = None  # Shared oscilloscope for coordination
        print("[MOCK] Using simulated VISA Resource Manager")
        print("[MOCK] No real instruments will be accessed")
    
    def list_resources(self):
        """Return a list of fake available resources"""
        return (
            'GPIB0::1::INSTR',   # Simulated Keithley
            'GPIB0::2::INSTR',   # Simulated Pulser  
            'USB0::0x2A8D::0x1797::MY12345678::INSTR',  # Simulated Keysight Scope
            'TCPIP0::192.168.1.100::INSTR',  # Simulated networked instrument
        )
    
    def open_resource(self, address):
        """Open a mock resource based on address pattern"""
        address_upper = address.upper()
        
        # Create shared oscilloscope if needed
        if self._oscilloscope is None:
            self._oscilloscope = MockOscilloscope("MOCK_SCOPE")
        
        # Detect instrument type from address or return generic mock
        if 'USB' in address_upper or 'SCOPE' in address_upper or '2A8D' in address_upper:
            # Likely an oscilloscope
            instrument = self._oscilloscope
            instrument.address = address
        elif 'GPIB' in address_upper:
            # Could be Keithley or pulser - check address number
            if '::1::' in address or '::5::' in address:
                # Assume Keithley
                instrument = MockKeithley(address, self._oscilloscope)
            elif '::2::' in address or '::3::' in address:
                # Assume voltage pulser
                instrument = MockPulser(address, self._oscilloscope)
            elif '::4::' in address:
                # Assume current pulser
                instrument = MockCurrentPulser(address, self._oscilloscope)
            else:
                instrument = MockInstrument(address)
        elif 'TCPIP' in address_upper:
            # Network instrument - could be scope
            instrument = MockOscilloscope(address)
            self._oscilloscope = instrument
        else:
            # Default to generic mock
            instrument = MockInstrument(address)
        
        self._instruments[address] = instrument
        return instrument
    
    def close(self):
        """Close all mock resources"""
        for addr, inst in self._instruments.items():
            inst.close()
        self._instruments = {}


def get_resource_manager():
    """
    Factory function to get the appropriate ResourceManager.
    Returns MockResourceManager if MOCK_INSTRUMENTS is enabled,
    otherwise returns the real pyvisa.ResourceManager.
    """
    if USE_MOCK_INSTRUMENTS:
        return MockResourceManager()
    else:
        import pyvisa
        return pyvisa.ResourceManager()


# Print status on import
if USE_MOCK_INSTRUMENTS:
    print("=" * 60)
    print("  MOCK INSTRUMENT MODE ENABLED")
    print("  All instrument communications will be simulated")
    print("  Set MOCK_INSTRUMENTS=0 to use real instruments")
    print("=" * 60)


