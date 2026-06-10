import os
from datetime import datetime
import matplotlib.pyplot as plt
from dataAnal import export_to_origin
from core_types import DeviceInfo, MeasurementType

def save_and_plot_data(voltage_array, current_array, light_array, device_info: DeviceInfo, meas_type: MeasurementType):
    """
    Data analysis block:
    Input: Raw data (voltage, current, light arrays), DeviceInfo cluster, MeasurementType
    Output: Data to text file, plot to PNG, export data to Origin
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    prefix = meas_type.name.lower()
    filename = f'{prefix}_{device_info.device_name}Celsius_{device_info.temperature}_{timestamp}'
    
    # 1. Save data to text file
    if not os.path.exists(device_info.txt_dir):
        try:
            os.makedirs(device_info.txt_dir)
        except Exception as e:
            print(f'Error creating directory: {device_info.txt_dir}')
            
    filepath = os.path.join(device_info.txt_dir, f'{filename}.txt')
    try:
        with open(filepath, 'w+') as fd:
            fd.writelines('Device voltage (V)\tDevice current (A)\tPhotodetector current (W)\n')
            for i in range(len(voltage_array)):
                fd.write(f'{voltage_array[i]:.5f}\t{current_array[i]}\t{light_array[i]}\n')
    except Exception as e:
        print(f"Failed to save text data: {e}")

    # 2. Plot to PNG
    fig, ax1 = plt.subplots()
    ax2 = ax1.twinx()
    
    # Convert for plotting if necessary (assuming current was in A and light was in W initially)
    # We plot current in mA, light in mW, voltage in V
    plot_current = [i * 1000 for i in current_array]
    plot_light = [l * 1000 for l in light_array]
    
    ax1.set_ylabel('Power per facet (mW)', color='black')
    ax1.set_xlabel('Current (mA)')
    ax2.set_ylabel('Voltage (V)', color='blue')
    
    ax2.plot(plot_current, voltage_array, color='blue', label='I-V Characteristic')
    ax1.plot(plot_current, plot_light, color='black', label='L-I Characteristic')

    plotString = (f'Device Name: {device_info.device_name}\n'
                  f'Test Type: {meas_type.name}\n'
                  f'Temperature (\u00B0C): {device_info.temperature}\n'
                  f'Device Dimensions: {device_info.dimensions} (\u03BCm x \u03BCm)\n'
                  f'Test Structure or Laser: {device_info.test_type}')

    plt.figtext(0.02, 0.02, plotString, fontsize=12)
    plt.subplots_adjust(bottom=0.3)

    if not os.path.exists(device_info.plot_dir):
        try:
            os.makedirs(device_info.plot_dir)
        except Exception:
            print('Error: Creating directory: ' + device_info.plot_dir)

    try:
        plt.savefig(os.path.join(device_info.plot_dir, f'{filename}.png'))
    except Exception as e:
        print(f"Failed to save plot: {e}")
    finally:
        plt.close(fig) # Important to free memory

    # 3. Export to Origin (Using the existing function from dataAnal)
    # export_to_origin expects currents and lights in mA and mW typically,
    # and takes numpy arrays or lists. Let's pass the converted ones.
    export_to_origin(plot_current, voltage_array, plot_light, device_info.device_name)
    
    print(f"Data saved to {filepath} and plot saved.")
