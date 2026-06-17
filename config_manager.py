"""
Configuration Manager for Laser Measurement Suite
Handles saving and loading test configurations to/from JSON files
"""

import json
import os
from tkinter import filedialog, messagebox

# Default directory for saving configurations
CONFIG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'configs')


def ensure_config_dir():
    """Create the config directory if it doesn't exist"""
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)


def get_entry_value(entry_widget):
    """Safely get value from an Entry widget"""
    try:
        return entry_widget.get()
    except:
        return ""


def get_var_value(var):
    """Safely get value from a StringVar/IntVar"""
    try:
        return var.get()
    except:
        return ""


def set_entry_value(entry_widget, value):
    """Safely set value in an Entry widget"""
    try:
        entry_widget.delete(0, 'end')
        entry_widget.insert(0, str(value))
    except:
        pass


def set_var_value(var, value):
    """Safely set value in a StringVar/IntVar"""
    try:
        var.set(value)
    except:
        pass


def save_config(gui_instance, meas_type_var):
    """
    Save the current configuration to a JSON file
    
    Args:
        gui_instance: The GUI class instance containing the entry widgets
        meas_type_var: String identifier for the test type (e.g., 'Unified_LIV')
    """
    ensure_config_dir()
    
    # Build configuration dictionary based on current GUI state
    config = {
        'meas_type_var': meas_type_var,
        'version': '2.0',
        'source': get_var_value(gui_instance.source_var),
        'regime': get_var_value(gui_instance.regime_var),
        'plot_type': get_var_value(gui_instance.plot_var),
        
        'directories': {
            'plot_dir': get_entry_value(gui_instance.plot_dir_entry),
            'txt_dir': get_entry_value(gui_instance.txt_dir_entry)
        },
        
        'device': {
            'name': get_entry_value(gui_instance.device_name_entry),
            'dimensions': get_entry_value(gui_instance.device_dim_entry),
            'temperature': get_entry_value(gui_instance.device_temp_entry),
            'test_laser': get_var_value(gui_instance.test_laser_var)
        },
        
        'sweep': {
            'start': get_entry_value(gui_instance.start_entry),
            'stop': get_entry_value(gui_instance.stop_entry),
            'step_size': get_entry_value(gui_instance.step_entry),
            'compliance': get_entry_value(gui_instance.compliance_entry),
            'sweep_type': get_var_value(gui_instance.sweep_type_var),
            'num_pts': get_entry_value(gui_instance.num_pts_entry)
        },
        
        'pulse': {
            'pulse_width': get_entry_value(gui_instance.pulse_width_entry),
            'delay': get_entry_value(gui_instance.delay_entry),
            'frequency': get_entry_value(gui_instance.frequency_entry),
            'series_resistance': get_entry_value(gui_instance.series_resistance_entry)
        },
        
        'measurement': {
            'wavelength': get_entry_value(gui_instance.wavelength_entry),
        },

        'instruments': {
            'smu_address': get_var_value(gui_instance.smu_addr_var),
            'pulser_address': get_var_value(gui_instance.pulse_addr_var),
            'osc_address': get_var_value(gui_instance.osc_addr_var),
            'det_address': get_var_value(gui_instance.det_addr_var),
            'tec_address': get_var_value(gui_instance.tec_address),
            'light_mode': get_var_value(gui_instance.light_mode_var),
            'light_channel': get_var_value(gui_instance.light_channel),
            'light_channel_impedance': get_var_value(gui_instance.light_channel_impedance),
            'current_channel': get_var_value(gui_instance.current_channel),
            'curr_channel_impedance': get_var_value(gui_instance.curr_channel_impedance),
            'voltage_channel': get_var_value(gui_instance.voltage_channel),
            'volt_channel_impedance': get_var_value(gui_instance.volt_channel_impedance),
            'trigger_channel': get_var_value(gui_instance.trigger_channel)
        }
    }
    
    # Ask user for save location
    default_filename = f"{meas_type_var}_config.json"
    filepath = filedialog.asksaveasfilename(
        initialdir=CONFIG_DIR,
        initialfile=default_filename,
        defaultextension='.json',
        filetypes=[('JSON files', '*.json'), ('All files', '*.*')],
        title='Save Configuration'
    )
    
    if filepath:
        try:
            with open(filepath, 'w') as f:
                json.dump(config, f, indent=4)
            messagebox.showinfo('Success', f'Configuration saved to:\n{filepath}')
        except Exception as e:
            messagebox.showerror('Error', f'Failed to save configuration:\n{str(e)}')


def load_config(gui_instance, meas_type_var):
    """
    Load a configuration from a JSON file
    
    Args:
        gui_instance: The GUI class instance containing the entry widgets
        meas_type_var: String identifier for the expected test type
    """
    ensure_config_dir()
    
    # Ask user to select file
    filepath = filedialog.askopenfilename(
        initialdir=CONFIG_DIR,
        defaultextension='.json',
        filetypes=[('JSON files', '*.json'), ('All files', '*.*')],
        title='Load Configuration'
    )
    
    if not filepath:
        return
    
    try:
        with open(filepath, 'r') as f:
            config = json.load(f)
    except Exception as e:
        messagebox.showerror('Error', f'Failed to load configuration:\n{str(e)}')
        return
    
    # Load test type if present
    if 'source' in config:
        set_var_value(gui_instance.source_var, config['source'])
    if 'regime' in config:
        set_var_value(gui_instance.regime_var, config['regime'])
    if 'plot_type' in config:
        set_var_value(gui_instance.plot_var, config['plot_type'])
    elif 'measurement_type' in config:
        # Backwards compatibility for older configurations
        old_mode = config['measurement_type']
        if old_mode == 'CW':
            set_var_value(gui_instance.source_var, 'Voltage')
            set_var_value(gui_instance.regime_var, 'Continuous')
        elif old_mode == 'VPULSE':
            set_var_value(gui_instance.source_var, 'Voltage')
            set_var_value(gui_instance.regime_var, 'Pulsed')
        elif old_mode == 'IPULSE':
            set_var_value(gui_instance.source_var, 'Current')
            set_var_value(gui_instance.regime_var, 'Pulsed')            
    
    # Load directories
    if 'directories' in config:
        dirs = config['directories']
        set_entry_value(gui_instance.plot_dir_entry, dirs.get('plot_dir', ''))
        set_entry_value(gui_instance.txt_dir_entry, dirs.get('txt_dir', ''))
    
    # Load device settings
    if 'device' in config:
        dev = config['device']
        set_entry_value(gui_instance.device_name_entry, dev.get('name', ''))
        set_entry_value(gui_instance.device_dim_entry, dev.get('dimensions', ''))
        set_entry_value(gui_instance.device_temp_entry, dev.get('temperature', ''))
        set_var_value(gui_instance.test_laser_var, dev.get('test_laser', 'Laser'))
    
    # Load sweep settings
    if 'sweep' in config:
        sweep = config['sweep']
        set_entry_value(gui_instance.start_entry, sweep.get('start', ''))
        set_entry_value(gui_instance.stop_entry, sweep.get('stop', ''))
        set_entry_value(gui_instance.step_entry, sweep.get('step_size', ''))
        set_entry_value(gui_instance.compliance_entry, sweep.get('compliance', ''))
        set_var_value(gui_instance.sweep_type_var, sweep.get('sweep_type', 'Lin'))
        set_entry_value(gui_instance.num_pts_entry, sweep.get('num_pts', ''))
    
    # Load pulse settings
    if 'pulse' in config:
        pulse = config['pulse']
        set_entry_value(gui_instance.pulse_width_entry, pulse.get('pulse_width', ''))
        set_entry_value(gui_instance.delay_entry, pulse.get('delay', ''))
        set_entry_value(gui_instance.frequency_entry, pulse.get('frequency', ''))
        set_entry_value(gui_instance.series_resistance_entry, pulse.get('series_resistance', ''))

    # Load measurement settings
    if 'measurement' in config:
        meas = config['measurement']
        set_entry_value(gui_instance.wavelength_entry, meas.get('wavelength', ''))
    
    # Load instrument settings
    if 'instruments' in config:
        instr = config['instruments']
        set_var_value(gui_instance.smu_addr_var, instr.get('smu_address', 'Select...'))
        set_var_value(gui_instance.pulse_addr_var, instr.get('pulser_address', 'Select...'))
        set_var_value(gui_instance.osc_addr_var, instr.get('osc_address', 'Select...'))
        set_var_value(gui_instance.det_addr_var, instr.get('det_address', 'Select...'))
        set_var_value(gui_instance.tec_address, instr.get('tec_address', 'Select...'))
        set_var_value(gui_instance.light_mode_var, instr.get('light_mode', 'osc'))
        set_var_value(gui_instance.light_channel, instr.get('light_channel', 1))
        set_var_value(gui_instance.light_channel_impedance, instr.get('light_channel_impedance', '50Ω'))
        set_var_value(gui_instance.current_channel, instr.get('current_channel', 2))
        set_var_value(gui_instance.curr_channel_impedance, instr.get('curr_channel_impedance', '50Ω'))
        set_var_value(gui_instance.voltage_channel, instr.get('voltage_channel', 3))
        set_var_value(gui_instance.volt_channel_impedance, instr.get('volt_channel_impedance', '50Ω'))
        set_var_value(gui_instance.trigger_channel, instr.get('trigger_channel', 3))

    if hasattr(gui_instance, 'change_plot_type'):
        gui_instance.change_plot_type()
    elif hasattr(gui_instance, 'update_dynamic_fields'):
        gui_instance.update_dynamic_fields()
    
    messagebox.showinfo('Success', f'Configuration loaded from:\n{filepath}')


def add_config_buttons(gui_instance, parent_frame, meas_type_var, row, column=0):
    """
    Add Save/Load configuration buttons to a GUI frame
    
    Args:
        gui_instance: The GUI class instance
        parent_frame: The tkinter frame to add buttons to
        meas_type_var: String identifier for the test type
        row: The row to place buttons at
        column: Starting column (default 0)
    
    Returns:
        Tuple of (save_button, load_button)
    """
    from tkinter import Button, LabelFrame
    
    # Create a frame for config buttons
    config_frame = LabelFrame(parent_frame, text='Configuration')
    config_frame.grid(column=column, row=row, columnspan=4, pady=(10, 5), padx=5, sticky='W')
    
    save_button = Button(
        config_frame,
        text='Save Config',
        command=lambda: save_config(gui_instance, meas_type_var)
    )
    save_button.grid(column=0, row=0, padx=5, pady=5)
    
    load_button = Button(
        config_frame,
        text='Load Config',
        command=lambda: load_config(gui_instance, meas_type_var)
    )
    load_button.grid(column=1, row=0, padx=5, pady=5)
    
    return save_button, load_button
