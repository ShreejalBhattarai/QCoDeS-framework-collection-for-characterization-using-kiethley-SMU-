import time, logging
import numpy as np
import matplotlib.pyplot as plt

from qcodes.instrument_drivers.Keithley import Keithley2400
from qcodes.instrument_drivers.rigol import RigolDG1062, RigolDG1062Channel
from qcodes.instrument import Instrument

# Fix for a bug in the QCoDeS Rigol driver: when the DG822 is in DC mode
# the ``:SOURx:APPL?`` query returns simply ``"DC"`` which the driver
# fails to translate.  Add a mapping so the constructor can complete.
RigolDG1062Channel.waveform_translate.setdefault("DC", "DC")

# ------------------------------------------------------------------ #
#  CONFIG 
# ------------------------------------------------------------------ #

DRAIN_ADDRESS    = "GPIB::24::INSTR"
GATE_ADDRESS     = "USB0::0x1AB1::0x0646::DG8Q279M00185::INSTR"

DRAIN_COMPLIANCE = 100e-3   # A  — max drain current before SMU clamps
GATE_V_LIMIT     = 10.0     # V  — hard cap on |V_GS| to protect gate oxide
VDS_START        = 5.0      # V
VDS_STOP         = 10.0      # V
VDS_POINTS       = 100

VGS_VALUES       = (4.5, 5.0, 5.5, 6.0, 6.5, 7.0, 7.5, 8.0)   # V

SETTLING_TIME    = 0.05     # s — wait after each voltage step

OUTPUT_FILE      = "iv_results.npz"

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
    # read back output status immediately to confirm the instrument did
    # actually enable its front panel output.  If this returns 0 the device
    # isn't driving, which would explain the "output off" errors later.
    try:
        out_stat = drain.output.get()
        log.info(f"drain output status after enabling: {out_stat}")
    except Exception as e:
        log.warning(f"could not query drain output status: {e}")

    # --- Rigol DG1062 CH1: DC offset mode, output on -------------------
    gate_ch = gate.channels[0]
    # The DG1062 driver requires freq and ampl even for DC mode, so we
    # provide harmless values here.  Only the offset actually controls
    # the DC level we care about.
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

        # set gate voltage through the QCoDeS Rigol DC offset parameter
        # again include the unused freq/ampl arguments required by the
        # driver for the "DC" waveform
        gate_ch.apply(waveform="DC", freq=0.0, ampl=0.0, offset=vgs)
        time.sleep(SETTLING_TIME)

        id_values  = []
        abort_sweep = False
        for vds in vds_array:
            drain.volt(vds)        # QCoDeS param: set drain voltage
            time.sleep(SETTLING_TIME)

            try:
                current = float(drain.curr())
            except RuntimeError as exc:
                # compliance or output disabled; stop the sweep since the
                # source-meter is essentially protecting itself.
                if "output off" in str(exc).lower():
                    log.error(
                        f"drain output off at V_DS={vds} – assumed compliance, "
                        "aborting V_GS={vgs} sweep"
                    )
                    abort_sweep = True
                    break
                else:
                    raise

            id_values.append(current)

        results["id"][vgs] = np.array(id_values)

    # safe ramp-down before closing
    drain.volt(0.0)
    drain.output("off")
    # again include unnecessary freq/ampl arguments to avoid driver errors
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

    # quick example of how to reload:
    # data = np.load("iv_results.npz")
    # id_at_2V = data["id_vgs_2p0"]   # Amps

# ------------------------------------------------------------------ #
#  Final blocking plot
# ------------------------------------------------------------------ #

def plot_final(results: dict) -> None:
    fig, ax = plt.subplots()
    for vgs in results["vgs_values"]:
        id_arr = results["id"].get(vgs, np.array([]))
        if id_arr.size == 0:
            log.warning(f"no data collected for V_GS={vgs}, skipping plot")
            continue
        ax.semilogy(results["vds"], id_arr * 1000.0,
                label=f"V_GS = {vgs:.1f} V")
    ax.set_xlabel("V_DS (V)")
    ax.set_ylabel("I_D (mA)")
    ax.set_title("MOSFET Output IV Curves")
    ax.legend()
    ax.grid(True)
    plt.tight_layout()
    log.info("Close the plot window to exit.")
    plt.show()

# ------------------------------------------------------------------ #
#  Main
# ------------------------------------------------------------------ #

def _connect_rigol(address: str, name: str = "gate", retries: int = 3, delay: float = 1.0) -> RigolDG1062:
    """Attempt to instantiate the Rigol DG1062 driver several times.

    The built‑in driver queries the current waveform in ``__init__`` which
    can time out if the instrument is busy or has been recently closed by
    another session.  A few retries with a short delay often cures spurious
    ``VI_ERROR_TMO`` failures.
    """
    for attempt in range(1, retries + 1):
        try:
            rigol = RigolDG1062(name, address)
            # bump the VISA timeout a little higher than the default so that
            # the device has more time to respond before we fail again later.
            rigol.timeout = 5000  # milliseconds
            return rigol
        except KeyError as exc:
            # this happens if the driver receives "DC" and doesn't know how
            # to translate it.  add the mapping and retry immediately.
            log.warning(
                f"Rigol driver KeyError '{exc}'; adding DC mapping and retrying"
            )
            RigolDG1062Channel.waveform_translate.setdefault("DC", "DC")
            if attempt == retries:
                raise
            continue
        except Exception as exc:  # could be VisaIOError or ValueError
            log.warning(
                f"Rigol connection attempt {attempt} failed: {exc}"
            )
            if attempt == retries:
                raise
            time.sleep(delay)


def main() -> None:
    # Clean up any leftover QCoDeS handles from a previous crashed session
    Instrument.close_all()
    # a short pause helps ensure the drivers have released the VISA resource
    time.sleep(0.5)

    drain = None
    gate = None
    results = None

    try:
        drain = Keithley2400("drain", DRAIN_ADDRESS)
        gate  = _connect_rigol(GATE_ADDRESS)

        results = run_sweep(drain, gate)
        save_results(results)
    except Exception as exc:  # catch keyboard interrupt and other errors
        log.warning(f"Interrupted or error ({exc}) — ramping instruments to 0 V.")
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
