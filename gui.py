import tkinter as tk
from tkinter import Label, Entry, Button, LabelFrame, OptionMenu, Radiobutton, StringVar, IntVar, BooleanVar, Checkbutton, DISABLED, NORMAL, font
import pyvisa
import threading
import os
import matplotlib.pyplot as plt
from pyvisa.constants import Parity, StopBits, VI_ASRL_FLOW_NONE

from core_types import InstrumentConfig, SweepParameters, DeviceInfo, MeasurementType, SweepType, LightMode, SafetyLimits
from instruments import initialize_instruments, shutdown_instruments, LDC3724B_TEC, LDT5525B_TEC
from measurement_loop import sweep_and_collect
from data_export import save_and_plot_data
from live_plot import LivePlotLIV, LivePlotIV, LivePlotLI
from Browse_buttons import browse_plot_file, browse_txt_file
from config_manager import add_config_buttons

# Use mock if testing without hardware, or real rm
try:
    from mock_instruments import get_resource_manager
    rm = get_resource_manager()
except ImportError:
    rm = pyvisa.ResourceManager()

class UnifiedMeasurementGUI:
    def __init__(self, master):
        self.master = master
        self.master.title('Olms Laser Measurement Suite')
        
        self.tec = None
        self.tec_output_enabled = False
        
        self.measurement_running = False
        
        def_font = font.nametofont("TkDefaultFont")
        helv36 = font.Font(family="MS PGothic", size=10)
        self.master.option_add("*Font", helv36)

        self.master.columnconfigure(0, weight=1)
        self.master.columnconfigure(1, weight=1)
        self.master.rowconfigure(1, weight=1)
        self.master.rowconfigure(2, weight=1)

        # Mode Selection Frame
        self.modeFrame = LabelFrame(self.master, text='Measurement Type')
        self.modeFrame.grid(column=0, row=0, columnspan=2, sticky='EW', padx=5, pady=5)
        
        Label(self.modeFrame, text='Source:').grid(row=0, column=0, padx=(10, 2))
        self.source_var = StringVar(value='Voltage')
        self.source_menu = OptionMenu(self.modeFrame, self.source_var, 'Voltage', 'Current', command=self.update_dynamic_fields)
        self.source_menu.grid(row=0, column=1, padx=(0, 10))

        Label(self.modeFrame, text='Regime:').grid(row=0, column=2, padx=(10, 2))
        self.regime_var = StringVar(value='Continuous')
        self.regime_menu = OptionMenu(self.modeFrame, self.regime_var, 'Continuous', 'Pulsed', command=self.update_dynamic_fields)
        self.regime_menu.grid(row=0, column=3, padx=(0, 10))

        Label(self.modeFrame, text='Plot:').grid(row=0, column=4, padx=(10, 2))
        self.plot_var = StringVar(value='LIV')
        self.plot_menu = OptionMenu(self.modeFrame, self.plot_var, 'LIV', 'IV', 'LI', command=self.change_plot_type)
        self.plot_menu.grid(row=0, column=5, padx=(0, 10))

        # Build Frames
        self.build_sweep_settings_frame()
        self.build_device_settings_frame()
        self.build_instrument_settings_frame()
        self.build_plot_frame()
        
        # Trigger initial state update
        self.update_dynamic_fields()
        
        # Start TEC readback 
        self.update_tec_readback()

    def log_selected(self):
        self.num_pts_entry.config(state=NORMAL)
        self.step_entry.config(state=DISABLED)

    def lin_selected(self):
        self.num_pts_entry.config(state=DISABLED)
        self.step_entry.config(state=NORMAL)

    def refresh_instruments(self):
        try:
            addresses = list(rm.list_resources())
        except Exception as e:
            print(f"Error while refreshing instruments: {e}")
            addresses = []

        if addresses:
            source_options  = ['Select...'] + addresses
            detector_options = ['Select...', 'None (IV)'] + addresses
            tec_options = ['Select...'] + addresses
            osc_options = ['Select...'] + addresses
        else:
            source_options  = ['Select...', 'No devices detected']
            detector_options = ['Select...', 'None (IV)', 'No devices detected']
            tec_options = ['Select...', 'None']
            osc_options = ['Select...', 'None']

        # Update SMU menu
        self.smu_menu['menu'].delete(0, 'end')
        for addr in source_options :
            self.smu_menu['menu'].add_command(
                label=addr,
                command=lambda value=addr: self.smu_addr_var.set(value)
            )

        # Update Pulser menu
        self.pulse_menu['menu'].delete(0, 'end')
        for addr in source_options :
            self.pulse_menu['menu'].add_command(
                label=addr,
                command=lambda value=addr: self.pulse_addr_var.set(value)
            )

        # Update Detector menu
        self.det_menu['menu'].delete(0, 'end')
        for addr in detector_options:
            self.det_menu['menu'].add_command(
                label=addr,
                command=lambda value=addr: self.det_addr_var.set(value)
            )

        # Update oscilloscope menu
        self.osc_menu['menu'].delete(0, 'end')
        for addr in osc_options:
            self.osc_menu['menu'].add_command(
                label=addr,
                command=lambda value=addr: self.osc_addr_var.set(value)
            )                           

        # Update TEC menu
        self.tec_menu['menu'].delete(0, 'end')
        for addr in tec_options:
            self.tec_menu['menu'].add_command(
                label=addr,
                command=lambda value=addr: self.tec_address.set(value)
            )

        # After refreshing, reset selections to 'Select...'
        self.smu_addr_var.set('Select...')
        self.pulse_addr_var.set('Select...')
        self.det_addr_var.set('Select...')
        self.osc_addr_var.set('Select...')
        self.tec_address.set('Select...')

    def build_sweep_settings_frame(self):
        self.setFrame = LabelFrame(self.master, text='Sweep Settings')
        self.setFrame.grid(column=0, row=1, sticky='NSEW', padx=5, pady=5)
        for c in range(4): self.setFrame.columnconfigure(c, weight=1)
        
        # Directories
        Label(self.setFrame, text='Plot file dir:').grid(row=0, column=0, sticky='W')
        self.plot_dir_entry = Entry(self.setFrame, width=20)
        self.plot_dir_entry.grid(row=0, column=1, columnspan=2, sticky='W')
        Button(self.setFrame, text='Browse', command=lambda: browse_plot_file(self)).grid(row=0, column=3)

        Label(self.setFrame, text='Text file dir:').grid(row=1, column=0, sticky='W')
        self.txt_dir_entry = Entry(self.setFrame, width=20)
        self.txt_dir_entry.grid(row=1, column=1, columnspan=2, sticky='W')
        Button(self.setFrame, text='Browse', command=lambda: browse_txt_file(self)).grid(row=1, column=3)

        # Base Sweep fields
        self.start_label = Label(self.setFrame, text='Start')
        self.start_label.grid(row=2, column=0, sticky='W')
        self.start_entry = Entry(self.setFrame, width=8)
        self.start_entry.grid(row=2, column=1, sticky='W')

        self.stop_label = Label(self.setFrame, text='Stop')
        self.stop_label.grid(row=2, column=2, sticky='W')
        self.stop_entry = Entry(self.setFrame, width=8)
        self.stop_entry.grid(row=2, column=3, sticky='W')

        self.step_label = Label(self.setFrame, text='Step Size')
        self.step_label.grid(row=3, column=0, sticky='W')
        self.step_entry = Entry(self.setFrame, width=8)
        self.step_entry.grid(row=3, column=1, sticky='W')

        self.compliance_label = Label(self.setFrame, text='Compliance/Limit')
        self.compliance_label.grid(row=3, column=2, sticky='W')
        self.compliance_entry = Entry(self.setFrame, width=8)
        self.compliance_entry.grid(row=3, column=3, sticky='W')

        # Pulsed fields
        self.pulse_width_label = Label(self.setFrame, text='Pulse Width (us)')
        self.pulse_width_entry = Entry(self.setFrame, width=8)
        self.delay_label = Label(self.setFrame, text='Delay (ms)')
        self.delay_entry = Entry(self.setFrame, width=8)
        
        self.frequency_label = Label(self.setFrame, text='Frequency (kHz)')
        self.frequency_entry = Entry(self.setFrame, width=8)
        
        self.series_res_label = Label(self.setFrame, text='Series Res (Ω)')
        self.series_resistance_entry = Entry(self.setFrame, width=8)

        self.glitch_label = Label(self.setFrame, text='Glitch Pts (V)')
        self.glitch_entry = Entry(self.setFrame, width=15)
        self.glitch_entry.insert(0, "7.12, 21.6, 68")


        # Sweep Type (Lin/Log)
        self.sweep_type_var = StringVar(value='Lin') # Default mode: Lin Mode
        self.lin_radio = Radiobutton(self.setFrame, text='Lin', variable=self.sweep_type_var, command=self.lin_selected, value='Lin')
        self.lin_radio.grid(row=6, column=0, sticky='W')
        self.log_radio = Radiobutton(self.setFrame, text='Log', variable=self.sweep_type_var, command=self.log_selected, value='Log')
        self.log_radio.grid(row=6, column=1, sticky='W')

        # # of points for Log sweep
        self.num_pts_label = Label(self.setFrame, text='# of pts')
        self.num_pts_label.grid(row=6, column=2, sticky='W')
        self.num_pts_entry = Entry(self.setFrame, width=8)
        self.num_pts_entry.grid(row=6, column=3, sticky='W')
        
        self.lin_selected() # Default mode: Lin Mode

        # Buttons
        self.startButton = Button(self.setFrame, text='Start', command=self.start_measurement, bg='lightgreen')
        self.startButton.grid(row=7, column=2, pady=10)
        
        self.stopButton = Button(self.setFrame, text='Stop', command=self.stop_measurement, bg='salmon')
        self.stopButton.grid(row=7, column=3, pady=10)
        
        self.refreshButton = Button(self.setFrame, text='Refresh', command=self.refresh_instruments, bg='lightblue')
        self.refreshButton.grid(row=7, column=1, pady=10)
        
        self.clearButton = Button(self.setFrame, text='Clear', command=self.clear_live_plot, bg='lightyellow')
        self.clearButton.grid(row=8, column=3, pady=10)

    def build_device_settings_frame(self):
        self.devFrame = LabelFrame(self.master, text='Device Settings & Config')
        self.devFrame.grid(column=1, row=0, rowspan=2, sticky='NSEW', padx=5, pady=5)
        for c in range(2): self.devFrame.columnconfigure(c, weight=1)
        
        Label(self.devFrame, text='Device name:').grid(row=0, column=0, sticky='W')
        self.device_name_entry = Entry(self.devFrame, width=15)
        self.device_name_entry.grid(row=0, column=1)

        Label(self.devFrame, text='Dimensions (um):').grid(row=1, column=0, sticky='W')
        self.device_dim_entry = Entry(self.devFrame, width=15)
        self.device_dim_entry.grid(row=1, column=1)

        self.test_laser_var = StringVar(value='Laser')
        Radiobutton(self.devFrame, text='Laser', variable=self.test_laser_var, value='Laser').grid(row=2, column=0)
        Radiobutton(self.devFrame, text='Test Structure', variable=self.test_laser_var, value='TestStructure').grid(row=2, column=1)

        # Config buttons from original
        add_config_buttons(self, self.devFrame, 'Unified_LIV', row=3)

        self.build_tec_frame()

    def build_tec_frame(self):
        self.tecFrame = LabelFrame(self.devFrame, text='TEC')
        self.tecFrame.grid(column=0, columnspan=2, row=4, sticky='NSEW', pady=(5, 0))
        
        Label(self.tecFrame, text='TEC address').grid(row=0, column=0, sticky='W')
        self.tec_address = StringVar(value='Select...')
        addresses = list(rm.list_resources()) if list(rm.list_resources()) else ['None']
        self.tec_menu = OptionMenu(self.tecFrame, self.tec_address, *(addresses + ['Select...']))
        self.tec_menu.grid(row=0, column=1)

        Label(self.tecFrame, text='Temp. to Set (°C)').grid(row=1, column=0, sticky='W')
        self.device_temp_entry = Entry(self.tecFrame, width=6)
        self.device_temp_entry.grid(row=1, column=1)
        
        self.tec_status = Label(self.tecFrame, text='Current: --- °C')
        self.tec_status.grid(row=2, column=0, columnspan=2)
        
        Label(self.tecFrame, text='Gain').grid(row=0, column=2)
        self.tec_gain_var = StringVar(value='300')
        gain_options = ('1', '3', '10', '30', '100', '300')
        self.tec_gain_menu = OptionMenu(self.tecFrame, self.tec_gain_var, *gain_options, command=self.set_tec_gain)
        self.tec_gain_menu.grid(row=0, column=3)

        Button(self.tecFrame, text='Send Temp.', command=self.set_tec_temp).grid(row=3, column=0)
        Button(self.tecFrame, text='Toggle Output', command=self.toggle_tec).grid(row=3, column=1)

    """
    def init_tec(self); def set_tec_temp(self);  def toggle_tec(self); def update_tec_readback(self); set_tec_gain
    These five functions are used to control the TEC from the GUI.
    """
    # init_tec(): initializes the TEC connection only when it is first needed.
    def init_tec(self):
        if hasattr(self, 'tec') and self.tec is not None:
            return

        address = self.tec_address.get()

        if address == 'Select...' or address == 'None':
            self.tec_model = 'No TEC selected'
            self.update_dynamic_fields()
            return

        try:
            if address.startswith("ASRL"):
                self.tec = LDT5525B_TEC(rm, address)
                self.tec_model = 'LDT-5525B'

            elif address.startswith("GPIB"):
                self.tec = LDC3724B_TEC(rm, address)
                self.tec_model = 'LDC-3724B'

            else:
                self.tec_model = 'Unknown TEC address'
                self.update_dynamic_fields()
                return

        except Exception as e:
            self.tec = None
            self.tec_model = 'TEC init error'
            self.tec_status.config(text=f'TEC init error: {e}')
            print(f"TEC initialization failed: {e}")            

        if hasattr(self, 'tec_gain_var') and self.tec is not None:
            self.tec.set_gain(self.tec_gain_var.get())

        self.update_dynamic_fields()

    # set_tec_temp() reads the target temperature from the GUI entry box, sends it to the TEC, and turns the TEC output on.
    def set_tec_temp(self):
        self.init_tec()
        if self.tec is None:
            return

        temp = float(self.device_temp_entry.get())
        self.tec.set_temperature(temp)
        self.tec.output_on()

    # toggle_tec() switches the TEC output between ON and OFF based on its current state.
    def toggle_tec(self):
        self.init_tec()
        if self.tec is None:
            return

        if self.tec_output_enabled:
            self.tec.output_off()
            self.tec_output_enabled = False
            self.tec_status.config(text='TEC output off')
        else:
            self.tec.output_on()
            self.tec_output_enabled = True
            self.tec_status.config(text='TEC output on')

    # set_tec_gain: Set gain of current temperature controller 
    def set_tec_gain(self, *args):
        gain = self.tec_gain_var.get()
        self.init_tec()
        if self.tec is None:
            return
        self.tec.set_gain(gain)

    # update_tec_readback() periodically reads the current TEC temperature and updates the GUI display.
    def update_tec_readback(self):
        if hasattr(self, 'tec') and self.tec is not None:
            try:
                t = self.tec.get_temperature()
                self.tec_status.config(text=f'Current: {t:.2f} °C')
            except Exception:
                self.tec_status.config(text='TEC read error')

        self.master.after(1000, self.update_tec_readback)        

    def build_instrument_settings_frame(self):
        self.instFrame = LabelFrame(self.master, text='Instrument Settings')
        self.instFrame.grid(column=0, row=2, columnspan=2, sticky='NSEW', padx=5, pady=5)
        
        addresses = list(rm.list_resources()) if list(rm.list_resources()) else ['No devices detected']
        
        self.smu_label = Label(self.instFrame, text='SMU Address:')
        self.smu_label.grid(row=0, column=0, sticky='W')
        self.smu_addr_var = StringVar(value='Select...')
        self.smu_menu = OptionMenu(self.instFrame, self.smu_addr_var, *addresses)
        self.smu_menu.grid(row=0, column=1)

        self.pulse_label = Label(self.instFrame, text='Pulser Address:')
        self.pulse_addr_var = StringVar(value='Select...')
        self.pulse_menu = OptionMenu(self.instFrame, self.pulse_addr_var, *addresses)
        
        self.det_addr_label = Label(self.instFrame, text='Detector Address:')
        self.det_addr_label.grid(row=1, column=0, sticky='W')
        self.det_addr_var = StringVar(value='Select...')
        self.det_menu = OptionMenu(self.instFrame, self.det_addr_var, *addresses)
        self.det_menu.grid(row=1, column=1)

        self.osc_addr_var_label = Label(self.instFrame, text='Oscilloscope Address:')
        self.osc_addr_var_label.grid(row=2, column=3, sticky='W')
        self.osc_addr_var = StringVar(value='Select...')
        self.osc_menu = OptionMenu(self.instFrame, self.osc_addr_var, *addresses)
        self.osc_menu.grid(row=2, column=4)  
        
        # Build a frame for thermopile to obtain wavelength
        self.thermoFrame = LabelFrame(self.instFrame, text='Thermopile')
        self.thermoFrame.grid(row=0, column=3, rowspan=2, sticky='NW', padx=(35, 5), pady=0,ipadx=20)
        
        Label(self.thermoFrame, text='Wavelength (nm)').grid(row=0, column=3, sticky='W')
        self.wavelength_entry = Entry(self.thermoFrame, width=10)
        self.wavelength_entry.grid(row=0, column=4, sticky='W')

        # Light Mode Radiobuttons
        self.light_mode_var = StringVar(value='osc')
        self.thermo_radio = Radiobutton(self.instFrame, text='Thermo', variable=self.light_mode_var, value='thermo', command=self.update_dynamic_fields)
        self.thermo_radio.grid(row=2, column=0)
        self.scope_radio = Radiobutton(self.instFrame, text='Scope', variable=self.light_mode_var, value='osc', command=self.update_dynamic_fields)
        self.scope_radio.grid(row=2, column=1)
        self.sourcemeter_radio = Radiobutton(self.instFrame, text='SourceMeter', variable=self.light_mode_var, value='SourceMeter', command=self.update_dynamic_fields)
        self.sourcemeter_radio.grid(row=2, column=2)

        # Channels Frame
        self.chanFrame = tk.Frame(self.instFrame)
        self.chanFrame.grid(row=3, column=0, columnspan=3, sticky='EW', pady=5)
        
        channels = [1, 2, 3, 4]
        impedance = ['50Ω', '1MΩ']
        
        # Light Channel
        self.light_chan_label = Label(self.chanFrame, text='Light Ch')
        self.light_chan_label.grid(row=0, column=0)
        self.light_channel = IntVar(value=1)
        self.light_chan_menu = OptionMenu(self.chanFrame, self.light_channel, *channels)
        self.light_chan_menu.grid(row=1, column=0)
        self.light_channel_impedance = StringVar(value='50Ω')
        self.light_impedance_menu = OptionMenu(self.chanFrame, self.light_channel_impedance, *impedance)
        self.light_impedance_menu.grid(row=2, column=0)

        # Current Channel
        self.curr_chan_lbl = Label(self.chanFrame, text='Curr Ch')
        self.current_channel = IntVar(value=2)
        self.curr_chan_menu = OptionMenu(self.chanFrame, self.current_channel, *channels)
        self.curr_channel_impedance = StringVar(value='50Ω')
        self.curr_imp_menu = OptionMenu(self.chanFrame, self.curr_channel_impedance, *impedance)

        # Voltage Channel
        self.volt_chan_lbl = Label(self.chanFrame, text='Volt Ch')
        self.voltage_channel = IntVar(value=3)
        self.volt_chan_menu = OptionMenu(self.chanFrame, self.voltage_channel, *channels)
        self.volt_channel_impedance = StringVar(value='50Ω')
        self.volt_imp_menu = OptionMenu(self.chanFrame, self.volt_channel_impedance, *impedance)

        # Trigger Channel
        self.trig_chan_lbl = Label(self.chanFrame, text='Trig Ch')
        self.trigger_channel = IntVar(value=3)
        self.trig_chan_menu = OptionMenu(self.chanFrame, self.trigger_channel, *channels)

    # create_live_plot: generates the live plot based on current plot type
    def create_live_plot(self):
        if hasattr(self, 'live_plot') and self.live_plot is not None:
            self.live_plot.frame.destroy()

        plot_type = self.plot_var.get()

        if plot_type == 'LI':
            self.live_plot = LivePlotLI(self.plotFrame)
        elif plot_type == 'IV':
            self.live_plot = LivePlotIV(self.plotFrame)
        else:
            self.live_plot = LivePlotLIV(self.plotFrame)

    def build_plot_frame(self):
        self.plotFrame = LabelFrame(self.master, text='Live Plot')
        self.plotFrame.grid(column=0, row=3, columnspan=2, sticky='NSEW', padx=5, pady=5)
        self.master.rowconfigure(3, weight=3)
        self.plotFrame.rowconfigure(0, weight=1)
        self.plotFrame.columnconfigure(0, weight=1)
        self.create_live_plot()

    # change_plot_type: updates the live plot while plot type changed
    def change_plot_type(self, *args):
        self.create_live_plot()
        self.update_dynamic_fields()

    # add_live_measurement_point: adds the measurement data points into plot based on plot type
    def add_live_measurement_point(self, curr, light, volt):
        plot_type = self.plot_var.get()

        if plot_type == 'LI':
            self.live_plot.add_point(curr, light)
        elif plot_type == 'IV':
            self.live_plot.add_point(volt, curr)
        else:
            self.live_plot.add_point(curr, light, volt)

    # clear_live_plot: Call 'clear_all_runs' in live_plot.py to clear all runs and reset live plot
    def clear_live_plot(self):
        """Clear all runs from the live plot when no measurement is running."""
        if self.measurement_running:
            print("Cannot clear live plot while a measurement is running.")
            return

        self.live_plot.clear_all_runs()

    def get_current_mode(self):
        source = self.source_var.get()
        regime = self.regime_var.get()
        if regime == 'Continuous':
            return 'CW_VOLTAGE' if source == 'Voltage' else 'CW_CURRENT'
        else:
            return 'VPULSE' if source == 'Voltage' else 'IPULSE'

    def update_dynamic_fields(self, *args):
        mode = self.get_current_mode()
        is_IV_plot_Type = self.plot_var.get() == 'IV'
        is_pulse_mode = mode in ('VPULSE', 'IPULSE')

        if hasattr(self, 'tecFrame') and hasattr(self, 'tec_model'):
            self.tecFrame.config(text=f'TEC - {self.tec_model}')
        
        if mode in ('CW_VOLTAGE', 'CW_CURRENT'):
            if mode == 'CW_VOLTAGE':
                self.start_label.config(text='Start (V)')
                self.stop_label.config(text='Stop (V)')
                self.step_label.config(text='Step Size (mV)')
                self.compliance_label.config(text='Compliance (mA)')
                self.compliance_entry.config(state=NORMAL)
            else:
                self.start_label.config(text='Start (mA)')
                self.stop_label.config(text='Stop (mA)')
                self.step_label.config(text='Step Size (mA)')
                self.compliance_label.config(text='Compliance (V)')
                self.compliance_entry.config(state=NORMAL)
            
            # Hide pulsed fields
            self.pulse_width_label.grid_remove()
            self.pulse_width_entry.grid_remove()
            self.delay_label.grid_remove()
            self.delay_entry.grid_remove()
            self.frequency_label.grid_remove()
            self.frequency_entry.grid_remove()
            self.series_res_label.grid_remove()
            self.series_resistance_entry.grid_remove()
            self.glitch_label.grid_remove()
            self.glitch_entry.grid_remove()
            
            # Show SMU, hide Pulser
            self.pulse_label.grid_remove()
            self.pulse_menu.grid_remove()
            self.smu_label.grid(row=0, column=0, sticky='W')
            self.smu_menu.grid(row=0, column=1)

            # Hide oscilloscope selection
            self.osc_addr_var_label.grid_remove()
            self.osc_menu.grid_remove()

            # Hide extra channels
            self.curr_chan_lbl.grid_remove(); self.curr_chan_menu.grid_remove(); self.curr_imp_menu.grid_remove()
            self.volt_chan_lbl.grid_remove(); self.volt_chan_menu.grid_remove(); self.volt_imp_menu.grid_remove()
            self.trig_chan_lbl.grid_remove(); self.trig_chan_menu.grid_remove()
            
            # Ajust Buttons (Continuous Wsve) 
            self.refreshButton.grid(row=7, column=1, sticky='', padx=0, pady=10)
            self.startButton.grid(row=7, column=2, sticky='', padx=0, pady=10)
            self.stopButton.grid(row=7, column=3, sticky='', padx=0, pady=10)

        elif mode == 'VPULSE':
            self.start_label.config(text='Start (V)')
            self.stop_label.config(text='Stop (V)')
            self.step_label.config(text='Step Size (mV)')
            self.compliance_label.config(text='Compliance (mA)') # Not heavily used in AVTECH
            self.compliance_entry.config(state=DISABLED)
            
            # Show pulsed fields
            self.pulse_width_label.grid(row=4, column=0, sticky='W')
            self.pulse_width_entry.grid(row=4, column=1, sticky='W')
            self.delay_label.grid(row=4, column=2, sticky='W')
            self.delay_entry.grid(row=4, column=3, sticky='W')
            self.frequency_label.grid(row=5, column=0, sticky='W')
            self.frequency_entry.grid(row=5, column=1, sticky='W')
            self.series_res_label.grid(row=5, column=2, sticky='W')
            self.series_resistance_entry.grid(row=5, column=3, sticky='W')
            self.glitch_label.grid(row=7, column=0, sticky='W')
            self.glitch_entry.grid(row=7, column=1, sticky='W')

            # Show Pulser, hide SMU
            self.smu_label.grid_remove()
            self.smu_menu.grid_remove()
            self.pulse_label.grid(row=0, column=0, sticky='W')
            self.pulse_menu.grid(row=0, column=1)
            
            # Show all channels
            self.curr_chan_lbl.grid(row=0, column=1); self.curr_chan_menu.grid(row=1, column=1); self.curr_imp_menu.grid(row=2, column=1)
            self.volt_chan_lbl.grid(row=0, column=2); self.volt_chan_menu.grid(row=1, column=2); self.volt_imp_menu.grid(row=2, column=2)
            self.trig_chan_lbl.grid(row=0, column=3); self.trig_chan_menu.grid(row=1, column=3)
            
            # Ajust Buttons (Voltage Pulse)
            self.refreshButton.grid(row=7, column=2, sticky='W', pady=10)
            self.startButton.grid(row=7, column=2, sticky='E', pady=10)
            self.stopButton.grid(row=7, column=3, sticky='E', pady=10)
            
            if self.light_mode_var.get() == "thermo":
                self.osc_addr_var_label.grid(row=2, column=3, sticky='E')
                self.osc_menu.grid(row=2, column=4)
            else:
                self.osc_addr_var_label.grid_remove()
                self.osc_menu.grid_remove()

        elif mode == 'IPULSE':
            self.start_label.config(text='Start (mA)')
            self.stop_label.config(text='Stop (mA)')
            self.step_label.config(text='Step Size (mA)')
            self.compliance_label.config(text='Limit (V)')
            self.compliance_entry.config(state=NORMAL)
            
            # Show pulsed fields
            self.pulse_width_label.grid(row=4, column=0, sticky='W')
            self.pulse_width_entry.grid(row=4, column=1, sticky='W')
            self.delay_label.grid(row=4, column=2, sticky='W')
            self.delay_entry.grid(row=4, column=3, sticky='W')
            self.frequency_label.grid_remove()
            self.frequency_entry.grid_remove()
            self.series_res_label.grid_remove()
            self.series_resistance_entry.grid_remove()
            self.glitch_label.grid_remove()
            self.glitch_entry.grid_remove()

            # Show Pulser
            self.smu_label.grid_remove()
            self.smu_menu.grid_remove()
            self.pulse_label.grid(row=0, column=0, sticky='W')
            self.pulse_menu.grid(row=0, column=1)

            # Show all channels
            self.curr_chan_lbl.grid(row=0, column=1); self.curr_chan_menu.grid(row=1, column=1); self.curr_imp_menu.grid(row=2, column=1)
            self.volt_chan_lbl.grid(row=0, column=2); self.volt_chan_menu.grid(row=1, column=2); self.volt_imp_menu.grid(row=2, column=2)
            self.trig_chan_lbl.grid(row=0, column=3); self.trig_chan_menu.grid(row=1, column=3)

            # Ajust Buttons (Current Pulse) 
            self.refreshButton.grid(row=7, column=1, sticky='', padx=0, pady=10)
            self.startButton.grid(row=7, column=2, sticky='', padx=0, pady=10)
            self.stopButton.grid(row=7, column=3, sticky='', padx=0, pady=10)  

            if self.light_mode_var.get() == "thermo":
                self.osc_addr_var_label.grid(row=2, column=3, sticky='E')
                self.osc_menu.grid(row=2, column=4)
            else:
                self.osc_addr_var_label.grid_remove()
                self.osc_menu.grid_remove()
        
        # Modify GUI while selecting 'IV' Plot type
        if is_IV_plot_Type:
            # IV plot does not need: light detector address / light mode radio button / light channels
            self.det_addr_label.grid_remove()
            self.det_menu.grid_remove()

            self.thermo_radio.grid_remove()
            self.scope_radio.grid_remove()
            self.sourcemeter_radio.grid_remove()
            self.thermoFrame.grid_remove()

            self.light_chan_label.grid_remove()
            self.light_chan_menu.grid_remove()
            self.light_impedance_menu.grid_remove()

            # Pulsed IV still needs an oscilloscope address to connect osc and read current/voltage
            if is_pulse_mode:
                self.osc_addr_var_label.grid(row=1, column=0, sticky='E')
                self.osc_menu.grid(row=1, column=1)
            else:
                self.osc_addr_var_label.grid_remove()
                self.osc_menu.grid_remove()

        else:
            # 'LI/LIV' plot types need light detector address to connect detector
            self.det_addr_label.grid(row=1, column=0, sticky='W')
            self.det_menu.grid(row=1, column=1)

            self.thermo_radio.grid(row=2, column=0)
            self.scope_radio.grid(row=2, column=1)
            self.sourcemeter_radio.grid(row=2, column=2)

            self.thermoFrame.grid(row=0, column=3, rowspan=2, sticky='NW', padx=(35, 5), pady=0, ipadx=20)

            self.light_chan_label.grid(row=0, column=0)
            self.light_chan_menu.grid(row=1, column=0)
            self.light_impedance_menu.grid(row=2, column=0)

    def stop_measurement(self):
        self.is_stopped = True
        
    # measurement_finished: Restore the GUI Button after the measurement thread has finished.
    def measurement_finished(self):
        self.measurement_running = False
        self.startButton.config(state=NORMAL, bg='lightgreen', text='Start')
        self.clearButton.config(state=NORMAL, bg='lightyellow', text ='Clear')

    def start_measurement(self):
        """
        Workflow after the Start button is clicked:

        1. Prevent a second measurement from starting if one is already running.
        2. Read the current GUI settings and convert them into:
           - InstrumentConfig
           - SweepParameters
           - DeviceInfo
           - SafetyLimits
        3. Create a new run with start_new_run().
           Previous runs remain visible on the live plot.
        4. Start measurement_thread() in the background so the GUI stays responsive.
           Main Thread: Update GUI; Measurement thread: Perform measurement
        5. Inside measurement_thread():
           - initialize_instruments() connects/configures instruments
           - sweep_and_collect() performs the measurement sweep
           - update_plot() sends each measured point back to the Tkinter main thread
           - add_live_measurement_point() updates the live plot
           - save_and_plot_data() saves TXT/PNG data and exports to Origin
        6. Whether the measurement finishes normally, stops, or raises an error:
           - shutdown_instruments() is called
           - measurement_finished() restores the Start/Clear buttons
        """
        
        # Prevent multiple measurements from running at the same time.
        if self.measurement_running:
            print("A measurement is currently running.")
            return
        
        self.is_stopped = False
        
        mode_str = self.get_current_mode()
        meas_type = MeasurementType[mode_str]
        is_IV_plot_Type = self.plot_var.get() == 'IV'

        # Gather Config
        # light_mode will be assigned as 'None' under 'IV' plot type to create osc via osc_address
        # In 'instruments.py', the osc will be created via det_address when light mode is oscilloscope
        # Else, the osc will be created via osc_address
        config = InstrumentConfig(
            smu_address=self.smu_addr_var.get(),
            det_address=self.det_addr_var.get(),
            osc_address=self.osc_addr_var.get(),
            pulser_address=self.pulse_addr_var.get(),
            tec_address=self.tec_address.get(),
            light_mode=LightMode.NONE if is_IV_plot_Type or self.light_mode_var.get() == 'None (IV)' else LightMode(self.light_mode_var.get()),
            light_channel=self.light_channel.get(),
            light_channel_impedance=self.light_channel_impedance.get(),
            volt_channel=self.voltage_channel.get(),
            volt_channel_impedance=self.volt_channel_impedance.get(),
            curr_channel=self.current_channel.get(),
            curr_channel_impedance=self.curr_channel_impedance.get(),
            trigger_channel=self.trigger_channel.get(),
            thermopile_wavelength=self.wavelength_entry.get()
        )

        def safe_float(s):
            try: return float(s)
            except: return 0.0

        st_map = {'Lin': SweepType.LINEAR, 'Log': SweepType.LOGARITHMIC}
        
        # Scaling logic
        if mode_str == 'CW_VOLTAGE':
            start_val = safe_float(self.start_entry.get())
            stop_val = safe_float(self.stop_entry.get())
            step_size = safe_float(self.step_entry.get()) / 1000.0
            comp_val = safe_float(self.compliance_entry.get()) / 1000.0
        elif mode_str == 'CW_CURRENT':
            start_val = safe_float(self.start_entry.get()) / 1000.0
            stop_val = safe_float(self.stop_entry.get()) / 1000.0
            step_size = safe_float(self.step_entry.get()) / 1000.0
            comp_val = safe_float(self.compliance_entry.get())
        elif mode_str == 'VPULSE':
            start_val = safe_float(self.start_entry.get())
            stop_val = safe_float(self.stop_entry.get())
            step_size = safe_float(self.step_entry.get()) / 1000.0   # Add /1000.0 to convert mV to V
            comp_val = safe_float(self.compliance_entry.get()) / 1000.0
        elif mode_str == 'IPULSE':
            start_val = safe_float(self.start_entry.get()) / 1000.0
            stop_val = safe_float(self.stop_entry.get()) / 1000.0
            step_size = safe_float(self.step_entry.get()) / 1000.0   # Add /1000.0 to convert mA to A
            comp_val = safe_float(self.compliance_entry.get())
        
        try:
            glitch_pts_str = self.glitch_entry.get()
            glitch_pts = [float(x.strip()) for x in glitch_pts_str.split(',') if x.strip()]
        except:
            glitch_pts = []

        params = SweepParameters(
            sweep_type=st_map.get(self.sweep_type_var.get(), SweepType.LINEAR),
            start_val=start_val,
            stop_val=stop_val,
            step_size=step_size,
            num_pts=int(safe_float(self.num_pts_entry.get())),
            compliance=comp_val,
            pulse_width=safe_float(self.pulse_width_entry.get()),
            pulse_delay=safe_float(self.delay_entry.get()),
            frequency=safe_float(self.frequency_entry.get()),
            glitch_points=glitch_pts
        )

        device_info = DeviceInfo(
            device_name=self.device_name_entry.get(),
            dimensions=self.device_dim_entry.get(),
            temperature=self.device_temp_entry.get(),
            test_type=self.test_laser_var.get(),
            plot_dir=self.plot_dir_entry.get(),
            txt_dir=self.txt_dir_entry.get()
        )
        
        safety = SafetyLimits()

        # Create a new live-plot run for this measurement.
        run_temperature = device_info.temperature.strip()

        if run_temperature:
            run_label = f"{run_temperature}\u00B0C"
        else:
            run_label = None

        self.live_plot.start_new_run(run_label)

        def measurement_thread():
            instruments_dict = {}
            try:
                instruments_dict = initialize_instruments(rm, config, meas_type, params)
                
                def update_plot(curr, light, volt):
                    self.master.after(0, self.add_live_measurement_point, curr, light, volt)
                
                v_arr, c_arr, l_arr = sweep_and_collect(
                    instruments_dict, config, params, meas_type, safety, update_plot, lambda: self.is_stopped
                )
                
                if len(v_arr) > 0:
                    save_and_plot_data(v_arr, c_arr, l_arr, device_info, meas_type)
                    
            except Exception as e:
                import traceback
                traceback.print_exc()
                print(f"Error during measurement: {e}")
            finally:
                try:
                    shutdown_instruments(instruments_dict)
                finally:
                    self.master.after(0, self.measurement_finished)

        measurement_thread_worker = threading.Thread(
            target=measurement_thread,
            daemon=True
        )

        self.measurement_running = True
        self.startButton.config(state=DISABLED, bg='lightgray', disabledforeground='gray40', text='Running...')
        self.clearButton.config(state=DISABLED, bg='lightgray', disabledforeground='gray40', text='Locked')

        try:
            measurement_thread_worker.start()
        except Exception:
            self.measurement_finished()
            raise

if __name__ == '__main__':
    root = tk.Tk()
    app = UnifiedMeasurementGUI(root)
    root.mainloop()
