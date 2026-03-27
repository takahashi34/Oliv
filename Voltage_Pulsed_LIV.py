from time import sleep, strftime
import numpy as np
from numpy import append, zeros, arange, logspace, log10, size
import os
import shutil
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from tkinter import Label, Entry, Button, LabelFrame, OptionMenu, Radiobutton, StringVar, IntVar, DISABLED, NORMAL, BooleanVar, Checkbutton

# Import Browse button functions
from Browse_buttons import browse_plot_file, browse_txt_file
# Import Oscilloscope scaling
from Oscilloscope_Scaling import incrOscVertScale, channelImpedance
# Import trigger updating
from Update_Trigger import updateTriggerCursor
# Import live plotting
from live_plot import LivePlotLI, LivePlotIV, LivePlotLIV
# Import configuration manager
from config_manager import add_config_buttons

# Use mock instruments for testing without hardware
from mock_instruments import get_resource_manager
rm = get_resource_manager()

class VPulse_LIV():

    # Import vertical scaling
    from adjustVerticalScale import adjustVerticalScale

    def start_liv_pulse(self):

        thermo_mode = (self.lightMode_var.get() == 'thermo')

        # Connect to oscilloscope
        self.scope = rm.open_resource(self.scope_address.get())

        # Initialize oscilloscope
        self.scope.write("*RST")
        self.scope.write("*CLS")
        
        if thermo_mode:
            self.thermopile = rm.open_resource(self.thermopile_address.get())
            self.thermopile.write("*CSU")
            self.thermopile.timeout = 5000
            self.thermopile.write_termination = ''
            wavelength = int(self.wavelength_entry.get())
            self.thermopile.write(f"*PWC{wavelength:05d}")
            print(f"Set wavelength to: {wavelength} nm")

        # Set channel impedance to 50 ohms
        self.scope.write(":CHANnel%d:IMPedance %s" %(self.light_channel.get(), channelImpedance(self.light_channel_impedance.get())))
        self.scope.write(":CHANnel%d:IMPedance %s" %(self.current_channel.get(), channelImpedance(self.curr_channel_impedance.get())))
        self.scope.write(":CHANnel%d:IMPedance %s" %(self.voltage_channel.get(), channelImpedance(self.volt_channel_impedance.get())))

        pulseWidth = float(self.pulse_width_entry.get())

        # Mulitplication by 10 is due to a peculiarty of this oscilloscope
        self.scope.write(":TIMebase:RANGe %.6fus" %(0.5*pulseWidth*10))

        self.scope.write(":TRIGger:MODE GLITch")
        self.scope.write(":TRIGger:GLITch:SOURce CHANnel%d" %self.trigger_channel.get())
        self.scope.write(":TRIGger:GLITch:QUALifier RANGe")

        # Define glitch trigger range as: [50% of PW, 150% of PW]
        glitchTriggerLower = pulseWidth*0.5
        glitchTriggerUpper = pulseWidth*1.5
        self.scope.write(":TRIGger:GLITch:RANGe %.6fus,%.6fus" %(glitchTriggerLower,glitchTriggerUpper))

        # Set initial trigger point to 1 mV
        self.scope.write("TRIGger:GLITch:LEVel 1E-3")
        # Note previous trigger level before updating the trigger cursor
        trigger_prev = 1e-3

        # Channel scales - set each channel to 1mV/div to start
        vertScaleLight = 0.001
        vertScaleCurrent = 0.001
        vertScaleVoltage = 0.001

        # Initial scale for light channel
        self.scope.write(":CHANNEL%d:SCALe %.3f" %(self.light_channel.get(), vertScaleLight))
        self.scope.write(":CHANnel%d:DISPlay ON" % self.light_channel.get())
        # Initial scale for current channel
        self.scope.write(":CHANNEL%d:SCALe %.3f" %(self.current_channel.get(), vertScaleCurrent))
        self.scope.write(":CHANnel%d:DISPlay ON" % self.current_channel.get())
        # Initial scale for voltage channel
        self.scope.write(":CHANNEL%d:SCALe %.3f" %(self.voltage_channel.get(), vertScaleVoltage))
        self.scope.write(":CHANnel%d:DISPlay ON" % self.voltage_channel.get())

        # Move each signal down two divisions for a better view on the screen
        self.scope.write(":CHANnel%d:OFFset %.3fV" %(self.light_channel.get(), 2*vertScaleLight))
        self.scope.write(":CHANnel%d:OFFset %.3fV" %(self.current_channel.get(), 2*vertScaleCurrent))
        self.scope.write(":CHANnel%d:OFFset %.3fV" %(self.voltage_channel.get(), 2*vertScaleVoltage))

        # Total mV based on 6 divisions to top of display
        totalDisplayLight = 6*vertScaleLight
        totalDisplayCurrent = 6*vertScaleCurrent
        totalDisplayVoltage = 6*vertScaleVoltage

        # Connect to AVTECH Voltage Pulser
        self.pulser = rm.open_resource(self.pulse_address.get())

        # Initialize pulser
        self.pulser.write("*RST")
        self.pulser.write("*CLS")
        self.pulser.write("OUTPut:IMPedance 50")
        self.pulser.write("SOURce INTernal")
        self.pulser.write("PULSe:WIDTh "+ self.pulse_width_entry.get() + "us")
        self.pulser.write("FREQuency " + self.frequency_entry.get() + "kHz")
        self.pulser.write("OUTPut ON")

        # Calculate number of points based on step size
        voltageRangeStart = float(self.start_voltage_entry.get())
        voltageRangeStop = float(self.stop_voltage_entry.get()) + float(self.step_size_entry.get())/1000
        voltageRangeStep = float(self.step_size_entry.get())/1000

        # Obtain series resistance value from entry box
        seriesResistance = float(self.series_resistance_entry.get())

        voltageSourceValues = np.arange(voltageRangeStart, voltageRangeStop, voltageRangeStep)

        # Lists for data values
        lightData = list() 
        currentData = list()  # To be plotted on y-axis
        voltageData = list()  # To be plotted on x-axis

        lightData.append(0)
        voltageData.append(0)
        currentData.append(0)

        # Reset and initialize live plot
        self.live_plot.reset()
        self.live_plot.add_point(0, 0, 0)  # Initial point (current, voltage, light)

        # Handling glitch points
        prevPulserVoltage = 0
        V_glitch_1 = 7.12
        V_glitch_2 = 21.6
        V_glitch_3 = 68

        for V_s in voltageSourceValues:
            if ((prevPulserVoltage <= V_glitch_1 < V_s) or (prevPulserVoltage <= V_glitch_2 < V_s) or (prevPulserVoltage <= V_glitch_3 < V_s)):
                self.pulser.write("output off")
                self.pulser.write("volt %.3f" %V_s)
                prevPulserVoltage = V_s
                sleep(4)
            else:
                self.pulser.write("VOLT %.3f" % (V_s))
                self.pulser.write("OUTPut ON")

                # Read light amplitude from oscilloscope
                light_ampl_osc = light_ampl_osc = self._read_light()
                # Update trigger cursor if it being applied to the current waveform
                if (self.trigger_channel.get() == self.light_channel.get()):
                    updateTriggerCursor(light_ampl_osc, self.scope, totalDisplayLight)

                # Read current amplitude from oscilloscope; multiply by 2 to use 50-ohms channel
                current_ampl_osc = self.scope.query_ascii_values("SINGLE;*OPC;:MEASure:VAMPlitude? CHANNEL%d" % self.current_channel.get())[0]
                # Update trigger cursor if it being applied to the current waveform
                if (self.trigger_channel.get() == self.current_channel.get()):
                    updateTriggerCursor(current_ampl_osc, self.scope, totalDisplayCurrent)

                # Read voltage amplitude
                voltage_ampl_osc = self.scope.query_ascii_values("SINGLE;*OPC;:MEASure:VAMPlitude? CHANNEL%d" % self.voltage_channel.get())[0]
                # Update trigger cursor if it being applied to the current waveform
                if (self.trigger_channel.get() == self.voltage_channel.get()):
                    updateTriggerCursor(voltage_ampl_osc, self.scope, totalDisplayVoltage)
                    
                # Adjust vertical scales if measured amplitude reaches top of screen (90% of display)
                vertScaleLight = self.adjustVerticalScale(self.light_channel.get(), self.trigger_channel.get(),\
                    light_ampl_osc, totalDisplayLight, vertScaleLight)      
                vertScaleCurrent = self.adjustVerticalScale(self.current_channel.get(), self.trigger_channel.get(),\
                    current_ampl_osc, totalDisplayCurrent, vertScaleCurrent)                
                vertScaleVoltage = self.adjustVerticalScale(self.voltage_channel.get(), self.trigger_channel.get(),\
                    voltage_ampl_osc, totalDisplayVoltage, vertScaleVoltage)

                # Get updated readings
                light_ampl_osc = self._read_light()
                current_ampl_osc = self.scope.query_ascii_values("SINGLE;*OPC;:MEASure:VAMPlitude? CHANNEL%d" % self.current_channel.get())[0]
                voltage_ampl_osc = self.scope.query_ascii_values("SINGLE;*OPC;:MEASure:VAMPlitude? CHANNEL%d" % self.voltage_channel.get())[0]
                
                # Update available display
                totalDisplayLight = 6*vertScaleLight
                totalDisplayCurrent = 6*vertScaleCurrent
                totalDisplayVoltage = 6*vertScaleVoltage

                current_ampl_device = 2*current_ampl_osc
                voltage_ampl_device = voltage_ampl_osc - seriesResistance*current_ampl_device

                lightData.append(light_ampl_osc)
                voltageData.append(voltage_ampl_device)
                currentData.append(current_ampl_device)

                # Update live plot (convert to mA and mV for display)
                self.live_plot.add_point(current_ampl_device * 1000, voltage_ampl_device * 1000, light_ampl_osc * 1000)

                # Handling glitch points
                prevPulserVoltage = V_s

        # Convert current and voltage readings to mA and mV values
        currentData[:] = [x*1000 for x in currentData]
        voltageData[:] = [x*1000 for x in voltageData]

        # Turn off the pulser, and clear event registers
        self.pulser.write("OUTPut OFF")
        self.pulser.write("*CLS")
        # Stop acquisition on oscilloscope
        self.scope.write(":STOP")
        # Stop acquisition on thermopile if in use.
        if thermo_mode:
            self.thermopile.write("*CSU")

        try:
            if not os.path.exists(self.txt_dir_entry.get()):
                os.makedirs(self.txt_dir_entry.get())
        except:
            print('Error: Creating directory: '+self.txt_dir_entry.get())

        # open file and write in data
        txtDir = self.txt_dir_entry.get()
        filename = self.device_name_entry.get() + '_VP-LIV_' + self.device_temp_entry.get() + \
            'C_' + self.device_dim_entry.get() + '_' + self.test_laser_button_var.get()
        filepath = os.path.join(txtDir + '/' + filename + '.txt')
        fd = open(filepath, 'w+')
        i = 1

        fd.writelines('Device light output (W)\tCurrent (mA)\tVoltage (mV)\n')
        for i in range(0, len(currentData)):
            fd.writelines(str(lightData[i]))
            fd.writelines('\t')
            fd.writelines(str(currentData[i]))
            fd.writelines('\t')
            fd.writelines(str(voltageData[i]))
            fd.writelines('\n')
        fd.close()


        # ------------------ Plot measured characteristic ----------------------------------

        fig, ax1 = plt.subplots()
        ax2 = ax1.twinx()
        ax2.set_ylabel('Measured device light output (W)', color='red')
        ax1.set_xlabel('Measured device current (mA)')
        ax1.set_ylabel('Measured device voltage (mV)', color='blue')
        ax1.plot(currentData, voltageData, color='blue', label='I-V Characteristic')
        ax2.plot(currentData, lightData, color='red', label='L-I Characteristic')
        ax1.legend(loc='upper left')

        plotString = 'Device Name: ' + self.device_name_entry.get() + '\nTest Type: Voltage Pulsed\n' + 'Temperature (' + u'\u00B0' + 'C): ' + self.device_temp_entry.get() + \
            '\n' + 'Device Dimensions: ' + self.device_dim_entry.get() + ' (' + u'\u03BC' + 'm x ' + u'\u03BC' + 'm)\n' + \
            'Test Structure or Laser: ' + self.test_laser_button_var.get()

        plt.figtext(0.02, 0.02, plotString, fontsize=12)

        plt.subplots_adjust(bottom=0.3)

        plt.savefig(self.plot_dir_entry.get() + '/' + filename + ".png")
        plt.show()
        self.export_to_origin(currentData, voltageData, lightData, filename)

        if self.computeAbsPower:
            x = float(self.medium_x_entry.get()) * 1e-6      # µm → m
            y = float(self.medium_y_entry.get()) * 1e-6      # µm → m
            z = float(self.distance_entry.get()) * 1e-3    # mm → m
            lam = float(self.wavelength_entry.get()) * 1e-9  # nm → m
            Ad = float(self.detector_area_entry.get()) * 1e-6  # mm² → m²
            Z = float(self.transimpedance_gain_entry.get())

            C = precompute_constant(x, y, z, lam, Ad, R, Z)
            print("Precomputed constant:", C)

            absolute_power = C * np.array(lightData)
            # -- Plot AbsPower -- #
            fig2, ax1 = plt.subplots()
            ax2 = ax1.twinx()

            ax1.set_xlabel('Measured device current (mA)')
            ax1.set_ylabel('Measured device voltage (mV)', color='blue')
            ax2.set_ylabel('Absolute optical power (W)', color='red')

            ax1.plot(currentData, voltageData, color='blue', label='I-V Characteristic')
            ax2.plot(currentData, absolute_power, color='red', label='L-P Characteristic')

            ax1.legend(loc='upper left')

            plt.figtext(0.02, 0.02, plotString, fontsize=12)
            plt.subplots_adjust(bottom=0.3)

            fig2.savefig(f"{self.plot_dir_entry.get()}/{filename}_absolute_power.png")
            plt.show()

        try:
            if not os.path.exists(self.plot_dir_entry.get()):
                os.makedirs(self.plot_dir_entry.get())
        except:
            print('Error: Creating directory: ' + self.plot_dir_entry.get())


    def thermo_selected(self):
        # Show thermopile address, hide oscilloscope channel picker
        self.light_channel_dropdown.grid_remove()
        self.thermopile_addr.grid(column=0, columnspan=2, row=5, padx=5, pady=5, sticky='W')
        self.light_channel_label.config(state=NORMAL)  # Keep label visible
        self.start_button.config(command=self.start_liv_pulse)
        self.compute_power_checkbox.config(state=DISABLED)

    """
    Function referenced when: Oscilloscope radiobutton is selected
    Description: When in oscilloscope mode enable the dropdown boxes
    for the selection of the light channel/channel impedance.
    """
    def osc_selected(self):
        # Show oscilloscope channel picker, hide thermopile address
        self.thermopile_addr.grid_remove()
        self.light_channel_dropdown.grid(column=0, row=5, padx=5, pady=5, sticky='W')

        self.light_channel_label.config(state=NORMAL)
        self.start_button.config(command=self.start_liv_pulse)
        self.compute_power_checkbox.config(state=NORMAL)

    def _read_light(self):
        if self.lightMode_var.get() == 'thermo':
            try:
                raw = self.thermopile.query('*CVU')
                return float(raw)
            except ValueError:
                print(f"Thermopile read error: {raw}")
                return 0.0
        else:
            return self.scope.query_ascii_values(
                "SINGLE;*OPC;:MEASure:VAMPlitude? CHANNEL%d" % self.light_channel.get()
            )[0]

    def precompute_constant(x, y, z, lam, Ad, R, Z):
        PI = np.pi
        PI2 = PI * PI

        term_x = np.sqrt(1 + (16 * z**2 * lam**2) / (PI2 * x**4))
        term_y = np.sqrt(1 + (16 * z**2 * lam**2) / (PI2 * y**4))

        print ((PI * x * y * term_x * term_y) / (2 * Ad * R * Z))


    def toggle_param_entries(self):
        """ Enables or disables the measurement entries based on the checkbox. """
        # Update your boolean variable
        self.computeAbsPower = self.computeAbsPower_var.get()
        
        # Determine the target state
        new_state = 'normal' if self.computeAbsPower else 'disabled'
        
        # Apply the state to all entries
        self.medium_x_entry.config(state=new_state)
        self.medium_y_entry.config(state=new_state)
        self.distance_entry.config(state=new_state)
        self.detector_area_entry.config(state=new_state)
        self.transimpedance_gain_entry.config(state=new_state)
        self.responsivity_entry.config(state=new_state)

    def init_tec(self):
        if not hasattr(self, 'tec'):
            self.tec = LDC3724B_TEC(rm, self.tec_address.get())

    def set_tec_temp(self):
        self.init_tec()
        temp = float(self.tec_temp_entry.get())
        self.tec.set_temperature(temp)
        self.tec.output_on()

    def toggle_tec(self):
        self.init_tec()
        if self.tec.output_state():
            self.tec.output_off()
        else:
            self.tec.output_on()

    def update_tec_readback(self):
        if hasattr(self, 'tec'):
            try:
                t = self.tec.get_temperature()
                self.tec_status.config(text=f'Current: {t:.2f} °C')
            except Exception:
                self.tec_status.config(text='TEC read error')

        self.master.after(1000, self.update_tec_readback)

    def export_to_origin(self, currentData, voltageData, lightData, filename):
        import subprocess

        opj_path    = (self.plot_dir_entry.get() + '/' + filename + '.opj').replace('\\', '/')
        txt_path    = (self.txt_dir_entry.get()  + '/' + filename + '.txt').replace('\\', '/')
        script_path = (self.plot_dir_entry.get() + '/' + filename + '_import.ogs').replace('\\', '/')
        origin_exe  =  r"C:\Program Files (x86)\Origin Lab\Origin85\Origin85.exe"

        script = f"""
    doc -n;

    // Import tab-delimited txt file
    string fname$ = "{txt_path}";
    impasc fname$ options.hdr.numSubHdr:=1 options.hdr.longnames:=1;

    // Imported column order: col(1)=L(W), col(2)=I(mA), col(3)=V(mV)
    // Add converted columns
    wks.nCols = 6;
    col(4) = col(2);            // I in mA
    col(5) = col(3) / 1000;    // V mV -> V
    col(6) = col(1) * 1000;    // L W  -> mW

    col(4)[L]$ = "Current";      col(4)[U]$ = "mA";
    col(5)[L]$ = "Voltage";      col(5)[U]$ = "V";
    col(6)[L]$ = "Light Output"; col(6)[U]$ = "mW";

    // Set col(4) as X for L-I plot
    wks.col = 4;
    wks.colDesig = 3;

    // L-I plot: I(mA) on bottom axis, L(mW) on left axis
    plotxy (4,6) plot:=200;
    layer.x.label$ = "Current (mA)";
    layer.y.label$ = "Light Output (mW)";
    page.title$ = "L-I {filename}";

    // Add col(7) for I in A
    wks.nCols = 7;
    col(7) = col(2) / 1000;    // I mA -> A
    col(7)[L]$ = "Current";    col(7)[U]$ = "A";

    // Set col(5) as X for I-V plot
    wks.col = 5;
    wks.colDesig = 3;

    // I-V plot: V(V) on bottom axis, I(A) on left axis
    plotxy (5,7) plot:=200;
    layer.x.label$ = "Voltage (V)";
    layer.y.label$ = "Current (A)";
    page.title$ = "I-V {filename}";

    save "{opj_path}";
    """

        with open(script_path, 'w') as f:
            f.write(script)
        print(f"LabTalk script written: {script_path}")

        subprocess.Popen([origin_exe, '-rs', script_path])
        print("Origin launched — check Origin window for plots.")
    
    def build_tec_frame(self):
        self.tecFrame = LabelFrame(self.devFrame, text='LDC-3724B TEC')
        self.tecFrame.grid(column=1, row=2, sticky='N', pady=(5, 0))

        Label(self.tecFrame, text='TEC address').grid(row=0, column=0, sticky='W')
        self.tec_address = StringVar()
        self.tec_address.set('Select...')

        addresses = list(rm.list_resources())
        OptionMenu(self.tecFrame, self.tec_address, *addresses).grid(row=0, column=1)

        Label(self.tecFrame, text='Temp. to Set (°C)').grid(row=1, column=0, sticky='W')
        self.tec_temp_entry = Entry(self.tecFrame, width=6)
        self.tec_temp_entry.grid(row=1, column=1)

        self.tec_status = Label(self.tecFrame, text='Current: --- °C')
        self.tec_status.grid(row=2, column=0, columnspan=2)

        Button(self.tecFrame, text='Send Temp.', command=self.set_tec_temp).grid(row=3, column=0)
        Button(self.tecFrame, text='Toggle Output', command=self.toggle_tec).grid(row=3, column=1)    


    def __init__(self, parent):
        self.master = parent

        # Assign window title and geometry
        self.master.title('Voltage Pulsed LIV')
        
        # Allow master to distribute space across its 2 columns and 3 rows
        self.master.columnconfigure(0, weight=1)
        self.master.columnconfigure(1, weight=1)
        self.master.rowconfigure(0, weight=1)
        self.master.rowconfigure(1, weight=1)
        self.master.rowconfigure(2, weight=1)

        """ Pulse settings frame """
        self.pulseFrame = LabelFrame(self.master, text='Pulse Settings')
        # Display pulse settings frame
        self.pulseFrame.grid(column=0, row=0, rowspan=2, sticky='NSEW', padx=5, pady=5)
        for c in range(4):
            self.pulseFrame.columnconfigure(c, weight=1)
        for r in range(10):
            self.pulseFrame.rowconfigure(r, weight=1)

        # Create plot directory label, button, and entry box
        # Plot File Label
        self.plot_dir_label = Label(
            self.pulseFrame, text='Plot file directory:')
        self.plot_dir_label.grid(column=1, row=0, columnspan=2)
        # Plot directory Entry Box
        self.plot_dir_entry = Entry(self.pulseFrame, width=30)
        self.plot_dir_entry.grid(column=1, row=1, padx=(3, 0), columnspan=2)
        # Browse button
        self.plot_dir_file = Button(
            self.pulseFrame, text='Browse', command=lambda:browse_plot_file(self))
        self.plot_dir_file.grid(column=3, row=1, ipadx=5)

        # Create text directory label, button, and entry box
        # Text file label
        self.txt_dir_label = Label(
            self.pulseFrame, text='Text file directory:')
        self.txt_dir_label.grid(column=1, row=2, columnspan=2)
        # Text directory entry box
        self.txt_dir_entry = Entry(self.pulseFrame, width=30)
        self.txt_dir_entry.grid(column=1, row=3, padx=(3, 0), columnspan=2)
        # Browse button
        self.txt_dir_file = Button(
            self.pulseFrame, text='Browse', command=lambda:browse_txt_file(self))
        self.txt_dir_file.grid(column=3, row=3, ipadx=5)

        # Step size label
        self.step_size_label = Label(self.pulseFrame, text='Step size (mV)')
        self.step_size_label.grid(column=1, row=4)
        # Step size entry box
        self.step_size_entry = Entry(self.pulseFrame, width=5)
        self.step_size_entry.grid(column=1, row=5)

        # Delay label
        self.delay_label = Label(self.pulseFrame, text='Delay (ms)')
        self.delay_label.grid(column=2, row=4)
        # Delay entry box
        self.delay_entry = Entry(self.pulseFrame, width=5)
        self.delay_entry.grid(column=2, row=5)

        # Pulse width label
        self.pulse_width_label = Label(self.pulseFrame, text='Pulse Width (' + u'\u03BC' + 's)')
        self.pulse_width_label.grid(column=3, row=4)
        # Pulse width entry box
        self.pulse_width_entry = Entry(self.pulseFrame, width=5)
        self.pulse_width_entry.grid(column=3, row=5)

        # Start voltage label
        self.start_voltage_label = Label(self.pulseFrame, text='Start (V)')
        self.start_voltage_label.grid(column=1, row=6)
        # Start voltage entry box
        self.start_voltage_entry = Entry(self.pulseFrame, width=5)
        self.start_voltage_entry.grid(column=1, row=7)

        # Stop voltage label
        self.stop_voltage_label = Label(self.pulseFrame, text='Stop (V)')
        self.stop_voltage_label.grid(column=2, row=6)
        # Stop voltage entry box
        self.stop_voltage_entry = Entry(self.pulseFrame, width=5)
        self.stop_voltage_entry.grid(column=2, row=7)

        # Frequency label
        self.frequency_label = Label(self.pulseFrame, text='Frequency (kHz)')
        self.frequency_label.grid(column=3, row=6)
        # Frequency entry box
        self.frequency_entry = Entry(self.pulseFrame, width=5)
        self.frequency_entry.grid(column=3, row=7)

        # Series resistance label
        self.series_resistance_label = Label(self.pulseFrame, text='Series resistance (' + u'\u03A9' + ')')
        self.series_resistance_label.grid(column=1, row=8)
        # Series resistance entry box
        self.series_resistance_entry = Entry(self.pulseFrame, width=5)
        self.series_resistance_entry.grid(column=1, row=9, pady=(0,10))

        # Start Button
        self.start_button = Button(self.pulseFrame, text='Start', command=self.start_liv_pulse)
        self.start_button.grid(column=3, row=8, rowspan=2, ipadx=10, pady=5)

        """ Live Plot frame """
        self.plotFrame = LabelFrame(self.master)
        self.plotFrame.grid(column=0, row=2, sticky='NSEW', padx=5, pady=5)
         # Live plot for real-time visualization (dual axis for voltage and light)
        self.plotFrame.columnconfigure(0, weight=1)
        self.plotFrame.rowconfigure(0, weight=1)
        self.live_plot = LivePlotLIV(self.plotFrame)

        """ Device settings frame """
        self.devFrame = LabelFrame(self.master, text='Device Settings')
        # Display device settings frame
        self.devFrame.grid(column=1, row=0, sticky='NSEW', padx=5, pady=5)
        for c in range(2):
            self.devFrame.columnconfigure(c, weight=1)
        for r in range(6):
            self.devFrame.rowconfigure(r, weight=1)
        
        # Create label for device name entry box
        self.device_name_label = Label(self.devFrame, text='Device name:')
        self.device_name_label.grid(column=0, row=0, sticky='W')
        # Device name entry box
        self.device_name_entry = Entry(self.devFrame, width=15)
        self.device_name_entry.grid(column=0, row=1, sticky='W', padx=(3, 0))

        # Create label for device dimensions entry box
        self.device_dim_label = Label(self.devFrame, text='Device dimensions ' + '(' + u'\u03BC' + 'm x ' + u'\u03BC' + 'm):')
        self.device_dim_label.grid(column=0, row=2, sticky='W')
        # Device dimensions entry box
        self.device_dim_entry = Entry(self.devFrame, width=15)
        self.device_dim_entry.grid(column=0, row=3, sticky='W', padx=(3, 0))

        self.test_laser_button_var = StringVar()

        self.laser_radiobuttom = Radiobutton(self.devFrame, text='Laser', variable=self.test_laser_button_var, value='Laser')
        self.laser_radiobuttom.grid(column=0, row=4, padx=(10, 0), sticky='W')
        self.test_radiobuttom = Radiobutton(self.devFrame, text='Test', variable=self.test_laser_button_var, value='Test')
        self.test_radiobuttom.grid(column=1, row=4, padx=(10, 0), sticky='W')

        self.test_laser_button_var.set('Laser')


        # Create label for device temperature entry box
        self.device_temp_label = Label(self.devFrame, text='Temperature (' + u'\u00B0' +'C):')
        self.device_temp_label.grid(column=1, row=0, sticky='W')
        # Device name entry box
        self.device_temp_entry = Entry(self.devFrame, width=5)
        self.device_temp_entry.grid(column=1, row=1, sticky='W', padx=(3, 0))

        """ Measurement parameters frame """
        self.paramsFrame = LabelFrame(self.master, text='Measurement Parameters')
        self.paramsFrame.grid(column=1, row=1, sticky='NSEW', padx=5, pady=5)
        for c in range(3):
            self.paramsFrame.columnconfigure(c, weight=1)
        for r in range(7):
            self.paramsFrame.rowconfigure(r, weight=1)

        # ---------------- Wavelength ----------------
        self.wavelength_label = Label(self.paramsFrame, text='Wavelength (nm)')
        self.wavelength_label.grid(column=0, row=0, sticky='W')

        self.wavelength_entry = Entry(self.paramsFrame, width=5)
        self.wavelength_entry.grid(column=0, row=1, sticky='W', padx=(3,0), pady=(0,5))


        # ---------------- Active Region X ----------------
        self.medium_x_label = Label(self.paramsFrame, text='Active medium width (µm)')
        self.medium_x_label.grid(column=0, row=2, sticky='W')

        self.medium_x_entry = Entry(self.paramsFrame, width=5)
        self.medium_x_entry.grid(column=0, row=3, sticky='W', padx=(3,0), pady=(0,5))


        # ---------------- Active Region Y ----------------
        self.medium_y_label = Label(self.paramsFrame, text='Active medium height (µm)')
        self.medium_y_label.grid(column=1, row=0, sticky='W')

        self.medium_y_entry = Entry(self.paramsFrame, width=5)
        self.medium_y_entry.grid(column=1, row=1, sticky='W', padx=(3,0), pady=(0,5))


        # ---------------- Distance Z ----------------
        self.distance_label = Label(self.paramsFrame, text='Axial distance (mm)')
        self.distance_label.grid(column=1, row=2, sticky='W')

        self.distance_entry = Entry(self.paramsFrame, width=5)
        self.distance_entry.grid(column=1, row=3, sticky='W', padx=(3,0), pady=(0,5))


        # ---------------- Detector Area ----------------
        self.detector_area_label = Label(self.paramsFrame, text='Detector area (mm²)')
        self.detector_area_label.grid(column=2, row=0, sticky='W')

        self.detector_area_entry = Entry(self.paramsFrame, width=5)
        self.detector_area_entry.grid(column=2, row=1, sticky='W', padx=(3,0), pady=(0,5))


        # ---------------- Transimpedance Gain ----------------
        self.transimpedance_label = Label(self.paramsFrame, text='Transimpedance Gain (V/A)')
        self.transimpedance_label.grid(column=2, row=2, sticky='W')

        self.transimpedance_gain_entry = Entry(self.paramsFrame, width=5)
        self.transimpedance_gain_entry.grid(column=2, row=3, sticky='W', padx=(3,0), pady=(0,5))


        # ---------------- Responsivity Override (Optional) ----------------
        self.responsivity_label = Label(self.paramsFrame, text='Responsivity R (A/W)')
        self.responsivity_label.grid(column=0, row=4, sticky='W')

        self.responsivity_entry = Entry(self.paramsFrame, width=5)
        self.responsivity_entry.grid(column=0, row=5, sticky='W', padx=(3,0), pady=(0,5))

        # ---------------- Compute Absolute Power Checkbox ----------------
        # 1. Create a Tkinter BooleanVar to track the checkbox state
        self.computeAbsPower_var = BooleanVar()
        self.computeAbsPower_var.set(False) # Default to unchecked
        self.computeAbsPower = False        # The standard boolean you used earlier

        # 2. Create the Checkbutton
        self.compute_power_checkbox = Checkbutton(
            self.paramsFrame, 
            text='Compute Absolute Power', 
            variable=self.computeAbsPower_var,
            command=self.toggle_param_entries # The function to call when clicked
        )
        self.compute_power_checkbox.grid(column=1, row=5, columnspan=3, sticky='W', pady=(10,0))
        
        # 3. Initialize the entries to match the default unchecked state
        self.toggle_param_entries()

        """ Instrument settings frame """
        self.instrFrame = LabelFrame(self.master, text='Instrument Settings')
        # Display device settings frame
        self.instrFrame.grid(column=1, row=2, sticky='NSEW', padx=5, pady=5)
        for c in range(4):
            self.instrFrame.columnconfigure(c, weight=1)
        for r in range(8):
            self.instrFrame.rowconfigure(r, weight=1)

        # Device addresses
        connected_addresses = list(rm.list_resources())
        # Pulser and scope variables
        self.pulse_address = StringVar()
        self.scope_address = StringVar()
        self.thermopile_address = StringVar()

        # If no devices detected
        if size(connected_addresses) == 0:
            connected_addresses = ['No devices detected.']

        # Set the keithley and scope variables to default values
        self.pulse_address.set('Select...')
        self.scope_address.set('Select...')
        self.thermopile_address.set('Select...')

        # Thermopile, oscilloscope buttons
        self.lightMode_var = StringVar()
        self.thermo_radiobutton = Radiobutton(
            self.instrFrame, text='Thermopile', variable=self.lightMode_var, command=self.thermo_selected, value='thermo')
        self.thermo_radiobutton.grid(column=1, row=0, padx=(10, 0), sticky='E')

        self.scope_radiobutton = Radiobutton(
            self.instrFrame, text='Oscilloscope', variable=self.lightMode_var, command=self.osc_selected, value='osc')
        self.scope_radiobutton.grid(column=2, row=0, sticky='E')

        # The default setting for radiobutton is set to linear sweep
        self.lightMode_var.set('osc')

        # Pulser address label
        self.pulse_label = Label(self.instrFrame, text='Pulser address')
        self.pulse_label.grid(column=0, row=0, sticky='W')
        # Pulser address dropdown
        self.pulse_addr = OptionMenu(
            self.instrFrame, self.pulse_address, *connected_addresses)
        self.pulse_addr.grid(column=0, columnspan=2, row=1,
                             padx=5, pady=5, sticky='W')

        # Oscilloscope address label
        self.scope_label = Label(self.instrFrame, text='Oscilloscope address')
        self.scope_label.grid(column=0, row=2, sticky='W')
        # Oscilloscope address dropdown
        self.scope_addr = OptionMenu(
            self.instrFrame, self.scope_address, *connected_addresses)
        self.scope_addr.grid(column=0, columnspan=2, row=3,
                             padx=5, pady=5, sticky='W')

        # Oscilloscope channel options
        channels = [1, 2, 3, 4]
        self.light_channel = IntVar()
        self.current_channel = IntVar()
        self.voltage_channel = IntVar()
        self.trigger_channel = IntVar()

        # Set light channel to 1
        self.light_channel.set(1)
        # Set current channel to 2
        self.current_channel.set(2)
        # Set voltage channel to 3
        self.voltage_channel.set(3)
        # Set trigger channel to 3
        self.trigger_channel.set(3)

        self.light_channel_impedance = StringVar()
        self.light_channel_impedance.set('50' + u'\u03A9')

        light_impedance = ['50' + u'\u03A9', '1M' + u'\u03A9']

        self.light_impedance_dropdown = OptionMenu(self.instrFrame, self.light_channel_impedance, *light_impedance)
        self.light_impedance_dropdown.grid(column=0, row=7, padx=5,pady=(0,5), sticky='W')

        # Light measurement channel label
        self.light_channel_label = Label(self.instrFrame, text='Light address / channel')
        self.light_channel_label.grid(column=0, row=4, sticky='W')

        # --- Thermopile address dropdown (shown in thermopile mode) ---
        self.thermopile_addr = OptionMenu(
            self.instrFrame, self.thermopile_address, *connected_addresses)
        self.thermopile_addr.grid(column=0, columnspan=2, row=5, padx=5, pady=5, sticky='W')

        # --- Oscilloscope light channel dropdown (shown in oscilloscope mode) ---
        self.light_channel_dropdown = OptionMenu(
            self.instrFrame, self.light_channel, *channels)
        self.light_channel_dropdown.grid(column=0, row=5, padx=5, pady=5, sticky='W')

        # Current measurement channel label
        self.curr_channel_label = Label(self.instrFrame, text='Current channel')
        self.curr_channel_label.grid(column=1, row=4)
        # Current measurement channel dropdown
        self.curr_channel_dropdown = OptionMenu(
            self.instrFrame, self.current_channel, *channels)
        self.curr_channel_dropdown.grid(column=1, row=5, pady=(0,10))

        self.curr_imp_label = Label(self.instrFrame, text='Impedance')
        self.curr_imp_label.grid(column=1, row=6, sticky='W')

        curr_impedance = ['50' + u'\u03A9', '1M' + u'\u03A9']

        self.curr_channel_impedance = StringVar()
        self.curr_channel_impedance.set('50' + u'\u03A9')

        self.curr_impedance_dropdown = OptionMenu(self.instrFrame, self.curr_channel_impedance, *curr_impedance)
        self.curr_impedance_dropdown.grid(column=1, row=7, padx=5,pady=(0,5), sticky='W')

        # Voltage measurement channel label
        self.voltage_channel_label = Label(self.instrFrame, text='Voltage channel')
        self.voltage_channel_label.grid(column=2, row=4)
        # Voltage measurement channel dropdown
        self.voltage_channel_dropdown = OptionMenu(
            self.instrFrame, self.voltage_channel, *channels)
        self.voltage_channel_dropdown.grid(column=2, row=5, pady=(0,10))
        
        self.volt_imp_label = Label(self.instrFrame, text='Impedance')
        self.volt_imp_label.grid(column=2, row=6, sticky='W')

        volt_impedance = ['50' + u'\u03A9', '1M' + u'\u03A9']

        self.volt_channel_impedance = StringVar()
        self.volt_channel_impedance.set('50' + u'\u03A9')

        self.volt_impedance_dropdown = OptionMenu(self.instrFrame, self.volt_channel_impedance, *volt_impedance)
        self.volt_impedance_dropdown.grid(column=2, row=7, padx=5,pady=(0,5), sticky='W')
        
        # Trigger channel label
        self.trigger_channel_label = Label(self.instrFrame, text='Trigger channel')
        self.trigger_channel_label.grid(column=3, row=4)
        # Trigger channel dropdown
        self.trigger_channel_dropdown = OptionMenu(
            self.instrFrame, self.trigger_channel, *channels)
        self.trigger_channel_dropdown.grid(column=3, row=5, pady=(0,10))

        # Add Save/Load config buttons
        add_config_buttons(self, self.devFrame, 'VPulse_LIV', row=5)

        self.build_tec_frame()
        self.update_tec_readback() 
