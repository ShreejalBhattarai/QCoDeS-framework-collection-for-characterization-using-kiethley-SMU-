"""
main.py

Main driver for MOSFET IV curve measurement.
─────────────────────────────────────────────
Edit the CONFIG section below, then run:

    python main.py

What it does:
  1. Connects to both Keithley 2400s and the Rigol DG822 Pro
  2. Opens a live plottr window
  3. Sweeps V_DS at each V_GS step, streaming every point to the plot
  4. Saves results to  data/iv_results.npz  when done
  5. Keeps the plot window open until you close it
"""

from configure_libraries import time, logging, np, Path

from instruments import Keithley2400Controller, RigolDG822Controller
from analysis import LiveIVPlot

# ─────────────────────────────────────────────────────────────────── #
#  LOGGING
# ─────────────────────────────────────────────────────────────────── #

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("main")


# ─────────────────────────────────────────────────────────────────── #
#  CONFIG  ← edit this section for your setup
# ─────────────────────────────────────────────────────────────────── #

# VISA addresses — TODO
DRAIN_ADDRESS  = "GPIB::24::INSTR"
SOURCE_ADDRESS = "GPIB::25::INSTR"
GATE_ADDRESS   = "USB0::0x1AB1::0x0643::DG8XXXXXXXX::INSTR"

# Safety limits
DRAIN_COMPLIANCE  = 100e-3   # Amps
SOURCE_COMPLIANCE = 10e-3    # Amps
GATE_V_LIMIT      = 10.0     # Volts — hard cap on V_GS

# Sweep parameters
VDS_START  = 0.0             # Volts
VDS_STOP   = 5.0             # Volts
VDS_POINTS = 100

VGS_VALUES = [0.0, 1.0, 2.0, 3.0, 4.0]   # Gate voltage steps

SETTLING_TIME = 0.05         # Seconds to wait after each voltage step

# Where to save results
OUTPUT_FILE = "data/iv_results.npz"


# ─────────────────────────────────────────────────────────────────── #
#  SWEEP
# ─────────────────────────────────────────────────────────────────── #

def run_output_iv(drain, source, gate, plotter):
    """
    Output IV sweep: I_D vs V_DS at each V_GS.

    Parameters
    ----------
    drain   : Keithley2400Controller — drain terminal
    source  : Keithley2400Controller — source terminal (held at 0 V)
    gate    : RigolDG822Controller   — gate terminal
    plotter : LiveIVPlot             — live plot handle

    Returns
    -------
    dict with keys 'vds', 'vgs_values', 'id'
    """
    vds_array = np.linspace(VDS_START, VDS_STOP, VDS_POINTS)
    results = {"vds": vds_array, "vgs_values": VGS_VALUES, "id": {}}

    log.info("─" * 45)
    log.info("Output IV sweep started")
    log.info(f"  V_DS : {VDS_START} → {VDS_STOP} V  ({VDS_POINTS} pts)")
    log.info(f"  V_GS : {VGS_VALUES}")
    log.info("─" * 45)

    # Source is always 0 V (ground reference)
    source.set_voltage(0)

    for step, vgs in enumerate(VGS_VALUES, 1):
        log.info(f"Step {step}/{len(VGS_VALUES)}  V_GS = {vgs:.2f} V")

        # Tell the plotter we're starting a new curve
        plotter.new_curve(label=f"V_GS = {vgs:.1f} V")

        # Apply gate voltage
        gate.set_voltage(vgs)
        time.sleep(SETTLING_TIME)

        id_values = []

        for vds in vds_array:
            drain.set_voltage(vds)
            time.sleep(SETTLING_TIME)

            id_meas = drain.measure_current()
            id_values.append(id_meas)

            # Stream point to live plot immediately
            plotter.add_point(x=vds, y_amps=id_meas)

        results["id"][vgs] = np.array(id_values)

    # Safe reset
    drain.set_voltage(0)
    gate.set_voltage(0)
    log.info("Sweep complete.")

    return results


# ─────────────────────────────────────────────────────────────────── #
#  SAVE
# ─────────────────────────────────────────────────────────────────── #

def save_results(results: dict, path: str):
    """Save vds array and all I_D curves to a .npz file."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)

    save_dict = {"vds": results["vds"]}
    for vgs, id_arr in results["id"].items():
        key = f"id_vgs_{str(vgs).replace('.', 'p')}"   # e.g. id_vgs_1p0
        save_dict[key] = id_arr

    np.savez(path, **save_dict)
    log.info(f"Results saved → {path}")


# ─────────────────────────────────────────────────────────────────── #
#  ENTRY POINT
# ─────────────────────────────────────────────────────────────────── #

def main():
    # 1. Open live plot window before connecting instruments
    plotter = LiveIVPlot(
        title="MOSFET Output IV — Live",
        x_label="V_DS (V)",
        y_label="I_D (mA)",
    )
    plotter.start()

    # 2. Connect instruments — context managers guarantee safe shutdown
    with (
        Keithley2400Controller("drain",  DRAIN_ADDRESS,  DRAIN_COMPLIANCE)  as drain,
        Keithley2400Controller("source", SOURCE_ADDRESS, SOURCE_COMPLIANCE) as source,
        RigolDG822Controller("gate",    GATE_ADDRESS,   v_limit=GATE_V_LIMIT) as gate,
    ):
        # 3. Run sweep
        results = run_output_iv(drain, source, gate, plotter)

    # Instruments are now safely closed (context managers ran __exit__)

    # 4. Save results
    save_results(results, OUTPUT_FILE)

    # 5. Block until user closes the plot window
    log.info("Sweep done — close the plot window to exit.")
    plotter.stop()


if __name__ == "__main__":
    main()