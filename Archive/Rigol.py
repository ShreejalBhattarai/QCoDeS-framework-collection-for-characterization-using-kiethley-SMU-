"""
instruments/rigol.py

Rigol DG822 Pro controller.
Used purely as a DC voltage source for the MOSFET gate (V_GS).
"""

from configure_libraries import logging, RigolDG800

log = logging.getLogger(__name__)


class RigolDG822Controller:
    """
    Thin wrapper around the QCoDeS Rigol DG800 driver.

    The DG822 Pro is configured in DC offset mode so it acts as a
    clean, programmable DC supply for the gate terminal.

    Parameters
    ----------
    name    : unique QCoDeS name, e.g. 'gate'
    address : VISA string, e.g. 'USB0::0x1AB1::0x0643::DG8A...::INSTR'
    channel : AWG channel to use (default 1)
    v_limit : hard cap on V_GS in Volts (default 10 V)
    """

    def __init__(self, name: str, address: str, channel: int = 1, v_limit: float = 10.0):
        self.name = name
        self.address = address
        self.channel = channel
        self.v_limit = v_limit
        self._awg = None
        self._ch = None

    # ------------------------------------------------------------------ #
    #  Connection
    # ------------------------------------------------------------------ #

    def connect(self):
        log.info(f"[{self.name}] connecting at {self.address}")
        self._awg = RigolDG800(self.name, self.address)
        self._ch = getattr(self._awg, f"ch{self.channel}")
        # DC mode, 0 V, output off until explicitly enabled
        self._ch.function_type("DC")
        self._ch.offset(0)
        self._ch.output("off")
        log.info(f"[{self.name}] connected")

    def disconnect(self):
        if self._awg is not None:
            self._ch.offset(0)
            self._ch.output("off")
            self._awg.close()
            log.info(f"[{self.name}] disconnected")

    # ------------------------------------------------------------------ #
    #  Output
    # ------------------------------------------------------------------ #

    def output_on(self):
        self._ch.output("on")

    def output_off(self):
        self._ch.output("off")

    # ------------------------------------------------------------------ #
    #  Gate voltage
    # ------------------------------------------------------------------ #

    def set_voltage(self, vgs: float):
        """
        Set gate voltage V_GS via DC offset.

        Raises ValueError if |vgs| exceeds v_limit.
        """
        if abs(vgs) > self.v_limit:
            raise ValueError(
                f"[{self.name}] V_GS = {vgs} V exceeds safety limit ±{self.v_limit} V"
            )
        self._ch.offset(vgs)
        log.debug(f"[{self.name}] V_GS = {vgs:.4f} V")

    def get_voltage(self) -> float:
        return float(self._ch.offset())

    # ------------------------------------------------------------------ #
    #  Context manager
    # ------------------------------------------------------------------ #

    def __enter__(self):
        self.connect()
        self.output_on()
        return self

    def __exit__(self, *_):
        self.disconnect()