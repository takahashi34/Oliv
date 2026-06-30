import os
import re
from datetime import datetime
import matplotlib.pyplot as plt
from dataAnal import export_to_origin
from core_types import DeviceInfo, MeasurementType

def save_and_plot_data(voltage_array, current_array, light_array, device_info: DeviceInfo, meas_type: MeasurementType, plot_type: str):
    """
    Data analysis block:
    Input: Raw data (voltage, current, light arrays), DeviceInfo cluster, MeasurementType, plot type
    Output: Data to text file, plot to PNG, export data to Origin
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    prefix = meas_type.name.lower()
    
    # Normalize the user-entered dimension
    safe_dimension = ''.join(device_info.dimensions.split())
    safe_dimension = safe_dimension.replace('*', 'x').replace('×', 'x')
    safe_dimension = re.sub(
        r'[<>:"/\\|?*\x00-\x1f]',
        '_',
        safe_dimension
    )
    
    if device_info.temperature != '':
        filename = f'{prefix}_{plot_type}_{device_info.device_name}_{safe_dimension}um_{device_info.temperature}C_{timestamp}'
    else:
        filename = f'{prefix}_{plot_type}_{device_info.device_name}_{safe_dimension}um_{timestamp}'

    # Convert measurement data for plotting and Origin export.
    # Current: A -> mA
    # Light: W -> mW
    # Voltage remains in V.
    plot_current = [value * 1000 for value in current_array]
    plot_light = [value * 1000 for value in light_array]

    # Select the data arrangement for the current plot type.
    if plot_type == 'LI':
        # X: Current, Y: Light
        plot_x_data = plot_current
        plot_y_data = plot_light
        plot_y2_data = None

        plot_x_label = 'Device Current (mA)'
        plot_y_label = 'Light Output (mW)'
        plot_y2_label = None
        
        primary_curve_label = 'L-I Characteristic'
        secondary_curve_label = None

        # TXT keeps the existing raw units: A and W.
        txt_columns = [
            ('Device current (A)', current_array),
            ('Photodetector current (W)', light_array)
        ]

    elif plot_type == 'IV':
        # X: Voltage, Y: Current
        plot_x_data = voltage_array
        plot_y_data = plot_current
        plot_y2_data = None

        plot_x_label = 'Device Voltage (V)'
        plot_y_label = 'Device Current (mA)'
        plot_y2_label = None
        
        primary_curve_label = 'I-V Characteristic'
        secondary_curve_label = None

        txt_columns = [
            ('Device voltage (V)', voltage_array),
            ('Device current (A)', current_array)
        ]

    elif plot_type == 'LIV':
        # X: Current, Y1: Light, Y2: Voltage
        plot_x_data = plot_current
        plot_y_data = plot_light
        plot_y2_data = voltage_array

        plot_x_label = 'Current (mA)'
        plot_y_label = 'Power per facet (mW)'
        plot_y2_label = 'Voltage (V)'
        
        primary_curve_label = 'L-I Characteristic'
        secondary_curve_label = 'I-V Characteristic'

        txt_columns = [
            ('Device current (A)', current_array),
            ('Photodetector current (W)', light_array),
            ('Device voltage (V)', voltage_array)
        ]

    else:
        raise ValueError(f'Unsupported plot type: {plot_type}')

    # 1. Save data to text file
    if not os.path.exists(device_info.txt_dir):
        try:
            os.makedirs(device_info.txt_dir)
        except Exception as e:
            print(f'Error creating directory: {device_info.txt_dir}')
            
    filepath = os.path.join(device_info.txt_dir, f'{filename}.txt')
    try:
        with open(filepath, 'w+') as fd:
            # Write column names.
            headers = []

            for column_name, column_data in txt_columns:
                headers.append(column_name)

            fd.write('\t'.join(headers) + '\n')

            # Write measurement data.
            for i in range(len(voltage_array)):
                row = []

                for column_name, column_data in txt_columns:
                    row.append(str(column_data[i]))

                fd.write('\t'.join(row) + '\n')

    except Exception as e:
        print(f"Failed to save text data: {e}")

    # 2. Plot to PNG
    fig, ax1 = plt.subplots()

    # Primary X and Y axes.
    ax1.set_xlabel(plot_x_label)
    ax1.set_ylabel(plot_y_label, color='black')
    ax1.plot(plot_x_data, plot_y_data, color='black', label=primary_curve_label)

    # Only LIV requires a secondary Voltage axis.
    if plot_y2_data is not None:
        ax2 = ax1.twinx()
        ax2.set_ylabel(plot_y2_label, color='blue')
        ax2.plot(plot_x_data, plot_y2_data, color='blue', label=secondary_curve_label)

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
    export_to_origin(plot_current, voltage_array, plot_light, device_info.device_name, plot_type)
    
    print(f"Data saved to {filepath} and plot saved.")
