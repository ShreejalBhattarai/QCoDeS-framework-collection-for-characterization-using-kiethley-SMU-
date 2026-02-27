"""
configure_libraries.py

Single source of truth for all third-party and stdlib imports.
Every other file in this project imports exclusively from here.

To add a new library to the project:
  1. pip install <library>
  2. Add the import below
  3. Use it via:  from configure_libraries import <name>
"""

# ── Standard library ────────────────────────────────────────────────
import time
import logging
from pathlib import Path
from typing import Optional

# ── Numerical ───────────────────────────────────────────────────────
import numpy as np

# ── QCoDeS instrument drivers ───────────────────────────────────────
from qcodes.instrument_drivers.tektronix.Keithley_2400 import Keithley2400
from qcodes.instrument_drivers.rigol.DG800 import RigolDG800

# ── Plottr live plotting ─────────────────────────────────────────────
from plottr.data.datadict import DataDict
from plottr.apps.autoplot import autoplot