# Helper functions for instruments

from pyvisa.constants import Parity, StopBits, VI_ASRL_FLOW_NONE

class LDC3724B_TEC:
    def __init__(self, rm, address):
        self.inst = rm.open_resource(address)

    def set_temperature(self, temp_c):
        self.inst.write(f"TEC:T {temp_c}")

    def get_temperature(self):
        return float(self.inst.query("TEC:T?").strip())

    def set_gain(self, gain):
        self.inst.write(f"TEC:GAIN {gain}")

    def output_on(self):
        self.inst.write("TEC:OUT 1")

    def output_off(self):
        self.inst.write("TEC:OUT 0")

    def output_state(self):
        return self.inst.query("TEC:OUT?").strip() == "1"

    def close(self):
        self.output_off()
        self.inst.close()

class LDT5525B_TEC:
    def __init__(self, rm, address):
        self.inst = rm.open_resource(address)

        self.inst.baud_rate = 115200
        self.inst.data_bits = 8
        self.inst.parity = Parity.none
        self.inst.stop_bits = StopBits.one
        self.inst.flow_control = VI_ASRL_FLOW_NONE
        self.inst.delay = 0.1
        self.inst.query_delay = 0.1
        self.inst.read_termination = '\n'
        self.inst.write_termination = '\n'
        self.inst.timeout = 10000

    def set_temperature(self, temp_c):
        self.inst.write(f"TEC:T {temp_c}")

    def get_temperature(self):
        return float(self.inst.query("TEC:T?").strip())

    def set_gain(self, gain):
        self.inst.write(f"TEC:GAIN {gain}")

    def output_on(self):
        self.inst.write("TEC:OUT 1")

    def output_off(self):
        self.inst.write("TEC:OUT 0")

    def output_state(self):
        return self.inst.query("TEC:OUT?").strip() == "1"

    def close(self):
        self.output_off()
        self.inst.close()

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
        k.write("form:elem volt")
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

    if "integra" in id.lower() or "wattmeter" in id.lower():
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
        if "integra" in detectorID.lower() or "wattmeter" in detectorID.lower():
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
            print(f"WARN: Thermopile {detectorID} is not compatible with this system.")
            return 0.0
    else:
        return detector.query_ascii_values(
            "SINGLE;*OPC;:MEASure:VAMPlitude? CHANNEL%d" % light_channel
        )[0]

from core_types import InstrumentConfig, MeasurementType, LightMode, SweepParameters
from Oscilloscope_Scaling import channelImpedance

def initialize_instruments(rm, config: InstrumentConfig, meas_type: MeasurementType, params: SweepParameters = None):
    """
    Initialize instruments block:
    Input: Source & detector addresses (via InstrumentConfig)
    Internal behavior: Configure source & detector based on conditionals
    Output: Dictionary of initialized instrument objects
    """
    # 'det' stores the sensor instrument object, except for thermopile.
    # It may refer to an oscilloscope or a SourceMeter used as a detector.
    # 'smu' stores the Keithley SourceMeter used as the source instrument.
    initialized = {
        'smu': None,
        'det': None,
        'osc': None,
        'pulser': None,
        'thermopile': None,
        'thermo_id': None
    }
    
    # 'det_address' here refers to sensors address, which is assigned in gui.py
    # 'thermo_id' here refers to sensors ID - thermo/osc
    # 1. Light Setup
    if config.light_mode == LightMode.THERMOPILE and config.det_address != 'Select...':
        thermopile, thermo_id = init_thermopile(rm, config.det_address, config.thermopile_wavelength)
        initialized['thermopile'] = thermopile
        initialized['thermo_id'] = thermo_id
        
    elif config.light_mode == LightMode.SOURCEMETER and config.det_address != 'Select...':
        det = init_detector(rm, config.det_address, config.light_mode.value) # 'det' actually stores a SourceMeter used as the light sensor
        initialized['det'] = det
        initialized['thermo_id'] = config.light_mode.value

    # 2. Oscilloscope Setup
    needs_osc = (config.light_mode == LightMode.OSCILLOSCOPE) or (meas_type in (MeasurementType.VPULSE, MeasurementType.IPULSE))
    if needs_osc and config.osc_address != 'Select...':
        if 'osc' not in initialized or initialized['osc'] is None:
            # if using osc as detector then open from det_address, if not then use osc_address
            if config.light_mode == LightMode.OSCILLOSCOPE:
                osc = rm.open_resource(config.det_address)
            else:
                osc = rm.open_resource(config.osc_address)
            osc.write("*RST")
            osc.write("*CLS")
            initialized['osc'] = osc
        else:
            osc = initialized['osc']

        if config.light_mode == LightMode.OSCILLOSCOPE:
            osc.write(f":CHANnel{config.light_channel}:IMPedance {channelImpedance(config.light_channel_impedance)}")
            osc.write(f":CHANNEL{config.light_channel}:SCALe 0.001")
            osc.write(f":CHANnel{config.light_channel}:DISPlay ON")
            osc.write(f":CHANnel{config.light_channel}:OFFset 0.002V")

        if meas_type in (MeasurementType.VPULSE, MeasurementType.IPULSE):
            if config.curr_channel:
                osc.write(f":CHANnel{config.curr_channel}:IMPedance {channelImpedance(config.curr_channel_impedance)}")
                osc.write(f":CHANNEL{config.curr_channel}:SCALe 0.001")
                osc.write(f":CHANnel{config.curr_channel}:DISPlay ON")
                osc.write(f":CHANnel{config.curr_channel}:OFFset 0.002V")
            if config.volt_channel:
                osc.write(f":CHANnel{config.volt_channel}:IMPedance {channelImpedance(config.volt_channel_impedance)}")
                osc.write(f":CHANNEL{config.volt_channel}:SCALe 0.001")
                osc.write(f":CHANnel{config.volt_channel}:DISPlay ON")
                osc.write(f":CHANnel{config.volt_channel}:OFFset 0.002V")

    # 2. Current/Voltage Setup
    if meas_type in (MeasurementType.CW_VOLTAGE, MeasurementType.CW_CURRENT):
        if config.smu_address != 'Select...' and params:
            source_mode = 'volt' if meas_type == MeasurementType.CW_VOLTAGE else 'curr'
            smu = init_keithley(rm, config.smu_address, source_mode, params.compliance)
            initialized['smu'] = smu

    elif meas_type in (MeasurementType.VPULSE, MeasurementType.IPULSE):
        if config.pulser_address and config.pulser_address != 'Select...' and params:
            pulser = rm.open_resource(config.pulser_address)
            initialized['pulser'] = pulser
            pulser.write("*RST")
            pulser.write("*CLS")
            if meas_type == MeasurementType.VPULSE:
                pulser.write("OUTPut:IMPedance 50")
                pulser.write("SOURce INTernal")
                if params.pulse_width:
                    pulser.write(f"PULSe:WIDTh {params.pulse_width}us")
                if params.frequency:
                    pulser.write(f"FREQuency {params.frequency}kHz")
                pulser.write("OUTPut ON")
            else: # IPULSE
                if params.pulse_width:
                    pulser.write(f":PW {params.pulse_width}")
                pulser.write(":DIS:LDI")
                pulser.write(f"LIMit:I {params.compliance * 1000.0}")
                pulser.write("OUTPut OFF")

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
            thermopile.clear()
            thermopile.close()
        except:
            pass
            
    det = instruments_dict.get('det')
    if det:
        try:
            det.close()
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
