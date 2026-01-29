import Tkinter as tk
from Tkinter import Label, PhotoImage, Entry, Button, StringVar, OptionMenu, END
import tkMessageBox as messagebox
import pyvisa
from pyvisa.constants import Parity, StopBits, VI_ASRL_FLOW_NONE

rm = pyvisa.ResourceManager()

# Address of Controller
TE_ADDR = 'ASRL9::INSTR'

# Configure LDC-3724B Temperature Controller
# Open resource connection with TE
temp = rm.open_resource(TE_ADDR)

# Serial Port Settings
temp.baud_rate = 115200
temp.data_bits = 8
temp.parity = Parity.none
temp.stop_bits = StopBits.one
temp.flow_control = VI_ASRL_FLOW_NONE
temp.delay = 0.1

temp.read_termination = '\n'
temp.write_termination = '\n'
temp.timeout = 10000

class TEC():

        ### Set temperature on LDC-3724B
    def setTemp (self):
        set_temperature = self.tempInput.get()
        
        # Set temperature
        temp.write("TEC:T " + set_temperature) # Set Controller temperature
        self.setTempLabel.configure(text = 'Set Temperature to ' + set_temperature + '°C')
        self.tempInput.delete(0, END)

    ### Set gain on LDC-3724B
    def setGain(self, gain):
        gain = self.var.get()
        ## Set gain
        temp.write("TEC:GAIN " + gain)
        
        
    ### Current temperature display refreshing once per second
    def getCurrentTemp(self):
        self.currentTemp.configure(text= 'Current Temperature(°C): ' + str(temp.query('TEC:T?')))
        self.currentTemp.after(500, self.getCurrentTemp)

    ### Toggle temperature output for LDC-3724B
    def toggleOutput(self):
        if (temp.query('TEC:OUT?') == '1'):
            temp.write('TEC:OUT 0')
            self.outputLabel = Label(text='The output is off.')
            self.outputLabel.grid(row=5, column=1)
        else:
            temp.write('TEC:OUT 1')
            self.outputLabel = Label(text='The output is on.')
            self.outputLabel.grid(row=5, column=1)

    def __init__(self, parent):
        self.master = parent

        parent.title('LDC-3724B TEC')
        parent.geometry('300x175')
        #self.photo = PhotoImage(file = 'OPREL_resized.gif')
       # parent.call('wm', 'iconphoto',parent._w, self.photo)
        # Enter Temperature Label and Entry Box
        self.label = Label(parent, text = "Enter temperature (°C): ").grid(row = 0)
        self.tempInput = Entry(parent)
        self.tempInput.grid(row = 0, column = 1)
        # Set Temperature Button
        self.tempButton = Button(text='Set Temperature', command=self.setTemp)
        self.tempButton.grid(row = 1, columnspan=2, pady=5)
        self.setTempLabel = Label(parent, text='Click "Set Temperature"')
        self.setTempLabel.grid(row = 2, columnspan=2)
        # Update Current Temperature Button
        self.currentTemp = Label(parent, text= 'Current Temperature(°C): ' + str(temp.query('TEC:T?')))
        self.currentTemp.grid(row = 3, column = 0, columnspan=2)
        self.getCurrentTemp()

        # Gain controls Label
        self.gainLabel = Label(parent, text ='Gain Controls:')
        self.gainLabel.grid(row = 4)
        # Gain Settings Dropdown
        gainList = ('1','3','10','30','100','300')
        self.var = StringVar()
        self.var.set(gainList[0])
        self.setGain('1')
        self.gainMenu = OptionMenu(parent, self.var, *gainList, command=self.setGain)
        self.gainMenu.grid(row = 4, column = 1)
        # Output Toggle Button
        self.outputLabel = Label(text='The output is off.')
        self.outputLabel.grid(row=5, column=1)
        self.outputButton = Button(text='Toggle Output', command=self.toggleOutput)
        self.outputButton.grid(row = 5)

### On closing, ensure the LDC-3724B output is turned off
def on_closing():
    if messagebox.askokcancel('Quit', 'Do you want to quit?'):
        temp.write('TEC:OUT 0')
        root.destroy()

root = tk.Tk()
TEC_gui = TEC(root)
root.protocol('WM_DELETE_WINDOW', on_closing)
root.mainloop()
