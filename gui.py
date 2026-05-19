import tkinter as tk
from tkinter import Label, Entry, Button, LabelFrame, OptionMenu, Radiobutton, StringVar, IntVar, BooleanVar, Checkbutton, DISABLED, NORMAL, font
import pyvisa
import threading
import os
import matplotlib.pyplot as plt

from core_types import InstrumentConfig, SweepParameters, DeviceInfo, MeasurementType, SweepType, LightMode, SafetyLimits
from instruments import initialize_instruments, shutdown_instruments
from measurement_loop import sweep_and_collect
from data_export import save_and_plot_data
from live_plot import LivePlotLIV
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
        
        self.meas_type_var = StringVar(value='CW')
        Radiobutton(self.modeFrame, text='Continuous Wave (CW)', variable=self.meas_type_var, value='CW', command=self.update_dynamic_fields).grid(row=0, column=0, padx=10)
        Radiobutton(self.modeFrame, text='Voltage Pulsed (VPulse)', variable=self.meas_type_var, value='VPULSE', command=self.update_dynamic_fields).grid(row=0, column=1, padx=10)
        Radiobutton(self.modeFrame, text='Current Pulsed (IPulse)', variable=self.meas_type_var, value='IPULSE', command=self.update_dynamic_fields).grid(row=0, column=2, padx=10)

        # Build Frames
        self.build_sweep_settings_frame()
        self.build_device_settings_frame()
        self.build_measurement_params_frame()
        self.build_instrument_settings_frame()
        self.build_plot_frame()
        
        # Trigger initial state update
        self.update_dynamic_fields()

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

        # Sweep Type (Lin/Log)
        self.sweep_type_var = StringVar(value='Lin')
        self.lin_radio = Radiobutton(self.setFrame, text='Lin', variable=self.sweep_type_var, value='Lin')
        self.lin_radio.grid(row=6, column=0, sticky='W')
        self.log_radio = Radiobutton(self.setFrame, text='Log', variable=self.sweep_type_var, value='Log')
        self.log_radio.grid(row=6, column=1, sticky='W')

        # # of points for Log sweep
        self.num_pts_label = Label(self.setFrame, text='# of pts')
        self.num_pts_label.grid(row=6, column=2, sticky='W')
        self.num_pts_entry = Entry(self.setFrame, width=8)
        self.num_pts_entry.grid(row=6, column=3, sticky='W')

        # Buttons
        Button(self.setFrame, text='Start', command=self.start_measurement, bg='lightgreen').grid(row=7, column=2, pady=10)
        Button(self.setFrame, text='Stop', command=self.stop_measurement, bg='salmon').grid(row=7, column=3, pady=10)

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
        self.tecFrame = LabelFrame(self.devFrame, text='LDC-3724B TEC')
        self.tecFrame.grid(column=0, columnspan=2, row=4, sticky='NSEW', pady=(5, 0))
        
        Label(self.tecFrame, text='TEC address').grid(row=0, column=0, sticky='W')
        self.tec_address = StringVar(value='Select...')
        addresses = list(rm.list_resources()) if list(rm.list_resources()) else ['None']
        OptionMenu(self.tecFrame, self.tec_address, *(addresses + ['Select...'])).grid(row=0, column=1)

        Label(self.tecFrame, text='Temp. Set (°C)').grid(row=1, column=0, sticky='W')
        self.device_temp_entry = Entry(self.tecFrame, width=6)
        self.device_temp_entry.grid(row=1, column=1)

    def build_measurement_params_frame(self):
        self.paramsFrame = LabelFrame(self.master, text='Optical Parameters')
        self.paramsFrame.grid(column=1, row=2, sticky='NSEW', padx=5, pady=5)
        
        Label(self.paramsFrame, text='Wavelength (nm)').grid(column=0, row=0, sticky='W')
        self.wavelength_entry = Entry(self.paramsFrame, width=8)
        self.wavelength_entry.grid(column=0, row=1, sticky='W')

        Label(self.paramsFrame, text='Medium X (µm)').grid(column=1, row=0, sticky='W')
        self.medium_x_entry = Entry(self.paramsFrame, width=8)
        self.medium_x_entry.grid(column=1, row=1, sticky='W')

        Label(self.paramsFrame, text='Medium Y (µm)').grid(column=2, row=0, sticky='W')
        self.medium_y_entry = Entry(self.paramsFrame, width=8)
        self.medium_y_entry.grid(column=2, row=1, sticky='W')

        Label(self.paramsFrame, text='Distance Z (mm)').grid(column=0, row=2, sticky='W')
        self.distance_entry = Entry(self.paramsFrame, width=8)
        self.distance_entry.grid(column=0, row=3, sticky='W')

        Label(self.paramsFrame, text='Detector Area (mm²)').grid(column=1, row=2, sticky='W')
        self.detector_area_entry = Entry(self.paramsFrame, width=8)
        self.detector_area_entry.grid(column=1, row=3, sticky='W')

        Label(self.paramsFrame, text='Gain Z (V/A)').grid(column=2, row=2, sticky='W')
        self.transimpedance_gain_entry = Entry(self.paramsFrame, width=8)
        self.transimpedance_gain_entry.grid(column=2, row=3, sticky='W')

        self.computeAbsPower_var = BooleanVar(value=False)
        self.compute_power_checkbox = Checkbutton(self.paramsFrame, text='Compute Absolute Power', variable=self.computeAbsPower_var)
        self.compute_power_checkbox.grid(column=0, row=4, columnspan=3, sticky='W', pady=(10,0))

    def build_instrument_settings_frame(self):
        self.instFrame = LabelFrame(self.master, text='Instrument Settings')
        self.instFrame.grid(column=0, row=2, sticky='NSEW', padx=5, pady=5)
        
        addresses = list(rm.list_resources()) if list(rm.list_resources()) else ['No devices detected']
        
        self.smu_label = Label(self.instFrame, text='SMU Address:')
        self.smu_label.grid(row=0, column=0, sticky='W')
        self.smu_addr_var = StringVar(value='Select...')
        self.smu_menu = OptionMenu(self.instFrame, self.smu_addr_var, *addresses)
        self.smu_menu.grid(row=0, column=1)

        self.pulse_label = Label(self.instFrame, text='Pulser Address:')
        self.pulse_addr_var = StringVar(value='Select...')
        self.pulse_menu = OptionMenu(self.instFrame, self.pulse_addr_var, *addresses)
        
        Label(self.instFrame, text='Sensor Address:').grid(row=1, column=0, sticky='W')
        self.osc_addr_var = StringVar(value='Select...')
        OptionMenu(self.instFrame, self.osc_addr_var, *(['None (IV)'] + addresses)).grid(row=1, column=1)

        self.light_mode_var = StringVar(value='osc')
        Radiobutton(self.instFrame, text='Thermo', variable=self.light_mode_var, value='thermo').grid(row=2, column=0)
        Radiobutton(self.instFrame, text='Scope', variable=self.light_mode_var, value='osc').grid(row=2, column=1)
        Radiobutton(self.instFrame, text='SourceMeter', variable=self.light_mode_var, value='SourceMeter').grid(row=2, column=2)

        # Channels Frame
        self.chanFrame = tk.Frame(self.instFrame)
        self.chanFrame.grid(row=3, column=0, columnspan=3, sticky='EW', pady=5)
        
        channels = [1, 2, 3, 4]
        impedance = ['50Ω', '1MΩ']
        
        # Light Channel
        Label(self.chanFrame, text='Light Ch').grid(row=0, column=0)
        self.light_channel = IntVar(value=1)
        OptionMenu(self.chanFrame, self.light_channel, *channels).grid(row=1, column=0)
        self.light_channel_impedance = StringVar(value='50Ω')
        OptionMenu(self.chanFrame, self.light_channel_impedance, *impedance).grid(row=2, column=0)

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

    def build_plot_frame(self):
        self.plotFrame = LabelFrame(self.master, text='Live Plot')
        self.plotFrame.grid(column=0, row=3, columnspan=2, sticky='NSEW', padx=5, pady=5)
        self.master.rowconfigure(3, weight=3)
        self.plotFrame.rowconfigure(0, weight=1)
        self.plotFrame.columnconfigure(0, weight=1)
        self.live_plot = LivePlotLIV(self.plotFrame)

    def update_dynamic_fields(self):
        mode = self.meas_type_var.get()
        
        if mode == 'CW':
            self.start_label.config(text='Start (V)')
            self.stop_label.config(text='Stop (V)')
            self.step_label.config(text='Step Size (mV)')
            self.compliance_label.config(text='Compliance (mA)')
            
            # Hide pulsed fields
            self.pulse_width_label.grid_remove()
            self.pulse_width_entry.grid_remove()
            self.delay_label.grid_remove()
            self.delay_entry.grid_remove()
            self.frequency_label.grid_remove()
            self.frequency_entry.grid_remove()
            self.series_res_label.grid_remove()
            self.series_resistance_entry.grid_remove()
            
            # Show SMU, hide Pulser
            self.pulse_label.grid_remove()
            self.pulse_menu.grid_remove()
            self.smu_label.grid(row=0, column=0, sticky='W')
            self.smu_menu.grid(row=0, column=1)

            # Hide extra channels
            self.curr_chan_lbl.grid_remove(); self.curr_chan_menu.grid_remove(); self.curr_imp_menu.grid_remove()
            self.volt_chan_lbl.grid_remove(); self.volt_chan_menu.grid_remove(); self.volt_imp_menu.grid_remove()
            self.trig_chan_lbl.grid_remove(); self.trig_chan_menu.grid_remove()

        elif mode == 'VPULSE':
            self.start_label.config(text='Start (V)')
            self.stop_label.config(text='Stop (V)')
            self.step_label.config(text='Step Size (mV)')
            self.compliance_label.config(text='Compliance (mA)') # Not heavily used in AVTECH
            
            # Show pulsed fields
            self.pulse_width_label.grid(row=4, column=0, sticky='W')
            self.pulse_width_entry.grid(row=4, column=1, sticky='W')
            self.delay_label.grid(row=4, column=2, sticky='W')
            self.delay_entry.grid(row=4, column=3, sticky='W')
            self.frequency_label.grid(row=5, column=0, sticky='W')
            self.frequency_entry.grid(row=5, column=1, sticky='W')
            self.series_res_label.grid(row=5, column=2, sticky='W')
            self.series_resistance_entry.grid(row=5, column=3, sticky='W')

            # Show Pulser, hide SMU
            self.smu_label.grid_remove()
            self.smu_menu.grid_remove()
            self.pulse_label.grid(row=0, column=0, sticky='W')
            self.pulse_menu.grid(row=0, column=1)
            
            # Show all channels
            self.curr_chan_lbl.grid(row=0, column=1); self.curr_chan_menu.grid(row=1, column=1); self.curr_imp_menu.grid(row=2, column=1)
            self.volt_chan_lbl.grid(row=0, column=2); self.volt_chan_menu.grid(row=1, column=2); self.volt_imp_menu.grid(row=2, column=2)
            self.trig_chan_lbl.grid(row=0, column=3); self.trig_chan_menu.grid(row=1, column=3)

        elif mode == 'IPULSE':
            self.start_label.config(text='Start (mA)')
            self.stop_label.config(text='Stop (mA)')
            self.step_label.config(text='Step Size (mA)')
            self.compliance_label.config(text='Limit (V)')
            
            # Show pulsed fields
            self.pulse_width_label.grid(row=4, column=0, sticky='W')
            self.pulse_width_entry.grid(row=4, column=1, sticky='W')
            self.delay_label.grid(row=4, column=2, sticky='W')
            self.delay_entry.grid(row=4, column=3, sticky='W')
            self.frequency_label.grid_remove()
            self.frequency_entry.grid_remove()
            self.series_res_label.grid_remove()
            self.series_resistance_entry.grid_remove()

            # Show Pulser
            self.smu_label.grid_remove()
            self.smu_menu.grid_remove()
            self.pulse_label.grid(row=0, column=0, sticky='W')
            self.pulse_menu.grid(row=0, column=1)

            # Show all channels
            self.curr_chan_lbl.grid(row=0, column=1); self.curr_chan_menu.grid(row=1, column=1); self.curr_imp_menu.grid(row=2, column=1)
            self.volt_chan_lbl.grid(row=0, column=2); self.volt_chan_menu.grid(row=1, column=2); self.volt_imp_menu.grid(row=2, column=2)
            self.trig_chan_lbl.grid(row=0, column=3); self.trig_chan_menu.grid(row=1, column=3)

    def stop_measurement(self):
        self.is_stopped = True

    def start_measurement(self):
        self.is_stopped = False
        self.live_plot.reset()
        
        mode_str = self.meas_type_var.get()
        meas_type = MeasurementType[mode_str]

        # Gather Config
        config = InstrumentConfig(
            smu_address=self.smu_addr_var.get(),
            osc_address=self.osc_addr_var.get(),
            pulser_address=self.pulse_addr_var.get(),
            tec_address=self.tec_address.get(),
            light_mode=LightMode(self.light_mode_var.get()) if self.light_mode_var.get() != 'None (IV)' else LightMode.NONE,
            light_channel=self.light_channel.get(),
            light_channel_impedance=self.light_channel_impedance.get(),
            volt_channel=self.voltage_channel.get(),
            curr_channel=self.current_channel.get(),
            thermopile_wavelength=self.wavelength_entry.get()
        )

        def safe_float(s):
            try: return float(s)
            except: return 0.0

        st_map = {'Lin': SweepType.LINEAR, 'Log': SweepType.LOGARITHMIC}
        
        # Scaling logic
        scale = 1000.0 if mode_str == 'CW' else 1.0 
        
        params = SweepParameters(
            sweep_type=st_map.get(self.sweep_type_var.get(), SweepType.LINEAR),
            start_val=safe_float(self.start_entry.get()),
            stop_val=safe_float(self.stop_entry.get()),
            step_size=safe_float(self.step_entry.get()) / scale,
            num_pts=int(safe_float(self.num_pts_entry.get())),
            compliance=safe_float(self.compliance_entry.get()) / 1000.0,
            pulse_width=safe_float(self.pulse_width_entry.get()),
            pulse_delay=safe_float(self.delay_entry.get())
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

        def measurement_thread():
            instruments_dict = {}
            try:
                instruments_dict = initialize_instruments(rm, config, meas_type)
                
                def update_plot(curr, light, volt):
                    self.master.after(0, self.live_plot.add_point, curr, light, volt)
                
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
                shutdown_instruments(instruments_dict)

        threading.Thread(target=measurement_thread, daemon=True).start()

if __name__ == '__main__':
    root = tk.Tk()
    app = UnifiedMeasurementGUI(root)
    root.mainloop()
