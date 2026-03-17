import time
import logging
import numpy as np
import matplotlib.pyplot as plt

from qcodes.instrument_drivers.Keithley import Keithley2400
from qcodes.instrument_drivers.rigol import RigolDG1062, RigolDG1062Channel
from qcodes.instrument import Instrument

RigolDG1062Channel.waveform_translate.setdefault("DC", "DC")

# ------------------------------------------------------------------ #
#  CONFIG
# ------------------------------------------------------------------ #

DRAIN_ADDRESS     = "GPIB::24::INSTR"
GATE_ADDRESS      = "USB0::0x1AB1::0x0646::DG8Q279M00185::INSTR"
CURRENT_THRESHOLD = 1e-6    # A — readings below this are set to nan

DRAIN_COMPLIANCE  = 1.0     # A — max drain current before SMU clamps
GATE_V_LIMIT      = 10.0    # V — hard cap on |V_GS| to protect gate oxide
VDS_START         = 0.01     # V — nonzero so log x-axis works
VDS_STOP          = 10.0    # V
VDS_POINTS        = 100

VGS_VALUES        = [4.5, 5.0, 5.5, 6.0, 6.5, 7.0, 7.5, 8.0]  # V

SETTLING_TIME     = 0.05    # s — wait after each voltage step

OUTPUT_FILE       = "iv_results.npz"

# ------------------------------------------------------------------ #
#  Logging
# ------------------------------------------------------------------ #

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ------------------------------------------------------------------ #
#  Sweep
# ------------------------------------------------------------------ #

def run_sweep(drain: Keithley2400, gate: RigolDG1062) -> dict:
    """
    Outer loop: step V_GS through VGS_VALUES via Rigol CH1 (DC offset mode).
    Inner loop: sweep V_DS with the Keithley SMU and read I_D at each point.
    Returns a results dict with the shared vds axis and a per-VGS current array.
    """
    vds_array = np.linspace(VDS_START, VDS_STOP, VDS_POINTS)
    results = {"vds": vds_array, "vgs_values": VGS_VALUES, "id": {}}

    # --- Keithley 2400: source voltage, sense current ------------------
    drain.mode("VOLT")
    drain.compliancei(DRAIN_COMPLIANCE)
    drain.volt(0.0)
    drain.output("on")
    try:
        out_stat = drain.output.get()
        log.info(f"drain output status after enabling: {out_stat}")
    except Exception as e:
        log.warning(f"could not query drain output status: {e}")

    # --- Rigol DG1062 CH1: DC offset mode, output on -------------------
    gate_ch = gate.channels[0]
    gate_ch.apply(waveform="DC", freq=0.0, ampl=0.0, offset=0.0)
    gate.write(":OUTP1 ON")

    log.info("=" * 55)
    log.info("Output IV sweep started")
    log.info(f"  V_DS : {VDS_START} → {VDS_STOP} V  ({VDS_POINTS} pts)")
    log.info(f"  V_GS : {VGS_VALUES}")
    log.info("=" * 55)

    for step, vgs in enumerate(VGS_VALUES, start=1):
        log.info(f"Step {step}/{len(VGS_VALUES)}  V_GS = {vgs:.2f} V")

        if abs(vgs) > GATE_V_LIMIT:
            raise ValueError(
                f"V_GS = {vgs} V exceeds safety limit ±{GATE_V_LIMIT} V"
            )

        gate_ch.apply(waveform="DC", freq=0.0, ampl=0.0, offset=vgs)
        time.sleep(SETTLING_TIME)

        id_values   = []
        abort_sweep = False

        for vds in vds_array:
            drain.volt(vds)
            time.sleep(SETTLING_TIME)

            try:
                current = float(drain.curr())
            except RuntimeError as exc:
                if "output off" in str(exc).lower():
                    log.error(
                        f"drain output off at V_DS={vds:.3f} V — "
                        f"assumed compliance, aborting V_GS={vgs} sweep"
                    )
                    abort_sweep = True
                    break
                else:
                    raise

            id_values.append(current)

        # apply threshold and store — one assignment only
        id_array = np.array(id_values)
        id_array = np.where(np.abs(id_array) < CURRENT_THRESHOLD, np.nan, id_array)
        results["id"][vgs] = id_array

        if abort_sweep:
            break

    # safe ramp-down
    drain.volt(0.0)
    drain.output("off")
    gate_ch.apply(waveform="DC", freq=0.0, ampl=0.0, offset=0.0)
    gate.write(":OUTP1 OFF")

    log.info("Sweep complete.")
    return results

# ------------------------------------------------------------------ #
#  Save results
# ------------------------------------------------------------------ #

def save_results(results: dict) -> None:
    arrays = {"vds": results["vds"]}
    for vgs, id_arr in results["id"].items():
        key = f"id_vgs_{str(vgs).replace('.', 'p').replace('-', 'n')}"
        arrays[key] = id_arr
    np.savez(OUTPUT_FILE, **arrays)
    log.info(f"Results saved → {OUTPUT_FILE}")

# ------------------------------------------------------------------ #
#  Final plot
# ------------------------------------------------------------------ #

def plot_final(results: dict) -> None:
    fig, ax = plt.subplots()
    for vgs in results["vgs_values"]:
        id_arr = results["id"].get(vgs, np.array([]))
        if id_arr.size == 0:
            log.warning(f"no data collected for V_GS={vgs}, skipping plot")
            continue
        ax.loglog(results["vds"][:len(id_arr)], id_arr * 1.0,
                  label=f"V_GS = {vgs:.1f} V")
    ax.set_xlabel("V_DS (V)")
    ax.set_ylabel("I_D (A)")
    ax.set_title("MOSFET Output IV Curves")
    ax.legend()
    ax.grid(True, which="both")
    ax.grid(True, which="minor", linestyle=":", linewidth=0.5, alpha=0.5)
    plt.tight_layout()
    log.info("Close the plot window to exit.")
    plt.show()

# ------------------------------------------------------------------ #
#  Rigol connection helper
# ------------------------------------------------------------------ #

def _connect_rigol(address: str, name: str = "gate", retries: int = 3, delay: float = 1.0) -> RigolDG1062:
    for attempt in range(1, retries + 1):
        try:
            rigol = RigolDG1062(name, address)
            rigol.timeout = 5000
            return rigol
        except KeyError as exc:
            log.warning(f"Rigol driver KeyError '{exc}'; adding DC mapping and retrying")
            RigolDG1062Channel.waveform_translate.setdefault("DC", "DC")
            if attempt == retries:
                raise
            continue
        except Exception as exc:
            log.warning(f"Rigol connection attempt {attempt} failed: {exc}")
            if attempt == retries:
                raise
            time.sleep(delay)

# ------------------------------------------------------------------ #
#  Main
# ------------------------------------------------------------------ #

def main() -> None:
    Instrument.close_all()
    time.sleep(0.5)

    drain  = None
    gate   = None
    results = None

    try:
        drain = Keithley2400("drain", DRAIN_ADDRESS)
        gate  = _connect_rigol(GATE_ADDRESS)

        results = run_sweep(drain, gate)
        save_results(results)
    except Exception as exc:
        log.warning(f"Interrupted or error ({exc}) — ramping instruments to 0 V.")
        try:
            if drain is not None:
                drain.volt(0.0)
                drain.output("off")
            if gate is not None:
                gate.channels[0].apply(waveform="DC", freq=0.0, ampl=0.0, offset=0.0)
                gate.write(":OUTP1 OFF")
        except Exception:
            pass
        if not isinstance(exc, KeyboardInterrupt):
            raise
    finally:
        if drain is not None:
            drain.close()
        if gate is not None:
            gate.close()
        log.info("Instruments closed.")

    if results is not None:
        plot_final(results)


if __name__ == "__main__":
    main()
