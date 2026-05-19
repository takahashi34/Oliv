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
    
    # 1. Finalize Initialization (e.g. Keithley compliance which needs params)
    smu = None
    if meas_type == MeasurementType.CW and config.smu_address != 'Select...':
        import pyvisa
        rm = pyvisa.ResourceManager()
        smu = init_keithley(rm, config.smu_address, 'volt', params.compliance)
        instruments_dict['smu'] = smu # save for shutdown
        
    osc = instruments_dict.get('osc')
    thermo_id = instruments_dict.get('thermo_id')
    
    vertScaleLight = 0.001
    totalDisplayCurrent = 6 * vertScaleLight if config.light_mode.value == 'osc' else float('inf')

    # Measurement Loop
    for i in range(n_pts):
        if check_stop_flag():
            print("Measurement stopped by user.")
            break
            
        # Check Safety: LI slope evaluated at two most recent points > 0 AND most recent point < max light
        if i >= 2:
            d_light = light_array[i-1] - light_array[i-2]
            d_curr = current_array[i-1] - current_array[i-2]
            if d_curr != 0:
                li_slope = d_light / d_curr
                if li_slope < safety.li_slope_threshold:
                    print(f"Safety Trigger: L-I slope {li_slope} dropped below threshold {safety.li_slope_threshold}")
                    break
        if i >= 1 and light_array[i-1] > safety.max_light:
            print(f"Safety Trigger: Light {light_array[i-1]} exceeded max limit {safety.max_light}")
            break

        # Set parameter
        set_val = round(sweep_array[i], 3)
        if meas_type == MeasurementType.CW and smu:
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
        
        # Read Light
        light_val = read_light(osc, config.light_mode.value, thermo_id, config.light_channel)
        
        # Autoscale oscilloscope if necessary
        if config.light_mode.value == 'osc' and osc:
            while light_val > 0.9 * totalDisplayCurrent:
                vertScaleLight = incrOscVertScale(vertScaleLight)
                totalDisplayCurrent = 6 * vertScaleLight
                osc.write(f":CHANNEL{config.light_channel}:SCALe {float(vertScaleLight):.3f}")
                light_val = read_light(osc, config.light_mode.value, thermo_id, config.light_channel)
                
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
