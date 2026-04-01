# Oliv (Oprel liv), version 1
# Written by K. Takahashi, 1 April 2026
# Original OLMS code: Thanks to former OPREL staff and an Autumn 2025 OSU ECE capstone group!

from time import sleep, strftime
import numpy as np
from numpy import append, zeros, arange, logspace, log10, size
import os
import subprocess
import matplotlib.pyplot as plt
from tkinter import (Label, Entry, Button, LabelFrame, OptionMenu, Radiobutton,
                     StringVar, IntVar, BooleanVar, Checkbutton, DISABLED, NORMAL, Tk)

from Browse_buttons import browse_plot_file, browse_txt_file
from Oscilloscope_Scaling import incrOscVertScale, channelImpedance
from Update_Trigger import updateTriggerCursor
from live_plot import LivePlotLIV
from config_manager import add_config_buttons
from instruments import init_keithley
from mock_instruments import get_resource_manager

rm = get_resource_manager()

# ── TEC ─────────────────────────────────────────────────────────────
class LDC3724B_TEC:
    def __init__(self, rm, address):
        self.inst = rm.open_resource(address)

    def set_temperature(self, temp_c):
        self.inst.write(f"TEC:T {temp_c}")

    def get_temperature(self):
        return float(self.inst.query("TEC:T?").strip())

    def output_on(self):
        self.inst.write("TEC:OUT 1")

    def output_off(self):
        self.inst.write("TEC:OUT 0")

    def output_state(self):
        return self.inst.query("TEC:OUT?").strip() == "1"

    def close(self):
        self.output_off()
        self.inst.close()


# ── Unified LIV application ────────────────────────────────────────────────────
class LIV_App():

    from adjustVerticalScale import adjustVerticalScale

    # ─────────────────────────────────────────────────────────────────────────
    # Shared instrument helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _init_scope(self, pulse_width_us=None):
        self.scope = rm.open_resource(self.scope_address.get())
        self.scope.write("*RST")
        self.scope.write("*CLS")
        self.scope.write(":CHANnel%d:IMPedance %s" % (
            self.light_channel.get(), channelImpedance(self.light_channel_impedance.get())))
        self.scope.write(":CHANnel%d:IMPedance %s" % (
            self.current_channel.get(), channelImpedance(self.curr_channel_impedance.get())))
        self.scope.write(":CHANnel%d:IMPedance %s" % (
            self.voltage_channel.get(), channelImpedance(self.volt_channel_impedance.get())))
        if pulse_width_us is not None:
            self.scope.write(":TIMebase:RANGe %.6fus" % (0.5 * pulse_width_us * 10))

    def _init_scope_channels(self, vs_l=0.001, vs_c=0.001, vs_v=0.001):
        for ch, scale in [(self.light_channel.get(),   vs_l),
                          (self.current_channel.get(), vs_c),
                          (self.voltage_channel.get(), vs_v)]:
            self.scope.write(":CHANNEL%d:SCALe %.3f" % (ch, scale))
            self.scope.write(":CHANnel%d:DISPlay ON" % ch)
            self.scope.write(":CHANnel%d:OFFset %.3fV" % (ch, 2 * scale))
        return {'light': 6*vs_l, 'current': 6*vs_c, 'voltage': 6*vs_v}

    def _init_thermopile(self):
        self.thermopile = rm.open_resource(self.thermopile_address.get())
        id = self.thermopile.query("*IDN?")
        wavelength = int(self.wavelength_entry.get())
        if "integra" in id.upper():
            self.thermopile.write("*CSU")
            self.thermopile.timeout = 5000
            self.thermopile.write_termination = ''
            self.thermopile.write(f"*PWC{wavelength:05d}")
            print("Thermopile wavelength set to %d nm" % wavelength)
        elif "coherent" in id.upper():
            self.thermopile.write(f"CONFigure:WAVElength {wavelength:05d}")
            print("Thermopile wavelength set to %d nm" % wavelength)
            self.thermopile.write("CONFigure:ZERO")

    def _read_thermopile(self):
        try:
            
            raw = self.thermopile.query('*CVU')
            return float(raw)
        except ValueError:
            print("Thermopile read error")
            return 0.0

    def _read_osc_amplitudes(self):
        def read(ch):
            return self.scope.query_ascii_values(
                "SINGLE;*OPC;:MEASure:VAMPlitude? CHANNEL%d" % ch)[0]
        return (read(self.light_channel.get()),
                read(self.current_channel.get()),
                read(self.voltage_channel.get()))

    def _adjust_all_scales(self, la, ca, va, vs_l, vs_c, vs_v, total):
        vs_l = self.adjustVerticalScale(self.light_channel.get(),
                   self.trigger_channel.get(), la, total['light'],   vs_l)
        vs_c = self.adjustVerticalScale(self.current_channel.get(),
                   self.trigger_channel.get(), ca, total['current'], vs_c)
        vs_v = self.adjustVerticalScale(self.voltage_channel.get(),
                   self.trigger_channel.get(), va, total['voltage'], vs_v)
        return vs_l, vs_c, vs_v, {'light': 6*vs_l, 'current': 6*vs_c, 'voltage': 6*vs_v}

    def _update_trigger_cursors(self, la, ca, va, total):
        trig = self.trigger_channel.get()
        if trig == self.light_channel.get():
            updateTriggerCursor(la, self.scope, total['light'])
        if trig == self.current_channel.get():
            updateTriggerCursor(ca, self.scope, total['current'])
        if trig == self.voltage_channel.get():
            updateTriggerCursor(va, self.scope, total['voltage'])

    # ─────────────────────────────────────────────────────────────────────────
    # Shared file / plot helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _ensure_dir(self, path):
        try:
            if not os.path.exists(path):
                os.makedirs(path)
        except Exception as e:
            print('Error creating directory %s: %s' % (path, e))

    def _make_filename(self, prefix):
        return (self.device_name_entry.get() + '_' + prefix + '_' +
                self.device_temp_entry.get() + 'C_' +
                self.device_dim_entry.get() + '_' +
                self.test_laser_button_var.get())

    def _plot_string(self, test_type):
        return ('Device Name: '   + self.device_name_entry.get() +
                '\nTest Type: '   + test_type +
                '\nTemperature (\u00B0C): ' + self.device_temp_entry.get() +
                '\nDevice Dimensions: ' + self.device_dim_entry.get() +
                ' (\u03BCm x \u03BCm)' +
                '\nTest Structure or Laser: ' + self.test_laser_button_var.get())

    def _save_and_plot_pulsed(self, filename, lightData, currentData, voltageData, test_type):
        """Save txt and matplotlib figure for CP and VP modes."""
        self._ensure_dir(self.txt_dir_entry.get())
        with open(self.txt_dir_entry.get() + '/' + filename + '.txt', 'w+') as fd:
            fd.write('Device light output (W)\tCurrent (mA)\tVoltage (mV)\n')
            for i in range(len(currentData)):
                fd.write('%s\t%s\t%s\n' % (lightData[i], currentData[i], voltageData[i]))

        fig, ax1 = plt.subplots()
        ax2 = ax1.twinx()
        ax1.set_xlabel('Measured device current (mA)')
        ax1.set_ylabel('Measured device voltage (mV)', color='blue')
        ax2.set_ylabel('Measured device light output (W)', color='red')
        ax1.plot(currentData, voltageData, color='blue', label='I-V Characteristic')
        ax2.plot(currentData, lightData,   color='red',  label='L-I Characteristic')
        ax1.legend(loc='upper left')
        plt.figtext(0.02, 0.02, self._plot_string(test_type), fontsize=12)
        plt.subplots_adjust(bottom=0.3)
        self._ensure_dir(self.plot_dir_entry.get())
        plt.savefig(self.plot_dir_entry.get() + '/' + filename + '.png')
        plt.show()

    def _save_and_plot_cw(self, filename, voltage_array, current, light):
        """Save txt and matplotlib figure for CW mode."""
        self._ensure_dir(self.txt_dir_entry.get())
        with open(self.txt_dir_entry.get() + '/' + filename + '.txt', 'w+') as fd:
            fd.write('Device voltage (V)\tDevice current (A)\tPhotodetector output (W)\n')
            for i in range(len(voltage_array)):
                fd.write('%s\t%s\t%s\n' % (round(voltage_array[i], 5), current[i], light[i]))

        fig, ax1 = plt.subplots()
        ax2 = ax1.twinx()
        ax1.set_xlabel('Measured device current (A)')
        ax1.set_ylabel('Measured device voltage (V)', color='blue')
        ax2.set_ylabel('Measured device light output (W)', color='red')
        ax1.plot(current, voltage_array, color='blue', label='I-V Characteristic')
        ax2.plot(current, light,         color='red',  label='L-I Characteristic')
        ax1.legend(loc='upper left')
        plt.figtext(0.02, 0.02, self._plot_string('CW'), fontsize=12)
        plt.subplots_adjust(bottom=0.3)
        self._ensure_dir(self.plot_dir_entry.get())
        plt.savefig(self.plot_dir_entry.get() + '/' + filename + '.png')
        plt.show()

    # ─────────────────────────────────────────────────────────────────────────
    # Origin export (in development)
    # ─────────────────────────────────────────────────────────────────────────

    def _export_to_origin(self, filename, mode='pulsed'):
        txt_path    = (self.txt_dir_entry.get()  + '/' + filename + '.txt').replace('\\', '/')
        opj_path    = (self.plot_dir_entry.get() + '/' + filename + '.opj').replace('\\', '/')
        script_path = (self.plot_dir_entry.get() + '/' + filename + '_import.ogs').replace('\\', '/')
        origin_exe  =  r"C:\Program Files (x86)\Origin Lab\Origin85\Origin85.exe"

        if mode == 'pulsed':
            # Imported: col(1)=L(W), col(2)=I(mA), col(3)=V(mV)
            script = f"""
doc -n;
impasc "{txt_path}" options.hdr.numSubHdr:=1 options.hdr.longnames:=1;

wks.nCols = 7;
col(4) = col(2);            col(4)[L]$ = "Current";      col(4)[U]$ = "mA";
col(5) = col(3) / 1000;    col(5)[L]$ = "Voltage";      col(5)[U]$ = "V";
col(6) = col(1) * 1000;    col(6)[L]$ = "Light Output"; col(6)[U]$ = "mW";
col(7) = col(2) / 1000;    col(7)[L]$ = "Current";      col(7)[U]$ = "A";

wks.col = 4; wks.colDesig = 3;
plotxy (4,6) plot:=200;
layer.x.label$ = "Current (mA)";
layer.y.label$ = "Light Output (mW)";
page.title$ = "L-I {filename}";

wks.col = 5; wks.colDesig = 3;
plotxy (5,7) plot:=200;
layer.x.label$ = "Voltage (V)";
layer.y.label$ = "Current (A)";
page.title$ = "I-V {filename}";

save "{opj_path}";
"""
        else:
            # Imported: col(1)=V(V), col(2)=I(A), col(3)=L(W)
            script = f"""
doc -n;
impasc "{txt_path}" options.hdr.numSubHdr:=1 options.hdr.longnames:=1;

wks.nCols = 6;
col(4) = col(2) * 1000;    col(4)[L]$ = "Current";      col(4)[U]$ = "mA";
col(5) = col(3) * 1000;    col(5)[L]$ = "Light Output"; col(5)[U]$ = "mW";
col(6) = col(2);            col(6)[L]$ = "Current";      col(6)[U]$ = "A";

wks.col = 4; wks.colDesig = 3;
plotxy (4,5) plot:=200;
layer.x.label$ = "Current (mA)";
layer.y.label$ = "Light Output (mW)";
page.title$ = "L-I {filename}";

wks.col = 1; wks.colDesig = 3;
plotxy (1,6) plot:=200;
layer.x.label$ = "Voltage (V)";
layer.y.label$ = "Current (A)";
page.title$ = "I-V {filename}";

save "{opj_path}";
"""

        with open(script_path, 'w') as f:
            f.write(script)
        subprocess.Popen([origin_exe, '-rs', script_path])
        print("Origin launched: %s" % script_path)

    # ─────────────────────────────────────────────────────────────────────────
    # Sweep functions: Constant wave, Voltage pulsed, Current pulsed.
    # ─────────────────────────────────────────────────────────────────────────

    def run_cw(self):
        use_thermo = self.light_mode_var.get() == 'thermo'

        # ── Initialise instruments ────────────────────────────────────────────
        compliance = float(self.compliance_entry.get()) / 1000
        self.keithley = init_keithley(rm, self.smu_address.get(),
                                      source_mode='volt', compliance=compliance)
        if use_thermo:
            self._init_thermopile()
        else:
            self.scope = rm.open_resource(self.scope_address.get())
            self.scope.write("*RST"); self.scope.write("*CLS")
            self.scope.write(":CHANnel%d:IMPedance %s" % (
                self.light_channel.get(),
                channelImpedance(self.light_channel_impedance.get())))
            self.scope.write(":TIMebase:RANGe 2E-6")
            vs_light    = 0.001
            total_light = 6 * vs_light
            self.scope.write(":CHANNEL%d:SCALe %.3f" % (self.light_channel.get(), vs_light))
            self.scope.write(":CHANnel%d:DISPlay ON" % self.light_channel.get())
            self.scope.write(":CHANnel%d:OFFset %.3fV" % (self.light_channel.get(), 2*vs_light))

        # ── Build voltage sweep array ─────────────────────────────────────────
        if self.sweep_var.get() == 'Lin':
            step  = round(float(self.step_size_entry.get()) / 1000, 3)
            start = float(self.start_entry.get())
            stop  = float(self.stop_entry.get())
            arr   = arange(start, stop, step)
            voltage_array = append(arr, stop)
        else:
            pos = logspace(-4, log10(float(self.stop_entry.get())),
                           int(self.num_pts_entry.get()) // 2)
            neg = -logspace(log10(abs(float(self.start_entry.get()))),
                            -4, int(self.num_pts_entry.get()) // 2)
            voltage_array = append(neg, pos)

        current = zeros(len(voltage_array), float)
        light   = zeros(len(voltage_array), float)
        self.live_plot.reset()

        # ── Sweep loop ────────────────────────────────────────────────────────
        for i in range(len(voltage_array)):
            # Set voltage via SMU
            k = rm.open_resource(self.smu_address.get())
            k.write("sour:func volt")
            k.write("sens:curr:rang:auto on")
            k.write("sens:func 'curr'")
            k.write("form:elem curr")
            k.write("outp on")
            k.write("sour:volt:lev " + str(round(voltage_array[i], 3)))
            k.query('READ?')
            sleep(0.1)

            current[i] = eval(self.keithley.query("read?"))

            # ── Light reading branch ──────────────────────────────────────────
            if use_thermo:
                light[i] = self._read_thermopile()
            else:
                l = self.scope.query_ascii_values(
                    "SINGLE;*OPC;:MEASure:VMAX? CHANNEL%d" % self.light_channel.get())[0]
                while l > 0.9 * total_light:
                    vs_light    = incrOscVertScale(vs_light)
                    total_light = 6 * vs_light
                    self.scope.write(":CHANNEL%d:SCALe %.3f" % (self.light_channel.get(), vs_light))
                    l = self.scope.query_ascii_values(
                        "SINGLE;*OPC;:MEASure:VMAX? CHANNEL%d" % self.light_channel.get())[0]
                light[i] = l

            self.live_plot.add_point(current[i]*1000, voltage_array[i]*1000, light[i]*1000)

        # ── Shutdown ──────────────────────────────────────────────────────────
        self.keithley.write("outp off")
        if use_thermo:
            self.thermopile.write('*COU')
        else:
            self.scope.write(":STOP")

        filename = self._make_filename('CW-LIV')
        self._save_and_plot_cw(filename, voltage_array, current, light)
        self._export_to_origin(filename, mode='cw')

    # ─────────────────────────────────────────────────────────────────────────

    def run_cp(self):
        use_thermo = self.light_mode_var.get() == 'thermo'

        # ── Initialise instruments ────────────────────────────────────────────
        self._init_scope(pulse_width_us=float(self.pulse_width_entry.get()) * 2)
        if use_thermo:
            self._init_thermopile()

        self.pulser = rm.open_resource(self.pulser_address.get())
        self.pulser.write("*RST"); self.pulser.write("*CLS")
        self.pulser.write(":PW "      + self.pulse_width_entry.get())
        self.pulser.write(":DIS:LDI")
        self.pulser.write("LIMit:I "  + self.curr_limit_entry.get())
        self.pulser.write("OUTPut OFF")

        # ── Trigger setup ─────────────────────────────────────────────────────
        self.scope.write(":TRIGger:MODE EDGE")
        self.scope.write(":TRIGger:EDGE:SOURce CHANnel%d" % self.trigger_channel.get())
        self.scope.write(":TRIGger:LEVel:ASETup")

        vs_l, vs_c, vs_v = 0.001, 0.002, 0.002
        total = self._init_scope_channels(vs_l, vs_c, vs_v)

        # ── Current sweep values ──────────────────────────────────────────────
        start = float(self.start_entry.get())
        stop  = float(self.stop_entry.get())  + float(self.step_size_entry.get())
        step  = float(self.step_size_entry.get())
        currentSourceValues = np.arange(start, stop, step)

        lightData, currentData, voltageData = [0], [0], [0]
        self.live_plot.reset()
        self.live_plot.add_point(0, 0, 0)

        # ── Sweep loop ────────────────────────────────────────────────────────
        for I_s in currentSourceValues:
            self.pulser.write(":LDI %.3f" % I_s)
            if self.pulser.query(":LDI?") != I_s:
                self.pulser.write(":LDI %.3f" % I_s); sleep(1)
            self.pulser.write("OUTPut ON"); sleep(0.1)
            self.scope.write(":TRIGger:LEVel:ASETup")

            # ── Light reading branch ──────────────────────────────────────────
            if use_thermo:
                la = self._read_thermopile()
            else:
                la, _, _ = self._read_osc_amplitudes()

            ca = self.scope.query_ascii_values(
                "SINGLE;*OPC;:MEASure:VAMPlitude? CHANNEL%d" % self.current_channel.get())[0]
            va = self.scope.query_ascii_values(
                "SINGLE;*OPC;:MEASure:VAMPlitude? CHANNEL%d" % self.voltage_channel.get())[0]

            self._update_trigger_cursors(la, ca, va, total)
            vs_l, vs_c, vs_v, total = self._adjust_all_scales(la, ca, va, vs_l, vs_c, vs_v, total)

            # Second reading after scale adjustment
            if use_thermo:
                la = self._read_thermopile()
            else:
                la, _, _ = self._read_osc_amplitudes()

            ca = self.scope.query_ascii_values(
                "SINGLE;*OPC;:MEASure:VAMPlitude? CHANNEL%d" % self.current_channel.get())[0]
            va = self.scope.query_ascii_values(
                "SINGLE;*OPC;:MEASure:VAMPlitude? CHANNEL%d" % self.voltage_channel.get())[0]

            cd = 2 * ca
            lightData.append(la); currentData.append(cd); voltageData.append(va)
            self.live_plot.add_point(cd*1000, va*1000, la*1000)

        # ── Shutdown ──────────────────────────────────────────────────────────
        currentData[:] = [x*1000 for x in currentData]
        voltageData[:] = [x*1000 for x in voltageData]
        self.pulser.write("OUTPut OFF"); self.pulser.write("*CLS")
        self.scope.write(":STOP")
        if use_thermo:
            self.thermopile.write("*CSU")

        filename = self._make_filename('CP-LIV')
        self._save_and_plot_pulsed(filename, lightData, currentData, voltageData, 'Current Pulsed')
        self._export_to_origin(filename, mode='pulsed')

    # ─────────────────────────────────────────────────────────────────────────

    def run_vp(self):
        use_thermo = self.light_mode_var.get() == 'thermo'
        pulseWidth = float(self.pulse_width_entry.get())

        # ── Initialise instruments ────────────────────────────────────────────
        self._init_scope(pulse_width_us=pulseWidth)
        if use_thermo:
            self._init_thermopile()

        self.pulser = rm.open_resource(self.pulser_address.get())
        self.pulser.write("*RST"); self.pulser.write("*CLS")
        self.pulser.write("OUTPut:IMPedance 50")
        self.pulser.write("SOURce INTernal")
        self.pulser.write("PULSe:WIDTh " + self.pulse_width_entry.get() + "us")
        self.pulser.write("FREQuency "   + self.frequency_entry.get()   + "kHz")
        self.pulser.write("OUTPut ON")

        # ── Trigger setup ─────────────────────────────────────────────────────
        self.scope.write(":TRIGger:MODE GLITch")
        self.scope.write(":TRIGger:GLITch:SOURce CHANnel%d" % self.trigger_channel.get())
        self.scope.write(":TRIGger:GLITch:QUALifier RANGe")
        self.scope.write(":TRIGger:GLITch:RANGe %.6fus,%.6fus" % (
            pulseWidth*0.5, pulseWidth*1.5))
        self.scope.write("TRIGger:GLITch:LEVel 1E-3")

        vs_l, vs_c, vs_v = 0.001, 0.001, 0.001
        total   = self._init_scope_channels(vs_l, vs_c, vs_v)
        seriesR = float(self.series_res_entry.get())

        # ── Voltage sweep values ──────────────────────────────────────────────
        start = float(self.start_entry.get())
        stop  = float(self.stop_entry.get())  + float(self.step_size_entry.get()) / 1000
        step  = float(self.step_size_entry.get()) / 1000
        voltageSourceValues = np.arange(start, stop, step)

        V_glitches = [7.12, 21.6, 68]
        prevV = 0
        lightData, currentData, voltageData = [0], [0], [0]
        self.live_plot.reset()
        self.live_plot.add_point(0, 0, 0)

        # ── Sweep loop ────────────────────────────────────────────────────────
        for V_s in voltageSourceValues:
            if any(prevV <= g < V_s for g in V_glitches):
                self.pulser.write("output off")
                self.pulser.write("volt %.3f" % V_s)
                prevV = V_s; sleep(4)
                continue

            self.pulser.write("VOLT %.3f" % V_s)
            self.pulser.write("OUTPut ON")

            # ── Light reading branch ──────────────────────────────────────────
            if use_thermo:
                la = self._read_thermopile()
            else:
                la, _, _ = self._read_osc_amplitudes()

            ca = self.scope.query_ascii_values(
                "SINGLE;*OPC;:MEASure:VAMPlitude? CHANNEL%d" % self.current_channel.get())[0]
            va = self.scope.query_ascii_values(
                "SINGLE;*OPC;:MEASure:VAMPlitude? CHANNEL%d" % self.voltage_channel.get())[0]

            self._update_trigger_cursors(la, ca, va, total)
            vs_l, vs_c, vs_v, total = self._adjust_all_scales(la, ca, va, vs_l, vs_c, vs_v, total)

            # Second reading after scale adjustment
            if use_thermo:
                la = self._read_thermopile()
            else:
                la, _, _ = self._read_osc_amplitudes()

            ca = self.scope.query_ascii_values(
                "SINGLE;*OPC;:MEASure:VAMPlitude? CHANNEL%d" % self.current_channel.get())[0]
            va = self.scope.query_ascii_values(
                "SINGLE;*OPC;:MEASure:VAMPlitude? CHANNEL%d" % self.voltage_channel.get())[0]

            cd = 2 * ca
            vd = va - seriesR * cd
            lightData.append(la); currentData.append(cd); voltageData.append(vd)
            self.live_plot.add_point(cd*1000, vd*1000, la*1000)
            prevV = V_s

        # ── Shutdown ──────────────────────────────────────────────────────────
        currentData[:] = [x*1000 for x in currentData]
        voltageData[:] = [x*1000 for x in voltageData]
        self.pulser.write("OUTPut OFF"); self.pulser.write("*CLS")
        self.scope.write(":STOP")
        if use_thermo:
            self.thermopile.write("*CSU")

        filename = self._make_filename('VP-LIV')
        self._save_and_plot_pulsed(filename, lightData, currentData, voltageData, 'Voltage Pulsed')
        self._export_to_origin(filename, mode='pulsed')

    # ─────────────────────────────────────────────────────────────────────────
    # Mode / sensor switching
    # ─────────────────────────────────────────────────────────────────────────

    def _update_start_command(self, *args):
        dispatch = {'CW': self.run_cw, 'CP': self.run_cp, 'VP': self.run_vp}
        self.start_button.config(command=dispatch[self.mode_var.get()])

    def _on_mode_change(self, *args):
        mode = self.mode_var.get()
        # Show/hide parameter frames
        self.cw_frame.grid_remove()
        self.pulse_frame.grid_remove()
        if mode == 'CW':
            self.cw_frame.grid()
            self.smu_label.grid();    self.smu_addr_menu.grid()
            self.pulser_label.grid_remove(); self.pulser_addr_menu.grid_remove()
            self.series_res_label.grid_remove(); self.series_res_entry.grid_remove()
            self.curr_limit_label.grid_remove(); self.curr_limit_entry.grid_remove()
            self.frequency_label.grid_remove();  self.frequency_entry.grid_remove()
        elif mode == 'CP':
            self.pulse_frame.grid()
            self.smu_label.grid_remove(); self.smu_addr_menu.grid_remove()
            self.pulser_label.grid();    self.pulser_addr_menu.grid()
            self.series_res_label.grid_remove(); self.series_res_entry.grid_remove()
            self.curr_limit_label.grid(); self.curr_limit_entry.grid()
            self.frequency_label.grid_remove(); self.frequency_entry.grid_remove()
        elif mode == 'VP':
            self.pulse_frame.grid()
            self.smu_label.grid_remove(); self.smu_addr_menu.grid_remove()
            self.pulser_label.grid();    self.pulser_addr_menu.grid()
            self.series_res_label.grid(); self.series_res_entry.grid()
            self.curr_limit_label.grid_remove(); self.curr_limit_entry.grid_remove()
            self.frequency_label.grid(); self.frequency_entry.grid()
        self._update_start_command()

    def _on_format_change(self, *args):
        print('poo')
        # IMPLEMENT: Change LivePlot, data output, parameters for format changes.

    def _on_light_mode_change(self, *args):
        if self.light_mode_var.get() == 'osc':
            self.thermopile_label.grid_remove()
            self.thermopile_addr_menu.grid_remove()

        else:
            
            self.thermopile_label.grid()
            self.thermopile_addr_menu.grid()

    # ─────────────────────────────────────────────────────────────────────────
    # TEC
    # ─────────────────────────────────────────────────────────────────────────

    def init_tec(self):
        if not hasattr(self, 'tec'):
            self.tec = LDC3724B_TEC(rm, self.tec_address.get())

    def set_tec_temp(self):
        self.init_tec()
        self.tec.set_temperature(float(self.tec_temp_entry.get()))
        self.tec.output_on()

    def toggle_tec(self):
        self.init_tec()
        self.tec.output_off() if self.tec.output_state() else self.tec.output_on()

    def update_tec_readback(self):
        if hasattr(self, 'tec'):
            try:
                t = self.tec.get_temperature()
                self.tec_status.config(text=f'Current: {t:.2f} °C')
            except Exception:
                self.tec_status.config(text='TEC read error')
        self.master.after(1000, self.update_tec_readback)

    # ─────────────────────────────────────────────────────────────────────────
    # GUI
    # ─────────────────────────────────────────────────────────────────────────

    def __init__(self, parent):
        self.master = parent
        self.master.title('LIV Measurement')

        # ── Mode + sensor bar ─────────────────────────────────────────────────
        top_bar = LabelFrame(self.master, text='Measurement Mode')
        top_bar.grid(row=0, column=0, columnspan=3, sticky='EW', padx=5, pady=5)

        self.mode_var = StringVar(value='CW')
        Label(top_bar, text='Mode:').grid(row=0, column=0, padx=(10, 2))
        OptionMenu(top_bar, self.mode_var, 'CW', 'CP', 'VP').grid(
            row=0, column=1, padx=5, pady=5)
        self.mode_var.trace_add('write', self._on_mode_change)

        self.format_var = StringVar(value='LIV')
        Label(top_bar, text='Format:').grid(row=0, column=0, padx=(10,2))
        OptionMenu(top_bar, self.format_var, 'LIV', 'LI', 'IV').grid(
            row=0, column=2, padx=5,pady=5)
        self.format_var.trace_add('write', self._on_format_change)

        self.light_mode_var = StringVar(value='osc')
        Label(top_bar, text='Light sensor:').grid(row=0, column=3, padx=(20, 2))
        Radiobutton(top_bar, text='Oscilloscope', variable=self.light_mode_var,
                    value='osc',    command=self._on_light_mode_change).grid(row=0, column=3)
        Radiobutton(top_bar, text='Thermopile',   variable=self.light_mode_var,
                    value='thermo', command=self._on_light_mode_change).grid(row=0, column=4)

        # ── File directories ──────────────────────────────────────────────────
        fileFrame = LabelFrame(self.master, text='File Directories')
        fileFrame.grid(row=1, column=0, sticky='EW', padx=5, pady=5)

        Label(fileFrame, text='Plot directory:').grid(row=0, column=0, sticky='W')
        self.plot_dir_entry = Entry(fileFrame, width=35)
        self.plot_dir_entry.grid(row=0, column=1, padx=3)
        Button(fileFrame, text='Browse',
               command=lambda: browse_plot_file(self)).grid(row=0, column=2)

        Label(fileFrame, text='Text directory:').grid(row=1, column=0, sticky='W')
        self.txt_dir_entry = Entry(fileFrame, width=35)
        self.txt_dir_entry.grid(row=1, column=1, padx=3)
        Button(fileFrame, text='Browse',
               command=lambda: browse_txt_file(self)).grid(row=1, column=2)

        # ── Device settings ───────────────────────────────────────────────────
        devFrame = LabelFrame(self.master, text='Device Settings')
        devFrame.grid(row=1, column=1, sticky='NEW', padx=5, pady=5)

        Label(devFrame, text='Device name:').grid(row=0, column=0, sticky='W')
        self.device_name_entry = Entry(devFrame, width=15)
        self.device_name_entry.grid(row=1, column=0, sticky='W', padx=3)

        Label(devFrame, text='Dimensions (\u03BCm x \u03BCm):').grid(row=0, column=1, sticky='W')
        self.device_dim_entry = Entry(devFrame, width=12)
        self.device_dim_entry.grid(row=1, column=1, sticky='W', padx=3)

        Label(devFrame, text='Temp (\u00B0C):').grid(row=0, column=2, sticky='W')
        self.device_temp_entry = Entry(devFrame, width=6)
        self.device_temp_entry.grid(row=1, column=2, sticky='W', padx=3)

        self.test_laser_button_var = StringVar(value='Laser')
        Radiobutton(devFrame, text='Laser',
                    variable=self.test_laser_button_var,
                    value='Laser').grid(row=2, column=0, sticky='W')
        Radiobutton(devFrame, text='Test Structure',
                    variable=self.test_laser_button_var,
                    value='TestStructure').grid(row=2, column=1, sticky='W')

        add_config_buttons(self, devFrame, 'LIV', row=3)

        # ── CW sweep parameters ───────────────────────────────────────────────
        self.cw_frame = LabelFrame(self.master, text='CW Sweep Parameters')
        self.cw_frame.grid(row=2, column=0, columnspan=2, sticky='EW', padx=5, pady=5)

        Label(self.cw_frame, text='Start (V)').grid(row=0, column=0, padx=5)
        self.start_entry = Entry(self.cw_frame, width=7)
        self.start_entry.grid(row=1, column=0, padx=5)

        Label(self.cw_frame, text='Stop (V)').grid(row=0, column=1, padx=5)
        self.stop_entry = Entry(self.cw_frame, width=7)
        self.stop_entry.grid(row=1, column=1, padx=5)

        Label(self.cw_frame, text='Step (mV)').grid(row=0, column=2, padx=5)
        self.step_size_entry = Entry(self.cw_frame, width=7)
        self.step_size_entry.grid(row=1, column=2, padx=5)

        Label(self.cw_frame, text='# Points').grid(row=0, column=3, padx=5)
        self.num_pts_entry = Entry(self.cw_frame, width=7)
        self.num_pts_entry.grid(row=1, column=3, padx=5)
        self.num_pts_entry.config(state=DISABLED)

        Label(self.cw_frame, text='Compliance (mA)').grid(row=0, column=4, padx=5)
        self.compliance_entry = Entry(self.cw_frame, width=7)
        self.compliance_entry.grid(row=1, column=4, padx=5)

        lin_log = LabelFrame(self.cw_frame, text='Sweep type')
        lin_log.grid(row=0, column=5, rowspan=2, padx=10)
        self.sweep_var = StringVar(value='Lin')
        Radiobutton(lin_log, text='Lin', variable=self.sweep_var, value='Lin',
                    command=lambda: self.num_pts_entry.config(state=DISABLED)).grid(row=0, column=0)
        Radiobutton(lin_log, text='Log', variable=self.sweep_var, value='Log',
                    command=lambda: self.num_pts_entry.config(state=NORMAL)).grid(row=0, column=1)

        # ── Pulse parameters ──────────────────────────────────────────────────
        self.pulse_frame = LabelFrame(self.master, text='Pulse Parameters')
        self.pulse_frame.grid(row=2, column=0, columnspan=2, sticky='EW', padx=5, pady=5)
        self.pulse_frame.grid_remove()

        Label(self.pulse_frame, text='Start').grid(row=0, column=0, padx=5)
        self.start_entry = Entry(self.pulse_frame, width=7)
        self.start_entry.grid(row=1, column=0, padx=5)

        Label(self.pulse_frame, text='Stop').grid(row=0, column=1, padx=5)
        self.stop_entry = Entry(self.pulse_frame, width=7)
        self.stop_entry.grid(row=1, column=1, padx=5)

        Label(self.pulse_frame, text='Step').grid(row=0, column=2, padx=5)
        self.step_size_entry = Entry(self.pulse_frame, width=7)
        self.step_size_entry.grid(row=1, column=2, padx=5)

        Label(self.pulse_frame, text='Pulse Width (\u03BCs)').grid(row=0, column=3, padx=5)
        self.pulse_width_entry = Entry(self.pulse_frame, width=7)
        self.pulse_width_entry.grid(row=1, column=3, padx=5)

        self.frequency_label = Label(self.pulse_frame, text='Frequency (kHz)')
        self.frequency_label.grid(row=0, column=4, padx=5)
        self.frequency_entry = Entry(self.pulse_frame, width=7)
        self.frequency_entry.grid(row=1, column=4, padx=5)

        self.series_res_label = Label(self.pulse_frame, text='Series R (\u03A9)')
        self.series_res_label.grid(row=0, column=5, padx=5)
        self.series_res_entry = Entry(self.pulse_frame, width=7)
        self.series_res_entry.grid(row=1, column=5, padx=5)

        self.curr_limit_label = Label(self.pulse_frame, text='Current Limit (mA)')
        self.curr_limit_label.grid(row=0, column=6, padx=5)
        self.curr_limit_entry = Entry(self.pulse_frame, width=7)
        self.curr_limit_entry.grid(row=1, column=6, padx=5)

        # ── Instrument settings ───────────────────────────────────────────────
        instrFrame = LabelFrame(self.master, text='Instrument Settings')
        instrFrame.grid(row=3, column=0, columnspan=3, sticky='EW', padx=5, pady=5)

        connected_addresses = list(rm.list_resources()) or ['No devices detected.']

        self.smu_address        = StringVar(value='Select...')
        self.pulser_address     = StringVar(value='Select...')
        self.scope_address      = StringVar(value='Select...')
        self.thermopile_address = StringVar(value='Select...')

        self.smu_label = Label(instrFrame, text='SMU address')
        self.smu_label.grid(row=0, column=0, sticky='W', padx=5)
        self.smu_addr_menu = OptionMenu(instrFrame, self.smu_address, *connected_addresses)
        self.smu_addr_menu.grid(row=1, column=0, padx=5, pady=3, sticky='W')

        self.pulser_label = Label(instrFrame, text='Pulser address')
        self.pulser_label.grid(row=0, column=0, sticky='W', padx=5)
        self.pulser_addr_menu = OptionMenu(instrFrame, self.pulser_address, *connected_addresses)
        self.pulser_addr_menu.grid(row=1, column=0, padx=5, pady=3, sticky='W')
        self.pulser_label.grid_remove()
        self.pulser_addr_menu.grid_remove()

        Label(instrFrame, text='Oscilloscope address').grid(row=0, column=1, sticky='W', padx=5)
        OptionMenu(instrFrame, self.scope_address,
                   *connected_addresses).grid(row=1, column=1, padx=5, pady=3, sticky='W')

        self.thermopile_label = Label(instrFrame, text='Thermopile address')
        self.thermopile_label.grid(row=0, column=2, sticky='W', padx=5)
        self.thermopile_addr_menu = OptionMenu(
            instrFrame, self.thermopile_address, *connected_addresses)
        self.thermopile_addr_menu.grid(row=1, column=2, padx=5, pady=3, sticky='W')
        self.thermopile_label.grid_remove()
        self.thermopile_addr_menu.grid_remove()

        Label(instrFrame, text='Wavelength (nm)').grid(row=0, column=3, sticky='W', padx=5)
        self.wavelength_entry = Entry(instrFrame, width=7)
        self.wavelength_entry.grid(row=1, column=3, padx=5)

        # Oscilloscope channels
        self.osc_channels_frame = LabelFrame(instrFrame, text='Oscilloscope Channels')
        self.osc_channels_frame.grid(row=2, column=0, columnspan=5,
                                     sticky='EW', padx=5, pady=5)

        channels = [1, 2, 3, 4]
        self.light_channel   = IntVar(value=1)
        self.current_channel = IntVar(value=2)
        self.voltage_channel = IntVar(value=4)
        self.trigger_channel = IntVar(value=4)

        imp_opts = ['50\u03A9', '1M\u03A9']
        self.light_channel_impedance = StringVar(value='50\u03A9')
        self.curr_channel_impedance  = StringVar(value='50\u03A9')
        self.volt_channel_impedance  = StringVar(value='50\u03A9')

        for col, (lbl, ch_var, imp_var) in enumerate([
            ('Light channel',   self.light_channel,   self.light_channel_impedance),
            ('Current channel', self.current_channel, self.curr_channel_impedance),
            ('Voltage channel', self.voltage_channel, self.volt_channel_impedance),
        ]):
            Label(self.osc_channels_frame, text=lbl).grid(row=0, column=col, padx=8)
            OptionMenu(self.osc_channels_frame, ch_var, *channels).grid(row=1, column=col, padx=8)
            Label(self.osc_channels_frame, text='Impedance').grid(row=2, column=col)
            OptionMenu(self.osc_channels_frame, imp_var,
                       *imp_opts).grid(row=3, column=col, padx=8, pady=(0, 5))

        Label(self.osc_channels_frame, text='Trigger channel').grid(row=0, column=3, padx=8)
        OptionMenu(self.osc_channels_frame, self.trigger_channel,
                   *channels).grid(row=1, column=3, padx=8)

        # ── TEC ───────────────────────────────────────────────────────────────
        tecFrame = LabelFrame(self.master, text='LDC-3724B TEC')
        tecFrame.grid(row=1, column=2, sticky='NEW', padx=5, pady=5)

        self.tec_address = StringVar(value='Select...')
        Label(tecFrame, text='TEC address').grid(row=0, column=0, sticky='W')
        OptionMenu(tecFrame, self.tec_address, *connected_addresses).grid(row=0, column=1)

        Label(tecFrame, text='Temp. to Set (\u00B0C)').grid(row=1, column=0, sticky='W')
        self.tec_temp_entry = Entry(tecFrame, width=6)
        self.tec_temp_entry.grid(row=1, column=1)

        self.tec_status = Label(tecFrame, text='Current: --- \u00B0C')
        self.tec_status.grid(row=2, column=0, columnspan=2)

        Button(tecFrame, text='Send Temp.',
               command=self.set_tec_temp).grid(row=3, column=0)
        Button(tecFrame, text='Toggle Output',
               command=self.toggle_tec).grid(row=3, column=1)

        # ── Live plot ─────────────────────────────────────────────────────────
        plotFrame = LabelFrame(self.master, text='Live Plot')
        plotFrame.grid(row=4, column=0, columnspan=3, sticky='NSEW', padx=5, pady=5)
        self.live_plot = LivePlotLIV(plotFrame)

        # ── Start button ──────────────────────────────────────────────────────
        self.start_button = Button(self.master, text='Start',
                                   width=15, command=self.run_cw)
        self.start_button.grid(row=5, column=0, columnspan=3, pady=10)

        # Trigger initial layout
        self._on_mode_change()
        self._on_format_change()
        self._on_light_mode_change()
        self.update_tec_readback()


# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    root = Tk()
    app = LIV_App(root)
    root.mainloop()
