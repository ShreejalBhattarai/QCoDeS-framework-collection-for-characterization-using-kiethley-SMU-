# Automated MOSFET Characterization using qcodes for future quantum dot characterization

> A modular Python toolkit for measuring MOSFET I–V (current–voltage) characteristics using QCoDeS.

Data is streamed to a live plot window, allowing you to watch the curves build in real time during the sweep. This code is designed for use with a **Keithley 2400 SMU** and a **Rigol DG822** (or DG1062) waveform generator for fully automated MOSFET characterization.

---

## Features

- **Sweep V_DS** over a defined range for multiple V_GS values
- Automatically logs **I_D currents** at each step
- Filters out very small currents below a threshold to remove noise
- Saves results in **NumPy `.npz` format** for easy post-processing
- Provides a final **log-log plot** of MOSFET output characteristics

---

## Example Results

<div align="center">

| Automated Setup | Datasheet Reference |
|:---:|:---:|
| <img width="420" alt="Poster_Plot" src="https://github.com/user-attachments/assets/6689df20-d004-45d4-8a60-d21d855d19ee" /> | <img width="420" alt="iv_datasheet" src="https://github.com/user-attachments/assets/0f5132db-08a0-4d94-8208-2dc26346b2de" /> |
| *Measured output characteristics* | *Official datasheet reference* |

| Sweep Flowchart | Block Diagram |
|:---:|:---:|
| <img width="420" alt="mosfet_iv_sweep_flowchart" src="https://github.com/user-attachments/assets/fbf83fbd-793a-41d2-84b5-45fba5dca43b" /> | <img width="420" alt="poster drawio" src="https://github.com/user-attachments/assets/fff497d4-a1d2-4287-8860-19e6e07f36d6" /> |
| *Measurement sweep flow* | *System block diagram* |

</div>

---

## Supported Instruments

| Instrument | Terminal | Role |
|---|---|---|
| Keithley 2400 SMU | Drain | Forces V_DS and measures I_D |
| Rigol DG822 / DG1062 AWG | Gate | Supplies DC gate voltage V_GS |
| Direct wire to ground | Source | Source pin tied to Keithley LO — no second SMU needed |

---

## How It Works

1. **Initialize instruments**
   - Keithley 2400 configured for voltage source mode with compliance current
   - Rigol waveform generator set to DC mode to provide gate voltage

2. **Outer loop:** step V_GS through a predefined list

3. **Inner loop:** sweep V_DS from `VDS_START` to `VDS_STOP` for each V_GS value
   - Reads I_D at each step
   - Applies a current threshold to remove low-noise readings

4. **Data storage**
   - Results saved in `iv_results.npz`
   - Each V_GS sweep stored as a separate array for easy plotting or analysis

5. **Plotting**
   - Generates a log-log plot of I_D vs V_DS
   - Each curve represents a different gate voltage V_GS

---

## Safety & Configuration

| Parameter | Purpose |
|---|---|
| `GATE_V_LIMIT` | Prevents exceeding the safe gate voltage to protect MOSFET gate oxide |
| `DRAIN_COMPLIANCE` | Prevents overcurrent on the drain |
| `SETTLING_TIME` | Ensures voltages stabilize before measurement |

**Default parameters** (modifiable in the script):

```python
VDS_START = 0.01   # V
VDS_STOP = 10.0    # V
VDS_POINTS = 100
VGS_VALUES = [4.5, 5.0, 5.5, 6.0, 6.5, 7.0, 7.5, 8.0]  # V
CURRENT_THRESHOLD = 1e-6  # A
```

---

## Usage

```bash
python mosfet_iv_qcodes.py
```

Ensure instruments are connected. The script will:

1. Initialize instruments
2. Sweep V_GS and V_DS
3. Save results to `iv_results.npz`
4. Display a live final plot

---

## License

MIT License. See [`LICENSE`](LICENSE) for details.
