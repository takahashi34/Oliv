# Helper functions for instruments

def init_keithley(rm, address, source_mode, compliance):
    """
    Initialize a Keithley SMU for CW measurements.

    source_mode: 'curr' or 'volt'
    compliance:  compliance value in A or V (already converted)
    """
    k = rm.open_resource(address)

    k.write("*RST; status:preset; *CLS")
    k.write(f"sour:func {source_mode}")

    if source_mode == 'curr':
        k.write("sens:func 'volt'")
        k.write(f"sens:volt:prot:lev {compliance}")
        k.write("sens:volt:range:auto on")
    else:
        k.write("sens:func 'curr'")
        k.write(f"sens:curr:prot:lev {compliance}")
        k.write("sens:curr:range:auto on")

    k.write("form:elem curr")
    k.write("outp on")

    return k

def init_thermopile(rm, address, wavelength):
    """
    Opens a connection to a thermopile and configures it for the given wavelength.
    Returns: (thermopile_resource, id_string)
    """
    thermopile = rm.open_resource(address)
    id = thermopile.query("*IDN?")
    wavelength = int(wavelength)

    if "integra" in id.lower():
        thermopile.write("*CSU")
        thermopile.timeout = 5000
        thermopile.write_termination = ''
        thermopile.write(f"*PWC{wavelength:05d}")
        print("Thermopile wavelength set to %d nm" % wavelength)

    elif "coherent" in id.lower():
        thermopile.write("*RST")
        thermopile.write(f"CONFigure:WAVElength {wavelength:05d}")
        print("Thermopile wavelength set to %d nm" % wavelength)
        thermopile.write("CONFigure:ZERO")

    else:
        print(f"WARNING: Thermopile '{id}' is not compatible with this system.")

    return thermopile, id

def init_detector(rm, address, detectorID):
    if detectorID == 'SourceMeter':
        k = rm.open_resource(address)
        k.write("*rst; status:preset; *cls")                       # Reset GPIB defaults
        k.write("sour:func:mode curr")                             # Select source function mode as current source
        k.write("sour:curr 0")                                     # Set source level to 10V
        k.write("sens:func 'volt'")
        k.write("sens:volt:prot:lev " + str(21))                   # Set volt compliance
        k.write("sens:volt:range 1")                               # Set volt measure range 100mA
        k.write("outp on")
    return k

def read_light(detector, mode, detectorID, light_channel):
    if detector is None:
        return 0.0
    if detectorID == 'SourceMeter':
            raw = detector.query('READ?')
            return float(raw.split(',')[0])
    if mode == 'thermo':
        if detectorID is None:
            print("WARN: Thermopile not initialized.")
            return 0.0
        if "integra" in detector.lower():
            try:
                raw = detector.query('*CVU')
                return float(raw)
            except ValueError:
                print(f"Thermopile read error: {raw}")
                return 0.0
        elif "coherent" in detectorID.lower():
            try:
                raw = detector.query('READ?')
                return float(raw.split(',')[0])
            except ValueError:
                print(f"Thermopile read error: {raw}")
                return 0.0
        else:
            print(f"WARN: Thermopile {thermo_id} is not compatible with this system.")
            return 0.0
    else:
        return detector.query_ascii_values(
            "SINGLE;*OPC;:MEASure:VAMPlitude? CHANNEL%d" % light_channel
        )[0]

from core_types import InstrumentConfig, MeasurementType, LightMode
from Oscilloscope_Scaling import channelImpedance

def initialize_instruments(rm, config: InstrumentConfig, meas_type: MeasurementType):
    """
    Initialize instruments block:
    Input: Source & detector addresses (via InstrumentConfig)
    Internal behavior: Configure source & detector based on conditionals
    Output: Dictionary of initialized instrument objects
    """
    initialized = {
        'smu': None,
        'osc': None,
        'pulser': None,
        'thermopile': None,
        'thermo_id': None
    }
    
    # 1. Light Setup
    if config.light_mode == LightMode.THERMOPILE and config.osc_address != 'Select...':
        thermopile, thermo_id = init_thermopile(rm, config.osc_address, config.thermopile_wavelength)
        initialized['thermopile'] = thermopile
        initialized['thermo_id'] = thermo_id
        
    elif config.light_mode == LightMode.OSCILLOSCOPE and config.osc_address != 'Select...':
        osc = rm.open_resource(config.osc_address)
        osc.write("*RST")
        osc.write("*CLS")
        osc.write(f":CHANnel{config.light_channel}:IMPedance {channelImpedance(config.light_channel_impedance)}")
        osc.write(":TIMebase:RANGe 2E-6")
        vertScaleLight = 0.001
        osc.write(f":CHANNEL{config.light_channel}:SCALe {vertScaleLight:.3f}")
        osc.write(f":CHANnel{config.light_channel}:DISPlay ON")
        osc.write(f":CHANnel{config.light_channel}:OFFset {2 * vertScaleLight:.3f}V")
        initialized['osc'] = osc
        
    elif config.light_mode == LightMode.SOURCEMETER and config.osc_address != 'Select...':
        osc = init_detector(rm, config.osc_address, config.light_mode.value)
        initialized['osc'] = osc
        initialized['thermo_id'] = config.light_mode.value

    # 2. Current/Voltage Setup
    if meas_type == MeasurementType.CW:
        # SourceMeter for CW measurement
        if config.smu_address != 'Select...':
            # Note: compliance needs to be passed in, maybe we initialize it later or pass it in SweepParameters.
            # For now, we will let the sweep loop do the final config of the SMU, or do it here if compliance is known.
            # The original cw.py did this in start_liv_sweep.
            pass
            
    elif meas_type == MeasurementType.VPULSE:
        # Voltage pulser setup would go here
        pass
        
    elif meas_type == MeasurementType.IPULSE:
        # Current pulser setup would go here
        pass

    return initialized

def shutdown_instruments(instruments_dict):
    """
    Shutdown instruments (separate file/function)
    Input: Configured instruments cluster
    Behavior: Turn all source outputs off, Close all instruments and reset their configurations to default values
    """
    smu = instruments_dict.get('smu')
    if smu:
        try:
            smu.write("outp off")
            smu.close()
        except:
            pass
            
    thermopile = instruments_dict.get('thermopile')
    if thermopile:
        try:
            thermopile.write('*COU')
            thermopile.close()
        except:
            pass
            
    osc = instruments_dict.get('osc')
    if osc:
        try:
            osc.close()
        except:
            pass
            
    pulser = instruments_dict.get('pulser')
    if pulser:
        try:
            # Turn pulser off
            pulser.write("OUTP OFF")
            pulser.close()
        except:
            pass
            
    print("All instruments safely shut down.")
