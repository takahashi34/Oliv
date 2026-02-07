import tkinter as tk
from tkinter import Label, Entry, Button, StringVar, OptionMenu, END, messagebox
import pyvisa

rm = pyvisa.ResourceManager()

# Address of Controller
TE_ADDR = 'GPIB0::2::INSTR'

# Open resource connection
temp = rm.open_resource(TE_ADDR)


class TEC:

    def setTemp(self):
        set_temperature = self.tempInput.get()
        temp.write(f"TEC:T {set_temperature}")
        self.setTempLabel.config(
            text=f"Set Temperature to {set_temperature} C"
        )
        self.tempInput.delete(0, END)

    def setGain(self, value):
        temp.write(f"TEC:GAIN {value}")

    def getCurrentTemp(self):
        current = temp.query('TEC:T?').strip()
        self.currentTemp.config(
            text=f"Current Temperature (C): {current}"
        )
        self.currentTemp.after(1000, self.getCurrentTemp)

    def toggleOutput(self):
        state = temp.query('TEC:OUT?').strip()
        if state == '1':
            temp.write('TEC:OUT 0')
            self.outputLabel.config(text='The output is off.')
        else:
            temp.write('TEC:OUT 1')
            self.outputLabel.config(text='The output is on.')

    def __init__(self, parent):
        self.master = parent
        parent.title('LDC-3724B TEC')
        parent.geometry('300x175')

        Label(parent, text="Enter temperature (C):").grid(row=0)
        self.tempInput = Entry(parent)
        self.tempInput.grid(row=0, column=1)

        Button(parent, text='Set Temperature',
               command=self.setTemp).grid(row=1, columnspan=2, pady=5)

        self.setTempLabel = Label(parent, text='Click "Set Temperature"')
        self.setTempLabel.grid(row=2, columnspan=2)

        self.currentTemp = Label(parent, text='Current Temperature (C): ---')
        self.currentTemp.grid(row=3, columnspan=2)
        self.getCurrentTemp()

        Label(parent, text='Gain Controls:').grid(row=4)

        gainList = ('1', '3', '10', '30', '100', '300')
        self.var = StringVar(value=gainList[0])
        self.setGain(gainList[0])

        OptionMenu(parent, self.var, *gainList,
                   command=self.setGain).grid(row=4, column=1)

        self.outputLabel = Label(parent, text='The output is off.')
        self.outputLabel.grid(row=5, column=1)

        Button(parent, text='Toggle Output',
               command=self.toggleOutput).grid(row=5)


def on_closing():
    if messagebox.askokcancel('Quit', 'Do you want to quit?'):
        temp.write('TEC:OUT 0')
        temp.close()
        rm.close()
        root.destroy()


root = tk.Tk()
TEC_gui = TEC(root)
root.protocol('WM_DELETE_WINDOW', on_closing)
root.mainloop()
