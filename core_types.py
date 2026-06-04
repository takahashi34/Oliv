from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

class MeasurementType(Enum):
    CW_VOLTAGE = auto()
    CW_CURRENT = auto()
    VPULSE = auto()
    IPULSE = auto()

class SweepType(Enum):
    LINEAR = auto()
    LOGARITHMIC = auto()
    LINLOG = auto()

class LightMode(Enum):
    THERMOPILE = 'thermo'
    OSCILLOSCOPE = 'osc'
    SOURCEMETER = 'SourceMeter'
    NONE = 'None (IV)'

@dataclass
class InstrumentConfig:
    """Cluster for configured instrument addresses and settings"""
    # Addresses
    smu_address: str = 'Select...'
    osc_address: str = 'Select...'
    det_address: str = 'Select...'
    pulser_address: Optional[str] = None
    tec_address: Optional[str] = None
    
    # Modes
    light_mode: LightMode = LightMode.OSCILLOSCOPE
    
    # Channels & Impedance (for Oscilloscope)
    light_channel: int = 1
    light_channel_impedance: str = '50Ω'
    volt_channel: Optional[int] = None
    volt_channel_impedance: str = '50Ω'
    curr_channel: Optional[int] = None
    curr_channel_impedance: str = '50Ω'
    trigger_channel: Optional[int] = None
    
    # Thermopile specifics
    thermopile_wavelength: Optional[str] = None

@dataclass
class SweepParameters:
    """Cluster for sweep and measurement parameters"""
    sweep_type: SweepType = SweepType.LINEAR
    
    # Swept parameter limits
    start_val: float = 0.0
    stop_val: float = 0.0
    step_size: float = 0.0  # Used in Linear
    num_pts: int = 10       # Used in Log
    
    # Compliance limits
    compliance: float = 0.0 # mA or V depending on mode
    
    # Pulsed specific (if needed later)
    pulse_width: Optional[float] = None
    pulse_delay: Optional[float] = None
    frequency: Optional[float] = None
    glitch_points: List[float] = field(default_factory=list)

@dataclass
class DeviceInfo:
    """Metadata for plotting and data saving"""
    device_name: str = 'Unknown'
    dimensions: str = 'N/A'
    temperature: str = '25'
    test_type: str = 'Laser' # 'Laser' or 'TestStructure'
    plot_dir: str = './plots'
    txt_dir: str = './data'

@dataclass
class SafetyLimits:
    max_light: float = float('inf') # Maximum allowed light read before stopping
    li_slope_threshold: float = 0.0 # LI slope evaluated at two most recent points
