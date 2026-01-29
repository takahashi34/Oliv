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


def save_config(gui_instance, test_type):
    """
    Save the current configuration to a JSON file
    
    Args:
        gui_instance: The GUI class instance containing the entry widgets
        test_type: String identifier for the test type (e.g., 'VPulse_LI', 'CW_IV')
    """
    ensure_config_dir()
    
    # Build configuration dictionary based on test type
    config = {
        'test_type': test_type,
        'version': '1.0'
    }
    
    # Common settings for all tests
    config['directories'] = {
        'plot_dir': get_entry_value(gui_instance.plot_dir_entry),
        'txt_dir': get_entry_value(gui_instance.txt_dir_entry)
    }
    
    config['device'] = {
        'name': get_entry_value(gui_instance.device_name_entry),
        'dimensions': get_entry_value(gui_instance.device_dim_entry),
        'temperature': get_entry_value(gui_instance.device_temp_entry),
        'test_laser': get_var_value(gui_instance.test_laser_button_var)
    }
    
    # Test-specific settings
    if test_type.startswith('VPulse') or test_type.startswith('IPulse'):
        # Pulsed measurement settings
        config['pulse'] = {}
        
        if hasattr(gui_instance, 'step_size_entry'):
            config['pulse']['step_size'] = get_entry_value(gui_instance.step_size_entry)
        if hasattr(gui_instance, 'delay_entry'):
            config['pulse']['delay'] = get_entry_value(gui_instance.delay_entry)
        if hasattr(gui_instance, 'pulse_width_entry'):
            config['pulse']['pulse_width'] = get_entry_value(gui_instance.pulse_width_entry)
        if hasattr(gui_instance, 'frequency_entry'):
            config['pulse']['frequency'] = get_entry_value(gui_instance.frequency_entry)
        if hasattr(gui_instance, 'series_resistance_entry'):
            config['pulse']['series_resistance'] = get_entry_value(gui_instance.series_resistance_entry)
        
        # Voltage-based pulsed tests
        if hasattr(gui_instance, 'start_voltage_entry'):
            config['pulse']['start_voltage'] = get_entry_value(gui_instance.start_voltage_entry)
        if hasattr(gui_instance, 'stop_voltage_entry'):
            config['pulse']['stop_voltage'] = get_entry_value(gui_instance.stop_voltage_entry)
        
        # Current-based pulsed tests
        if hasattr(gui_instance, 'start_current_entry'):
            config['pulse']['start_current'] = get_entry_value(gui_instance.start_current_entry)
        if hasattr(gui_instance, 'stop_current_entry'):
            config['pulse']['stop_current'] = get_entry_value(gui_instance.stop_current_entry)
        if hasattr(gui_instance, 'current_limit_entry'):
            config['pulse']['current_limit'] = get_entry_value(gui_instance.current_limit_entry)
        
        # Instrument settings - addresses
        config['instruments'] = {}
        if hasattr(gui_instance, 'pulse_address'):
            config['instruments']['pulse_address'] = get_var_value(gui_instance.pulse_address)
        if hasattr(gui_instance, 'scope_address'):
            config['instruments']['scope_address'] = get_var_value(gui_instance.scope_address)
        
        # Channel settings
        if hasattr(gui_instance, 'current_channel'):
            config['instruments']['current_channel'] = get_var_value(gui_instance.current_channel)
        if hasattr(gui_instance, 'voltage_channel'):
            config['instruments']['voltage_channel'] = get_var_value(gui_instance.voltage_channel)
        if hasattr(gui_instance, 'light_channel'):
            config['instruments']['light_channel'] = get_var_value(gui_instance.light_channel)
        if hasattr(gui_instance, 'trigger_channel'):
            config['instruments']['trigger_channel'] = get_var_value(gui_instance.trigger_channel)
        
        # Impedance settings
        if hasattr(gui_instance, 'curr_channel_impedance'):
            config['instruments']['curr_channel_impedance'] = get_var_value(gui_instance.curr_channel_impedance)
        if hasattr(gui_instance, 'volt_channel_impedance'):
            config['instruments']['volt_channel_impedance'] = get_var_value(gui_instance.volt_channel_impedance)
        if hasattr(gui_instance, 'light_channel_impedance'):
            config['instruments']['light_channel_impedance'] = get_var_value(gui_instance.light_channel_impedance)
    
    elif test_type.startswith('CW'):
        # CW measurement settings
        config['sweep'] = {}
        
        if hasattr(gui_instance, 'step_size_entry'):
            config['sweep']['step_size'] = get_entry_value(gui_instance.step_size_entry)
        if hasattr(gui_instance, 'num_of_pts_entry'):
            config['sweep']['num_of_pts'] = get_entry_value(gui_instance.num_of_pts_entry)
        if hasattr(gui_instance, 'compliance_entry'):
            config['sweep']['compliance'] = get_entry_value(gui_instance.compliance_entry)
        if hasattr(gui_instance, 'radiobutton_var'):
            config['sweep']['sweep_type'] = get_var_value(gui_instance.radiobutton_var)
        
        # Voltage-based CW tests
        if hasattr(gui_instance, 'start_voltage_entry'):
            config['sweep']['start_voltage'] = get_entry_value(gui_instance.start_voltage_entry)
        if hasattr(gui_instance, 'stop_voltage_entry'):
            config['sweep']['stop_voltage'] = get_entry_value(gui_instance.stop_voltage_entry)
        
        # Current-based CW tests
        if hasattr(gui_instance, 'start_current_entry'):
            config['sweep']['start_current'] = get_entry_value(gui_instance.start_current_entry)
        if hasattr(gui_instance, 'stop_current_entry'):
            config['sweep']['stop_current'] = get_entry_value(gui_instance.stop_current_entry)
        
        # Instrument settings
        config['instruments'] = {}
        if hasattr(gui_instance, 'keithley_address'):
            config['instruments']['keithley_address'] = get_var_value(gui_instance.keithley_address)
        if hasattr(gui_instance, 'keithley1_address'):
            config['instruments']['keithley1_address'] = get_var_value(gui_instance.keithley1_address)
        if hasattr(gui_instance, 'keithley2_address'):
            config['instruments']['keithley2_address'] = get_var_value(gui_instance.keithley2_address)
        if hasattr(gui_instance, 'scope_address'):
            config['instruments']['scope_address'] = get_var_value(gui_instance.scope_address)
        if hasattr(gui_instance, 'osc_address'):
            config['instruments']['osc_address'] = get_var_value(gui_instance.osc_address)
        
        # Channel settings
        if hasattr(gui_instance, 'light_channel'):
            config['instruments']['light_channel'] = get_var_value(gui_instance.light_channel)
        if hasattr(gui_instance, 'channel_impedance'):
            config['instruments']['channel_impedance'] = get_var_value(gui_instance.channel_impedance)
        if hasattr(gui_instance, 'light_channel_impedance'):
            config['instruments']['light_channel_impedance'] = get_var_value(gui_instance.light_channel_impedance)
    
    # Ask user for save location
    default_filename = f"{test_type}_config.json"
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


def load_config(gui_instance, test_type):
    """
    Load a configuration from a JSON file
    
    Args:
        gui_instance: The GUI class instance containing the entry widgets
        test_type: String identifier for the expected test type
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
    
    # Verify test type matches (warn but allow loading)
    if config.get('test_type') != test_type:
        result = messagebox.askyesno(
            'Warning',
            f"Configuration is for '{config.get('test_type')}' but current test is '{test_type}'.\n"
            "Some settings may not apply. Continue loading?"
        )
        if not result:
            return
    
    # Load directories
    if 'directories' in config:
        dirs = config['directories']
        if 'plot_dir' in dirs:
            set_entry_value(gui_instance.plot_dir_entry, dirs['plot_dir'])
        if 'txt_dir' in dirs:
            set_entry_value(gui_instance.txt_dir_entry, dirs['txt_dir'])
    
    # Load device settings
    if 'device' in config:
        dev = config['device']
        if 'name' in dev:
            set_entry_value(gui_instance.device_name_entry, dev['name'])
        if 'dimensions' in dev:
            set_entry_value(gui_instance.device_dim_entry, dev['dimensions'])
        if 'temperature' in dev:
            set_entry_value(gui_instance.device_temp_entry, dev['temperature'])
        if 'test_laser' in dev and hasattr(gui_instance, 'test_laser_button_var'):
            set_var_value(gui_instance.test_laser_button_var, dev['test_laser'])
    
    # Load pulse settings (VPulse/IPulse)
    if 'pulse' in config:
        pulse = config['pulse']
        if 'step_size' in pulse and hasattr(gui_instance, 'step_size_entry'):
            set_entry_value(gui_instance.step_size_entry, pulse['step_size'])
        if 'delay' in pulse and hasattr(gui_instance, 'delay_entry'):
            set_entry_value(gui_instance.delay_entry, pulse['delay'])
        if 'pulse_width' in pulse and hasattr(gui_instance, 'pulse_width_entry'):
            set_entry_value(gui_instance.pulse_width_entry, pulse['pulse_width'])
        if 'frequency' in pulse and hasattr(gui_instance, 'frequency_entry'):
            set_entry_value(gui_instance.frequency_entry, pulse['frequency'])
        if 'series_resistance' in pulse and hasattr(gui_instance, 'series_resistance_entry'):
            set_entry_value(gui_instance.series_resistance_entry, pulse['series_resistance'])
        if 'start_voltage' in pulse and hasattr(gui_instance, 'start_voltage_entry'):
            set_entry_value(gui_instance.start_voltage_entry, pulse['start_voltage'])
        if 'stop_voltage' in pulse and hasattr(gui_instance, 'stop_voltage_entry'):
            set_entry_value(gui_instance.stop_voltage_entry, pulse['stop_voltage'])
        if 'start_current' in pulse and hasattr(gui_instance, 'start_current_entry'):
            set_entry_value(gui_instance.start_current_entry, pulse['start_current'])
        if 'stop_current' in pulse and hasattr(gui_instance, 'stop_current_entry'):
            set_entry_value(gui_instance.stop_current_entry, pulse['stop_current'])
        if 'current_limit' in pulse and hasattr(gui_instance, 'current_limit_entry'):
            set_entry_value(gui_instance.current_limit_entry, pulse['current_limit'])
    
    # Load sweep settings (CW)
    if 'sweep' in config:
        sweep = config['sweep']
        if 'step_size' in sweep and hasattr(gui_instance, 'step_size_entry'):
            set_entry_value(gui_instance.step_size_entry, sweep['step_size'])
        if 'num_of_pts' in sweep and hasattr(gui_instance, 'num_of_pts_entry'):
            set_entry_value(gui_instance.num_of_pts_entry, sweep['num_of_pts'])
        if 'compliance' in sweep and hasattr(gui_instance, 'compliance_entry'):
            set_entry_value(gui_instance.compliance_entry, sweep['compliance'])
        if 'sweep_type' in sweep and hasattr(gui_instance, 'radiobutton_var'):
            set_var_value(gui_instance.radiobutton_var, sweep['sweep_type'])
            # Trigger the appropriate radio button callback
            if sweep['sweep_type'] == 'Lin' and hasattr(gui_instance, 'lin_selected'):
                gui_instance.lin_selected()
            elif sweep['sweep_type'] == 'Log' and hasattr(gui_instance, 'log_selected'):
                gui_instance.log_selected()
            elif sweep['sweep_type'] == 'Linlog' and hasattr(gui_instance, 'linlog_selected'):
                gui_instance.linlog_selected()
        if 'start_voltage' in sweep and hasattr(gui_instance, 'start_voltage_entry'):
            set_entry_value(gui_instance.start_voltage_entry, sweep['start_voltage'])
        if 'stop_voltage' in sweep and hasattr(gui_instance, 'stop_voltage_entry'):
            set_entry_value(gui_instance.stop_voltage_entry, sweep['stop_voltage'])
        if 'start_current' in sweep and hasattr(gui_instance, 'start_current_entry'):
            set_entry_value(gui_instance.start_current_entry, sweep['start_current'])
        if 'stop_current' in sweep and hasattr(gui_instance, 'stop_current_entry'):
            set_entry_value(gui_instance.stop_current_entry, sweep['stop_current'])
    
    # Load instrument settings
    if 'instruments' in config:
        instr = config['instruments']
        # Addresses
        if 'pulse_address' in instr and hasattr(gui_instance, 'pulse_address'):
            set_var_value(gui_instance.pulse_address, instr['pulse_address'])
        if 'scope_address' in instr and hasattr(gui_instance, 'scope_address'):
            set_var_value(gui_instance.scope_address, instr['scope_address'])
        if 'keithley_address' in instr and hasattr(gui_instance, 'keithley_address'):
            set_var_value(gui_instance.keithley_address, instr['keithley_address'])
        if 'keithley1_address' in instr and hasattr(gui_instance, 'keithley1_address'):
            set_var_value(gui_instance.keithley1_address, instr['keithley1_address'])
        if 'keithley2_address' in instr and hasattr(gui_instance, 'keithley2_address'):
            set_var_value(gui_instance.keithley2_address, instr['keithley2_address'])
        if 'osc_address' in instr and hasattr(gui_instance, 'osc_address'):
            set_var_value(gui_instance.osc_address, instr['osc_address'])
        
        # Channels
        if 'current_channel' in instr and hasattr(gui_instance, 'current_channel'):
            set_var_value(gui_instance.current_channel, instr['current_channel'])
        if 'voltage_channel' in instr and hasattr(gui_instance, 'voltage_channel'):
            set_var_value(gui_instance.voltage_channel, instr['voltage_channel'])
        if 'light_channel' in instr and hasattr(gui_instance, 'light_channel'):
            set_var_value(gui_instance.light_channel, instr['light_channel'])
        if 'trigger_channel' in instr and hasattr(gui_instance, 'trigger_channel'):
            set_var_value(gui_instance.trigger_channel, instr['trigger_channel'])
        
        # Impedances
        if 'curr_channel_impedance' in instr and hasattr(gui_instance, 'curr_channel_impedance'):
            set_var_value(gui_instance.curr_channel_impedance, instr['curr_channel_impedance'])
        if 'volt_channel_impedance' in instr and hasattr(gui_instance, 'volt_channel_impedance'):
            set_var_value(gui_instance.volt_channel_impedance, instr['volt_channel_impedance'])
        if 'light_channel_impedance' in instr and hasattr(gui_instance, 'light_channel_impedance'):
            set_var_value(gui_instance.light_channel_impedance, instr['light_channel_impedance'])
        if 'channel_impedance' in instr and hasattr(gui_instance, 'channel_impedance'):
            set_var_value(gui_instance.channel_impedance, instr['channel_impedance'])
    
    messagebox.showinfo('Success', f'Configuration loaded from:\n{filepath}')


def add_config_buttons(gui_instance, parent_frame, test_type, row, column=0):
    """
    Add Save/Load configuration buttons to a GUI frame
    
    Args:
        gui_instance: The GUI class instance
        parent_frame: The tkinter frame to add buttons to
        test_type: String identifier for the test type
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
        command=lambda: save_config(gui_instance, test_type)
    )
    save_button.grid(column=0, row=0, padx=5, pady=5)
    
    load_button = Button(
        config_frame,
        text='Load Config',
        command=lambda: load_config(gui_instance, test_type)
    )
    load_button.grid(column=1, row=0, padx=5, pady=5)
    
    return save_button, load_button
