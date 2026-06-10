import time
import numpy as np
from core_types import SweepParameters, MeasurementType, SafetyLimits, SweepType
from instruments import read_light, init_keithley
from Oscilloscope_Scaling import incrOscVertScale

def build_sweep_array(params: SweepParameters):
    if params.sweep_type == SweepType.LINEAR:
        arr = np.arange(params.start_val, params.stop_val, params.step_size)
        arr = np.append(arr, params.stop_val)
        return arr
    elif params.sweep_type == SweepType.LOGARITHMIC:
        voltage_source_pos = np.logspace(-4, np.log10(params.stop_val), int(params.num_pts) // 2)
        voltage_source_neg = -np.logspace(np.log10(abs(params.start_val)), -4, int(params.num_pts) // 2)
        return np.append(voltage_source_neg, voltage_source_pos)
    return np.array([params.start_val, params.stop_val])

def sweep_and_collect(instruments_dict, config, params: SweepParameters, meas_type: MeasurementType, safety: SafetyLimits, update_callback, check_stop_flag):
    """
    Sweep and collect data block:
    Input: Configured instrument addresses cluster, Typedef enum, Sweep parameters cluster
    Output: Raw dataset (yielded or returned)
    """
    
    sweep_array = build_sweep_array(params)
    n_pts = len(sweep_array)
    
    current_array = np.zeros(n_pts, float)
    light_array = np.zeros(n_pts, float)
    
    # 1. Fetch Instruments from Dictionary
    smu = instruments_dict.get('smu')
    pulser = instruments_dict.get('pulser')

    osc = instruments_dict.get('osc')
    det = instruments_dict.get('det')
    thermopile = instruments_dict.get('thermopile')
    thermo_id = instruments_dict.get('thermo_id')
    
    vertScaleLight = 0.001
    totalDisplayLight = 6 * vertScaleLight if config.light_mode.value == 'osc' else float('inf')
    
    vertScaleCurrent = 0.001
    totalDisplayCurrent = 6 * vertScaleCurrent
    vertScaleVoltage = 0.001
    totalDisplayVoltage = 6 * vertScaleVoltage

    if osc and meas_type in (MeasurementType.VPULSE, MeasurementType.IPULSE):
        pulseWidth = params.pulse_width if params.pulse_width else 1.0
        if meas_type == MeasurementType.VPULSE:
            osc.write(f":TIMebase:RANGe {10 * pulseWidth * 10:.6f}us")
            osc.write(":TRIGger:MODE GLITch")
            osc.write(f":TRIGger:GLITch:SOURce CHANnel{config.trigger_channel}")
            osc.write(":TRIGger:GLITch:QUALifier RANGe")
            glitchTriggerLower = pulseWidth * 0.5
            glitchTriggerUpper = pulseWidth * 1.5
            osc.write(f":TRIGger:GLITch:RANGe {glitchTriggerLower:.6f}us,{glitchTriggerUpper:.6f}us")
            osc.write("TRIGger:GLITch:LEVel 1E-3")
        else: # IPULSE
            osc.write(":TIMebase:RANGe 2E-6")
            osc.write(":TRIGger:MODE EDGE")
            osc.write(f":TRIGger:EDGE:SOURce CHANnel{config.trigger_channel}")
            osc.write(":TRIGger:LEVel:ASETup")

    prevPulserVoltage = 0.0


    # Measurement Loop
    for i in range(n_pts):
        if check_stop_flag():
            print("Measurement stopped by user.")
            break
            
        # Check Safety: latest light value reaches 90% of the maximum light value that was measured
        if i >= 1:
            max_light_so_far = np.max(light_array[:i])
            # To prevent triggering on noise at the start, ensure max_light_so_far is somewhat above the noise floor (e.g. 1uW)
            if max_light_so_far > 1e-6 and light_array[i-1] <= 0.9 * max_light_so_far:
                print(f"Safety Trigger: Light {light_array[i-1]:.6f} dropped to/below 90% of max {max_light_so_far:.6f}")
                break

        if i >= 1 and light_array[i-1] > safety.max_light:
            print(f"Safety Trigger: Light {light_array[i-1]} exceeded max limit {safety.max_light}")
            break

        # Set parameter
        set_val = round(sweep_array[i], 3)
        if meas_type in (MeasurementType.CW_VOLTAGE, MeasurementType.CW_CURRENT) and smu:
            if meas_type == MeasurementType.CW_VOLTAGE:
                # We are setting voltage and measuring current
                smu.write("sour:func volt")
                smu.write("sens:curr:rang:auto on")
                smu.write("sens:func 'curr'")
                smu.write("form:elem curr")
                smu.write("outp on")
                smu.write("sour:volt:lev " + str(set_val))
                
                # Wait settle time (assuming 0.1s for CW)
                time.sleep(0.1)
                
                # Read current
                curr_str = smu.query("read?")
                try:
                    current_array[i] = eval(curr_str)
                except:
                    current_array[i] = 0.0
            else:
                # We are setting current and measuring voltage
                smu.write("sour:func curr")
                smu.write("sens:volt:rang:auto on")
                smu.write("sens:func 'volt'")
                smu.write("form:elem volt")
                smu.write("outp on")
                smu.write("sour:curr:lev " + str(set_val))
                
                # Wait settle time (assuming 0.1s for CW)
                time.sleep(0.1)
                
                # Read voltage
                volt_str = smu.query("read?")
                try:
                    current_array[i] = set_val
                    sweep_array[i] = eval(volt_str)
                except:
                    current_array[i] = set_val
                    sweep_array[i] = 0.0

        elif meas_type == MeasurementType.VPULSE and pulser:
            is_glitch = any(prevPulserVoltage <= gp < set_val for gp in params.glitch_points)
            if is_glitch:
                pulser.write("output off")
                pulser.write(f"volt {set_val:.3f}")
                prevPulserVoltage = set_val
                time.sleep(4)
                pulser.write("OUTPut ON")
            else:
                pulser.write(f"VOLT {set_val:.3f}")
                pulser.write("OUTPut ON")
                
            time.sleep(0.1) # Give scope time to trigger
            
            curr_str = osc.query_ascii_values(f"SINGLE;*OPC;:MEASure:VAMPlitude? CHANNEL{config.curr_channel}")[0]
            volt_str = osc.query_ascii_values(f"SINGLE;*OPC;:MEASure:VAMPlitude? CHANNEL{config.volt_channel}")[0]
            
            current_array[i] = 2 * curr_str # 2 * for 50 ohms
            sweep_array[i] = volt_str
            prevPulserVoltage = set_val

        elif meas_type == MeasurementType.IPULSE and pulser:
            pulser.write(f":LDI {set_val:.3f}")
            if float(pulser.query(":LDI?")) != set_val:
                pulser.write(f":LDI {set_val:.3f}")
                time.sleep(1)
            pulser.write("OUTPut ON")
            time.sleep(0.1)
            
            osc.write(":TRIGger:LEVel:ASETup")
            curr_str = osc.query_ascii_values(f"SINGLE;*OPC;:MEASure:VAMPlitude? CHANNEL{config.curr_channel}")[0]
            volt_str = osc.query_ascii_values(f"SINGLE;*OPC;:MEASure:VAMPlitude? CHANNEL{config.volt_channel}")[0]

            current_array[i] = 2 * curr_str
            sweep_array[i] = volt_str

        
        # Read Light
        if config.light_mode.value == 'thermo':
            light_val = read_light(thermopile, config.light_mode.value, thermo_id, config.light_channel)
        elif config.light_mode.value == 'osc':
            light_val = read_light(osc, config.light_mode.value, thermo_id, config.light_channel)
        else:
            light_val = read_light(det, config.light_mode.value, thermo_id, config.light_channel)
        
        # Autoscale oscilloscope if necessary
        if config.light_mode.value == 'osc' and osc:
            while light_val > 0.9 * totalDisplayLight:
                vertScaleLight = incrOscVertScale(vertScaleLight)
                totalDisplayLight = 6 * vertScaleLight
                osc.write(f":CHANNEL{config.light_channel}:SCALe {float(vertScaleLight):.3f}")
                light_val = read_light(osc, config.light_mode.value, thermo_id, config.light_channel)
                
        if meas_type in (MeasurementType.VPULSE, MeasurementType.IPULSE) and osc:
            curr_str = current_array[i] / 2.0
            volt_str = sweep_array[i]

            while curr_str > 0.9 * totalDisplayCurrent:
                vertScaleCurrent = incrOscVertScale(vertScaleCurrent)
                totalDisplayCurrent = 6 * vertScaleCurrent
                osc.write(f":CHANNEL{config.curr_channel}:SCALe {float(vertScaleCurrent):.3f}")
                curr_str = osc.query_ascii_values(f"SINGLE;*OPC;:MEASure:VAMPlitude? CHANNEL{config.curr_channel}")[0]
                volt_str = osc.query_ascii_values(f"SINGLE;*OPC;:MEASure:VAMPlitude? CHANNEL{config.volt_channel}")[0]
                current_array[i] = 2 * curr_str
                sweep_array[i] = volt_str

            while volt_str > 0.9 * totalDisplayVoltage:
                vertScaleVoltage = incrOscVertScale(vertScaleVoltage)
                totalDisplayVoltage = 6 * vertScaleVoltage
                osc.write(f":CHANNEL{config.volt_channel}:SCALe {float(vertScaleVoltage):.3f}")
                curr_str = osc.query_ascii_values(f"SINGLE;*OPC;:MEASure:VAMPlitude? CHANNEL{config.curr_channel}")[0]
                volt_str = osc.query_ascii_values(f"SINGLE;*OPC;:MEASure:VAMPlitude? CHANNEL{config.volt_channel}")[0]
                current_array[i] = 2 * curr_str
                sweep_array[i] = volt_str
                
        light_array[i] = light_val
        
        # Send data to GUI for live plot
        if update_callback:
            # Current in mA, Light in mW, Voltage in V for plotting
            update_callback(current_array[i] * 1000, light_array[i] * 1000, sweep_array[i])

    # Truncate arrays if stopped early
    actual_pts = i if check_stop_flag() or (i > 0 and light_array[i-1] > safety.max_light) else i + 1
    if actual_pts < n_pts:
        sweep_array = sweep_array[:actual_pts]
        current_array = current_array[:actual_pts]
        light_array = light_array[:actual_pts]
        
    return sweep_array, current_array, light_array
