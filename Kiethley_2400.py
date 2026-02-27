"""
instruments/keithley.py

Keithley 2400 SMU controller.
Handles connection, safe defaults, output control, and measurement.
"""

from configure_libraries import time, logging, Keithley2400

log = logging.getLogger(__name__)


class Keithley2400Controller:
    """
    Simple wrapper around the QCoDeS Keithley 2400 driver.

    Parameters
    ----------
    name       : unique QCoDeS name, e.g. 'drain' or 'source'
    address    : VISA string, e.g. 'GPIB::24::INSTR'
    compliance : current compliance in Amps (protects the DUT)
    """

    def __init__(self, name: str, address: str, compliance: float = 100e-3):
        self.name = name
        self.address = address
        self.compliance = compliance
        self._smu = None

    # ------------------------------------------------------------------ #
    #  Connection
    # ------------------------------------------------------------------ #

    def connect(self):
        log.info(f"[{self.name}] connecting at {self.address}")
        self._smu = Keithley2400(self.name, self.address)
        # Safe defaults — output stays OFF until explicitly enabled
        self._smu.mode("VOLT")
        self._smu.volt(0)
        self._smu.compliance_current(self.compliance)
        self._smu.output("off")
        log.info(f"[{self.name}] connected")

    def disconnect(self):
        if self._smu is not None:
            self.set_voltage(0)
            time.sleep(0.05)
            self._smu.output("off")
            self._smu.close()
            log.info(f"[{self.name}] disconnected")

    # ------------------------------------------------------------------ #
    #  Output
    # ------------------------------------------------------------------ #

    def output_on(self):
        self._smu.output("on")

    def output_off(self):
        self._smu.output("off")

    # ------------------------------------------------------------------ #
    #  Source & Measure
    # ------------------------------------------------------------------ #

    def set_voltage(self, v: float):
        """Force voltage on this terminal."""
        self._smu.volt(v)

    def measure_current(self) -> float:
        """Read drain current in Amps."""
        return float(self._smu.curr())

    # ------------------------------------------------------------------ #
    #  Context manager  (with Keithley2400Controller(...) as k:)
    # ------------------------------------------------------------------ #

    def __enter__(self):
        self.connect()
        self.output_on()
        return self

    def __exit__(self, *_):
        self.disconnect()