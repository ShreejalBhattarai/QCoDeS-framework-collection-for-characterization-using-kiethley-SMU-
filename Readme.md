# mosfet_iv_qcodes

A modular Python toolkit for measuring MOSFET IV (current-voltage) characteristics using [QCoDeS](https://qcodes.github.io/Qcodes/). Data is streamed to a **live plot window** via [plottr](https://github.com/toolsforexperiments/plottr) so you can watch the curves build in real-time during the sweep.

---

## Instruments

| Instrument | Terminal | Role |
|---|---|---|
| Keithley 2400 SMU #1 | Drain | Forces V_DS, measures I_D |
| Keithley 2400 SMU #2 | Source | Holds 0 V ground reference |
| Rigol DG822 Pro AWG | Gate | Supplies DC gate voltage V_GS |

---

## Table of Contents

1. [What This Code Does](#what-this-code-does)
2. [Hardware Setup](#hardware-setup)
3. [Software Requirements](#software-requirements)
4. [Installation](#installation)
5. [Finding Your VISA Addresses](#finding-your-visa-addresses)
6. [Configuration](#configuration)
7. [Running the Measurement](#running-the-measurement)
8. [Repository Structure](#repository-structure)
9. [Module Reference](#module-reference)
   - [configure_libraries.py](#configure_librariespy)
   - [instruments/keithley.py](#instrumentskeithleypy)
   - [instruments/rigol.py](#instrumentsrigolpy)
   - [analysis/live_plot.py](#analysislive_plotpy)
   - [main.py](#mainpy)
10. [Understanding the Output](#understanding-the-output)
11. [Extending the Project](#extending-the-project)
12. [Troubleshooting](#troubleshooting)

---

## What This Code Does

When you run `python main.py`, the program:

1. Opens a live **plottr** window on your screen
2. Connects to all three instruments over GPIB and USB
3. Runs an **output IV sweep** — for each gate voltage in `VGS_VALUES`, it sweeps the drain voltage from `VDS_START` to `VDS_STOP` and reads the drain current at each point
4. Streams every measurement point to the live plot as it is taken — you watch the curves grow in real time
5. Saves the complete results to `data/iv_results.npz` when the sweep finishes
6. Keeps the plot window open until you close it

The result is a **family of I_D vs V_DS curves**, one per gate voltage, which is the standard characterisation of a MOSFET's output behaviour.

---

## Hardware Setup

### Wiring Diagram

```
┌─────────────────────┐
│   Rigol DG822 Pro   │
│                     │
│  CH1 OUTPUT ────────┼─────────────────── Gate  (G) ─┐
│  CH1 GND    ────────┼──────────────┐                 │
└─────────────────────┘              │                 │
                                     │    ┌────────────┴────────┐
┌─────────────────────┐              │    │                     │
│  Keithley 2400 #1   │              │    │    N-channel MOSFET  │
│  (DRAIN SMU)        │              │    │    (Device Under     │
│                     │              │    │     Test / DUT)      │
│  HI ────────────────┼──────────────┼────┤ Drain  (D)          │
│  LO ────────────────┼──────────────┼────┤ Source (S)          │
└─────────────────────┘              │    └─────────────────────┘
                                     │
┌─────────────────────┐              │
│  Keithley 2400 #2   │              │
│  (SOURCE SMU)       │              │
│                     │              │
│  HI ────────────────┼──────────────┘   ← forced to 0 V
│  LO ────────────────┼─────────────────── Chassis GND
└─────────────────────┘
```

### Connection Rules

- **Gate → Rigol CH1 OUTPUT**: The gate draws essentially zero DC current, so a simple voltage source is sufficient. The Rigol in DC offset mode is ideal — clean, stable, and programmable.
- **Drain → Keithley #1 HI**: This SMU forces V_DS and measures I_D simultaneously. The LO terminal connects to the source/ground.
- **Source → Keithley #2 HI**: This SMU actively holds the source at 0 V throughout the sweep. Its LO terminal connects to chassis ground.
- **All grounds must share a common point** at the MOSFET's source pin. The Rigol GND, both Keithley LO terminals, and the source pin all connect together.

### Physical Cable Types

| Connection | Recommended cable |
|---|---|
| Keithley HI to MOSFET drain | Triax or coax with BNC-to-probe adapter |
| Keithley LO to source/ground | Short low-resistance wire |
| Rigol CH1 to MOSFET gate | BNC-to-probe or low-capacitance coax |
| Keithley to PC | GPIB-USB adapter (e.g. NI GPIB-USB-HS) |
| Rigol to PC | USB-B cable (standard) |

### GPIB Address Assignment

The Keithley 2400 GPIB address is set on the instrument's front panel:
- Press `MENU` → `COMMUNICATION` → `GPIB`
- Set a unique address for each unit (e.g. 24 for drain, 25 for source)
- The addresses in `main.py` must match what you set here

---

## Software Requirements

### Python

Python **3.10 or newer** is required. The multi-context `with` statement syntax used in `main.py` was introduced in Python 3.10.

```bash
python --version   # must be 3.10+
```

### Python Packages

| Package | Version | Purpose |
|---|---|---|
| `qcodes` | ≥ 0.39.0 | Instrument communication framework |
| `numpy` | ≥ 1.24.0 | Numerical arrays and file saving |
| `plottr` | ≥ 0.9.0 | Live plot window |

### System Dependencies

| Dependency | Purpose | Install |
|---|---|---|
| NI-VISA or PyVISA-py | VISA backend for instrument communication | See below |
| NI-488.2 driver | GPIB communication (if using NI GPIB adapter) | [ni.com/gpib](https://www.ni.com/en/support/downloads/drivers/download.ni-488-2.html) |

**VISA backend options:**

- **NI-VISA** (recommended for GPIB): Download from [ni.com](https://www.ni.com/en/support/downloads/drivers/download.ni-visa.html). Free, works on Windows/Linux/macOS.
- **PyVISA-py** (no NI driver needed, USB-only setups): `pip install PyVISA-py`. Note: PyVISA-py does not support GPIB without additional hardware drivers.

---

## Installation

### Step 1 — Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/mosfet_iv_qcodes.git
cd mosfet_iv_qcodes
```

### Step 2 — Create a virtual environment (recommended)

```bash
python -m venv .venv

# Activate it:
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate
```

### Step 3 — Install Python dependencies

```bash
pip install -r requirements.txt
```

### Step 4 — Install NI-VISA (for GPIB)

Download and install NI-VISA from the National Instruments website. After installation, verify it works:

```bash
python -c "import pyvisa; rm = pyvisa.ResourceManager(); print(rm.list_resources())"
```

This should print a tuple of connected VISA resource strings. If your instruments are connected and powered on, their addresses will appear here.

### Step 5 — Verify instrument detection

```bash
python -c "
import pyvisa
rm = pyvisa.ResourceManager()
resources = rm.list_resources()
print('Found instruments:')
for r in resources:
    print(' ', r)
"
```

---

## Finding Your VISA Addresses

Before editing `main.py`, you need the exact VISA address strings for each instrument.

### Option 1 — NI MAX (Windows, recommended for GPIB)

1. Open **NI Measurement & Automation Explorer (NI MAX)**
2. Expand `Devices and Interfaces` → `VISA`
3. Each connected instrument appears with its full VISA address
4. Click on an instrument and press `Open VISA Test Panel` to send a `*IDN?` query and confirm it responds

### Option 2 — Python script

```python
import pyvisa
rm = pyvisa.ResourceManager()
for address in rm.list_resources():
    try:
        instr = rm.open_resource(address)
        idn = instr.query("*IDN?")
        print(f"{address}  →  {idn.strip()}")
        instr.close()
    except Exception as e:
        print(f"{address}  →  could not query: {e}")
```

### Address Formats

```
GPIB::24::INSTR                          ← Keithley on GPIB address 24
GPIB::25::INSTR                          ← Keithley on GPIB address 25
USB0::0x1AB1::0x0643::DG8A241400001::INSTR  ← Rigol via USB
```

The Rigol USB address contains your instrument's serial number. Copy it exactly as shown — it is case-sensitive.

---

## Configuration

All measurement parameters live in the **CONFIG block** near the top of `main.py`. This is the only section you need to edit between experiments.

```python
# ─────────────────────────────────────────────────────────────────── #
#  CONFIG  ← edit this section for your setup
# ─────────────────────────────────────────────────────────────────── #

# VISA addresses — update to match your lab
DRAIN_ADDRESS  = "GPIB::24::INSTR"
SOURCE_ADDRESS = "GPIB::25::INSTR"
GATE_ADDRESS   = "USB0::0x1AB1::0x0643::DG8XXXXXXXX::INSTR"

# Safety limits
DRAIN_COMPLIANCE  = 100e-3   # Amps  — max current allowed on drain
SOURCE_COMPLIANCE = 10e-3    # Amps  — max current allowed on source
GATE_V_LIMIT      = 10.0     # Volts — hard cap on V_GS (protects gate oxide)

# Sweep parameters
VDS_START  = 0.0             # Volts — start of V_DS sweep
VDS_STOP   = 5.0             # Volts — end of V_DS sweep
VDS_POINTS = 100             # number of V_DS steps

VGS_VALUES = [0.0, 1.0, 2.0, 3.0, 4.0]   # Gate voltages to step through (Volts)

SETTLING_TIME = 0.05         # Seconds to wait after each voltage step

# Where to save results
OUTPUT_FILE = "data/iv_results.npz"
```

### Parameter Guide

| Parameter | What to set it to |
|---|---|
| `DRAIN_ADDRESS` | VISA address of the Keithley connected to the MOSFET drain |
| `SOURCE_ADDRESS` | VISA address of the Keithley connected to the MOSFET source |
| `GATE_ADDRESS` | VISA address of the Rigol DG822 Pro |
| `DRAIN_COMPLIANCE` | Set to ~10–20% above the maximum I_D you expect. Default 100 mA is safe for most signal-level MOSFETs |
| `SOURCE_COMPLIANCE` | Keep low (10 mA). The source should draw almost no current. A reading here means something is wrong |
| `GATE_V_LIMIT` | Check your MOSFET datasheet for V_GS(max). Never exceed it. Default 10 V is conservative |
| `VDS_START` | Almost always 0.0 V |
| `VDS_STOP` | Check your MOSFET's V_DS(max). Typically 20–60 V for power MOSFETs, 5–10 V for small signal |
| `VDS_POINTS` | 50–100 is typical. More points = smoother curves but slower sweep |
| `VGS_VALUES` | Choose values that span from below V_th to above it. Start with a coarse range then refine once you know V_th |
| `SETTLING_TIME` | 50 ms (0.05) is safe for most devices. Reduce to 10 ms for faster sweeps, increase to 200 ms for high-capacitance devices or noisy measurements |

### Example: Power MOSFET (e.g. IRFZ44N)

```python
DRAIN_COMPLIANCE  = 500e-3        # 500 mA
GATE_V_LIMIT      = 20.0          # IRFZ44N V_GS(max) = ±20 V
VDS_STOP          = 10.0          # Stay well below V_DS(max) = 55 V
VGS_VALUES        = [0, 2, 3, 4, 5, 6, 8, 10]  # V_th is ~2–4 V
SETTLING_TIME     = 0.1           # Power devices have more capacitance
```

### Example: Small Signal MOSFET (e.g. 2N7000)

```python
DRAIN_COMPLIANCE  = 50e-3         # 50 mA
GATE_V_LIMIT      = 10.0
VDS_STOP          = 5.0
VGS_VALUES        = [0, 1, 1.5, 2.0, 2.5, 3.0]
SETTLING_TIME     = 0.05
```

---

## Running the Measurement

### Pre-flight checklist

- [ ] All three instruments powered on and warmed up (allow 15 minutes for Keithley accuracy spec)
- [ ] MOSFET wired correctly — Gate to Rigol, Drain to Keithley #1, Source to Keithley #2
- [ ] All grounds connected to a common point at the Source pin
- [ ] GPIB cable connected from both Keithleys to the GPIB-USB adapter
- [ ] USB cable connected from Rigol to PC
- [ ] VISA addresses confirmed (see [Finding Your VISA Addresses](#finding-your-visa-addresses))
- [ ] CONFIG block in `main.py` updated with your addresses and sweep parameters
- [ ] Compliance limits set safely for your specific MOSFET

### Run

```bash
python main.py
```

### What you will see

**In the terminal:**
```
10:23:01 | INFO    | instruments.keithley | [drain] connecting at GPIB::24::INSTR
10:23:02 | INFO    | instruments.keithley | [drain] connected
10:23:02 | INFO    | instruments.keithley | [source] connecting at GPIB::25::INSTR
10:23:03 | INFO    | instruments.keithley | [source] connected
10:23:03 | INFO    | instruments.rigol    | [gate] connecting at USB0::...
10:23:04 | INFO    | instruments.rigol    | [gate] connected
10:23:04 | INFO    | main | ─────────────────────────────────────────────
10:23:04 | INFO    | main | Output IV sweep started
10:23:04 | INFO    | main |   V_DS : 0.0 → 5.0 V  (100 pts)
10:23:04 | INFO    | main |   V_GS : [0.0, 1.0, 2.0, 3.0, 4.0]
10:23:04 | INFO    | main | ─────────────────────────────────────────────
10:23:04 | INFO    | main | Step 1/5  V_GS = 0.00 V
10:23:10 | INFO    | main | Step 2/5  V_GS = 1.00 V
...
10:23:40 | INFO    | main | Sweep complete.
10:23:40 | INFO    | main | Results saved → data/iv_results.npz
10:23:40 | INFO    | main | Sweep done — close the plot window to exit.
```

**On screen:** A plottr window opens and each IV curve appears point by point as the sweep progresses. After the sweep finishes, the complete family of curves is displayed and remains visible until you close the window.

### Stopping mid-sweep

Press `Ctrl+C` at any time. Python's `with` block guarantees that all instruments ramp to 0 V and disconnect safely even if interrupted.

---

## Repository Structure

```
mosfet_iv_qcodes/
│
├── main.py                      ← Run this. Edit the CONFIG block at the top.
│
├── configure_libraries.py       ← All imports live here. One file only.
│
├── instruments/
│   ├── __init__.py              ← Exports Keithley2400Controller and RigolDG822Controller
│   ├── keithley.py              ← Keithley 2400 SMU controller class
│   └── rigol.py                 ← Rigol DG822 Pro AWG controller class
│
├── analysis/
│   ├── __init__.py              ← Exports LiveIVPlot
│   └── live_plot.py             ← Real-time plottr plot manager class
│
├── requirements.txt             ← Python package dependencies
├── .gitignore                   ← Excludes data/, logs/, __pycache__/, etc.
└── README.md                    ← This file
```

### Why This Structure

Each layer depends only on the layers below it, not sideways or upward:

```
main.py
  └── imports from instruments/  and  analysis/
        └── both import from configure_libraries.py only
```

This means you can change an instrument driver without touching the plot code, and vice versa. You can add a new instrument by adding one file to `instruments/` without editing anything else.

---

## Module Reference

### `configure_libraries.py`

**The single import hub.** Every external library and standard library module used anywhere in the project is imported here. All other files do `from configure_libraries import <thing>` and never write their own `import` statements.

```python
# Standard library
import time           # time.sleep() for settling delays
import logging        # logging.getLogger() for timestamped log messages
from pathlib import Path    # Path() for cross-platform file/folder handling
from typing import Optional # Optional[str] type hints in function signatures

# Numerical
import numpy as np    # np.linspace(), np.array(), np.savez()

# QCoDeS instrument drivers
from qcodes.instrument_drivers.tektronix.Keithley_2400 import Keithley2400
from qcodes.instrument_drivers.rigol.DG800 import RigolDG800

# Plottr live plotting
from plottr.data.datadict import DataDict
from plottr.apps.autoplot import autoplot
```

**To add a new library:** install it with pip, add the import here, then use `from configure_libraries import <name>` in the file that needs it.

---

### `instruments/keithley.py`

**Class:** `Keithley2400Controller`

Controls a single Keithley 2400 SMU. Used twice in `main.py` — once as the drain SMU and once as the source SMU.

#### Constructor

```python
Keithley2400Controller(name, address, compliance=100e-3)
```

| Parameter | Type | Description |
|---|---|---|
| `name` | `str` | Unique label used internally by QCoDeS. Must be different for each instrument instance. E.g. `"drain"`, `"source"` |
| `address` | `str` | VISA resource string. E.g. `"GPIB::24::INSTR"` |
| `compliance` | `float` | Current compliance limit in Amps. Default 100 mA. The SMU will never allow current to exceed this value |

#### Methods

| Method | Description |
|---|---|
| `connect()` | Opens VISA session, configures voltage mode, sets 0 V, applies compliance, leaves output OFF |
| `disconnect()` | Ramps to 0 V, waits 50 ms, turns output off, closes VISA session |
| `output_on()` | Activates the SMU output — voltage appears on terminals |
| `output_off()` | Deactivates the SMU output |
| `set_voltage(v)` | Forces voltage `v` (Volts) on this terminal |
| `measure_current()` | Reads and returns the measured current (Amps) |

#### Context Manager

```python
with Keithley2400Controller("drain", "GPIB::24::INSTR", 100e-3) as drain:
    drain.set_voltage(3.5)
    i = drain.measure_current()
# disconnect() called automatically here — even if an exception occurred
```

#### Safety Features

- Output starts OFF on connection. Must call `output_on()` explicitly to activate.
- Compliance current clamps output current at hardware level — not just software.
- `disconnect()` always ramps to 0 V before shutting off to prevent voltage spikes.

---

### `instruments/rigol.py`

**Class:** `RigolDG822Controller`

Controls the Rigol DG822 Pro, using it purely as a DC voltage source for the MOSFET gate. The AWG is locked into DC offset mode — it does not output any waveform.

#### Constructor

```python
RigolDG822Controller(name, address, channel=1, v_limit=10.0)
```

| Parameter | Type | Description |
|---|---|---|
| `name` | `str` | Unique label. E.g. `"gate"` |
| `address` | `str` | VISA resource string. E.g. `"USB0::0x1AB1::0x0643::DG8A...::INSTR"` |
| `channel` | `int` | AWG channel number. Default `1`. Change to `2` if wired to CH2 |
| `v_limit` | `float` | Maximum gate voltage in Volts. Any `set_voltage()` call above this raises `ValueError` before touching the instrument. Default 10 V |

#### Methods

| Method | Description |
|---|---|
| `connect()` | Opens VISA session, sets DC mode, 0 V offset, output OFF |
| `disconnect()` | Sets offset to 0 V, turns output off, closes VISA session |
| `output_on()` | Activates channel output |
| `output_off()` | Deactivates channel output |
| `set_voltage(vgs)` | Sets gate voltage V_GS. Raises `ValueError` if `abs(vgs) > v_limit` |
| `get_voltage()` | Returns the currently programmed gate voltage (Volts) |

#### Context Manager

```python
with RigolDG822Controller("gate", "USB0::...", v_limit=10.0) as gate:
    gate.set_voltage(2.5)
# disconnect() called automatically here
```

#### Safety Features

- `v_limit` is enforced in `set_voltage()` before any SCPI command is sent. The instrument is never commanded beyond this value.
- Gate voltage resets to 0 V on disconnect.

---

### `analysis/live_plot.py`

**Class:** `LiveIVPlot`

Manages a plottr live plot window. Opens the window before the sweep starts and accepts data point-by-point as they are measured, redrawing after each one.

#### Constructor

```python
LiveIVPlot(title="MOSFET IV Curves", x_label="V_DS (V)", y_label="I_D (mA)")
```

| Parameter | Type | Description |
|---|---|---|
| `title` | `str` | Window title bar text |
| `x_label` | `str` | X-axis label (for reference — passed to DataDict) |
| `y_label` | `str` | Y-axis label (for reference — passed to DataDict) |

#### Methods

| Method | When to call | Description |
|---|---|---|
| `start()` | Once, before the sweep | Creates the DataDict schema and opens the plottr Qt window |
| `new_curve(label=None)` | Once per V_GS step, before inner loop | Resets internal x/y buffers. New points go to a fresh curve |
| `add_point(x, y_amps)` | Once per measurement point | Appends point, rebuilds arrays, pushes to plottr, redraws window |
| `stop()` | Once, after sweep complete | Enters Qt event loop — blocks until user closes window |

#### How plottr live updating works

plottr uses a `DataDict` object as its data container. After each `add_point()` call:

1. The new (x, y) pair is appended to internal Python lists
2. The lists are converted to numpy arrays and written into the `DataDict`
3. `fc.setData(datadict)` pushes the updated DataDict into the plottr flowchart
4. `app.processEvents()` forces the Qt window to repaint immediately

This happens synchronously inside the measurement loop, so the plot updates as fast as the measurement loop runs.

---

### `main.py`

The entry point and orchestration layer. Contains three sections: config, sweep function, and the `main()` entry point.

#### CONFIG block

All measurement parameters as module-level constants (ALL_CAPS). Edit this section only — no other changes needed for typical experiments.

#### `run_output_iv(drain, source, gate, plotter)`

The sweep function. Accepts the three instrument controllers and the plotter as arguments. Returns a `results` dictionary:

```python
{
    "vds":       np.ndarray,          # shape (VDS_POINTS,) — the V_DS sweep axis
    "vgs_values": list,               # the VGS_VALUES list from config
    "id": {
        0.0: np.ndarray,              # I_D measurements at V_GS = 0.0 V
        1.0: np.ndarray,              # I_D measurements at V_GS = 1.0 V
        ...                           # one entry per V_GS value
    }
}
```

All currents in the `id` dict are in **Amps**. The plotter converts to mA for display.

#### `save_results(results, path)`

Saves the results dictionary to a NumPy `.npz` file. The file contains named arrays:

```
vds           → the shared V_DS axis array
id_vgs_0p0    → I_D array for V_GS = 0.0 V
id_vgs_1p0    → I_D array for V_GS = 1.0 V
id_vgs_2p0    → I_D array for V_GS = 2.0 V
...
```

Load the data later with:

```python
import numpy as np
data = np.load("data/iv_results.npz")
vds = data["vds"]
id_at_vgs2 = data["id_vgs_2p0"]   # I_D in Amps at V_GS = 2.0 V
```

#### `main()`

Wires everything together:
1. Creates and starts the live plotter
2. Opens all three instruments in a single `with` block
3. Calls `run_output_iv()` inside the `with` block
4. `with` block exits → all instruments disconnect safely
5. Saves results to disk
6. Calls `plotter.stop()` to keep the window open

The `if __name__ == "__main__": main()` guard at the bottom means `main()` only runs when the file is executed directly (`python main.py`), not when imported by another script.

---

## Understanding the Output

### IV Curve Shape

A healthy N-channel enhancement MOSFET produces the following family of curves:

```
I_D (mA)
  ^
  |          V_GS = 4 V ───────────────────────────────
  |       V_GS = 3 V ────────────────────────
  |    V_GS = 2 V ─────────────────
  | V_GS = 1 V ──────
  | V_GS = 0 V ─ (near zero across entire V_DS range)
  └──────────────────────────────────────────> V_DS (V)
       linear region | saturation region
```

- **Left side (linear region):** Current rises steeply. MOSFET acts as a voltage-controlled resistor.
- **Knee:** Transition point at approximately V_DS = V_GS − V_th.
- **Right side (saturation region):** Current flattens. MOSFET acts as a current source controlled only by V_GS.

### Loaded data example

```python
import numpy as np
import matplotlib.pyplot as plt

data = np.load("data/iv_results.npz")
vgs_values = [0.0, 1.0, 2.0, 3.0, 4.0]

for vgs in vgs_values:
    key = f"id_vgs_{str(vgs).replace('.', 'p')}"
    id_mA = data[key] * 1000   # Amps to mA
    plt.plot(data["vds"], id_mA, label=f"V_GS = {vgs} V")

plt.xlabel("V_DS (V)")
plt.ylabel("I_D (mA)")
plt.legend()
plt.grid(True)
plt.show()
```

---

## Extending the Project

### Adding a transfer curve sweep (I_D vs V_GS)

Add a new function to `main.py` following the same pattern as `run_output_iv()`, but swap which loop is inner and outer:

```python
def run_transfer_iv(drain, source, gate, plotter):
    """Transfer IV sweep: I_D vs V_GS at fixed V_DS values."""
    vgs_array = np.linspace(0.0, 4.0, 100)
    vds_values = [0.5, 1.0, 2.0, 5.0]
    results = {"vgs": vgs_array, "vds_values": vds_values, "id": {}}

    for vds in vds_values:
        plotter.new_curve(label=f"V_DS = {vds:.1f} V")
        drain.set_voltage(vds)
        time.sleep(SETTLING_TIME)

        id_values = []
        for vgs in vgs_array:
            gate.set_voltage(vgs)
            time.sleep(SETTLING_TIME)
            id_meas = drain.measure_current()
            id_values.append(id_meas)
            plotter.add_point(x=vgs, y_amps=id_meas)

        results["id"][vds] = np.array(id_values)

    drain.set_voltage(0)
    gate.set_voltage(0)
    return results
```

Then call it inside the `with` block in `main()`.

### Adding a new instrument

1. Create `instruments/your_instrument.py`
2. Follow the same class pattern: `__init__`, `connect`, `disconnect`, `__enter__`, `__exit__`
3. Add all its imports to `configure_libraries.py`
4. Add `from .your_instrument import YourClass` to `instruments/__init__.py`

### Adding a new library

1. `pip install <library>`
2. Add `import <library>` (or `from <library> import <thing>`) to `configure_libraries.py`
3. In any file that needs it: `from configure_libraries import <thing>`

---

## Troubleshooting

### `pyvisa.errors.VisaIOError: VI_ERROR_RSRC_NFOUND`

The VISA address is wrong or the instrument is not detected.
- Run `python -m visa list` to see all detected resources
- Check GPIB address on instrument front panel matches the address in config
- Check USB cable is connected and Rigol is powered on
- Try power cycling the instrument and reconnecting

### `qcodes.instrument.base.InstrumentAlreadyExistsError`

A previous Python session left the QCoDeS instrument open without closing it properly.
```python
from qcodes.instrument.base import Instrument
Instrument.close_all()
```
Run this once, then retry.

### Compliance current hit — current clamps, voltage drops

The measured current reached `DRAIN_COMPLIANCE`. Either:
- The MOSFET is drawing more current than expected — increase `DRAIN_COMPLIANCE` (check device I_D(max) first)
- V_DS or V_GS is too high for this device — reduce `VDS_STOP` or `VGS_VALUES`
- Wiring fault causing a short circuit — check all connections

### Curves look noisy or jagged

- Increase `SETTLING_TIME` to 100 ms or 200 ms
- Check for loose connections (especially ground)
- Ensure no other equipment is sharing the power strip (switching supplies inject noise)
- Try a shorter GPIB cable

### All curves are flat at zero

- Gate voltage not reaching the device: check Rigol output is `on`, cable is connected to Gate pin
- V_th may be higher than your `VGS_VALUES` range: try higher gate voltages
- MOSFET may be oriented incorrectly: verify pin-out from datasheet (Gate, Drain, Source are not always in the same position)

### Plot window does not appear

- plottr requires a Qt backend. Install it: `pip install PyQt5` or `pip install PySide6`
- On headless Linux servers, a display must be available. Set `DISPLAY=:0` or use a virtual display

### Python version error on the `with` block

The multi-context `with (A as a, B as b, C as c):` syntax requires Python 3.10+.
```bash
python --version
```
If below 3.10, either upgrade Python or rewrite the `with` block as nested statements:
```python
with Keithley2400Controller("drain", DRAIN_ADDRESS, DRAIN_COMPLIANCE) as drain:
    with Keithley2400Controller("source", SOURCE_ADDRESS, SOURCE_COMPLIANCE) as source:
        with RigolDG822Controller("gate", GATE_ADDRESS, v_limit=GATE_V_LIMIT) as gate:
            results = run_output_iv(drain, source, gate, plotter)
```

---

## Contributing

Contributions welcome. Please:

- Follow the existing import pattern — all imports in `configure_libraries.py`
- Maintain the context manager pattern for any new instrument classes
- Test that instruments disconnect safely on both normal exit and Ctrl+C
- Update this README if you add a new module, parameter, or measurement type

---

## License

MIT License. See `LICENSE` for details.