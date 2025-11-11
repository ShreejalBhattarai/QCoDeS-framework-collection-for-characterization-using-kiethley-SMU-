import qcodes as qc
from qcodes.instrument import Instrument
from qcodes.instrument_drivers.tektronix.Keithley_2400 import Keithley2400
import matplotlib.pyplot as plt
import time

# Clean up any existing instance
if 'Keithley2400' in Instrument._all_instruments:
    Instrument._all_instruments['Keithley2400'].close()

# Connect to instrument
visa_address = 'GPIB0::24::INSTR'  # Update if needed
keithley = Keithley2400(name='Keithley2400', address=visa_address)
keithley.reset()

# Configure instrument
keithley.mode('VOLT')        # Source voltage
keithley.sense('CURR')       # Measure current
keithley.rangev(5)           # Voltage range 5 V
keithley.rangei(1e-6)        # Current range 1 µA
keithley.nplci(1)            # Integration time (1 power line cycle)
keithley.compliancei(1e-5)   # Current limit = 10 µA
keithley.output('on')        # Turn output on
print("Status", keithley.output())

# Sweep config
voltages = [round(v * 0.5, 2) for v in range(11)]  # 0.0 V to 5.0 V in 0.5 V steps
currents = []

# Setup real-time plot
plt.ion()
fig, ax = plt.subplots()
line, = ax.plot([], [], 'ro-')
ax.set_xlabel("Voltage (V)")
ax.set_ylabel("Current (A)")
ax.set_title("Live I-V Sweep")
ax.grid(True)


times = []
currents = []
start_time = time.time()
try:
    while True:
        t = time.time() - start_time
        current = keithley.curr()

        times.append(t)
        currents.append(current)

        line.set_xdata(times)
        line.set_ydata(currents)
        ax.relim()
        ax.autoscale_view()
        fig.canvas.draw()
        fig.canvas.flush_events()

        print(f"Time = {t:.1f} s, I = {current:.6e} A")
        time.sleep(0.5)

except KeyboardInterrupt:
    print("Measurement stopped by user.")
    keithley.output('off')
    plt.ioff()
    plt.show()

# Clean up
keithley.output('off')
plt.ioff()
plt.show()
