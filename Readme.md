# mosfet_iv_qcodes

A modular Python toolkit for measuring MOSFET IV (current-voltage) characteristics using [QCoDeS](https://qcodes.github.io/Qcodes/). Data is streamed to a **live plot window** via [plottr](https://github.com/toolsforexperiments/plottr) so you can watch the curves build in real-time during the sweep.



## Results:


From the automated setup:
<img width="1920" height="975" alt="Poster_Plot" src="https://github.com/user-attachments/assets/6689df20-d004-45d4-8a60-d21d855d19ee" />



From the official datasheet:
<img width="943" height="762" alt="iv_datasheet" src="https://github.com/user-attachments/assets/0f5132db-08a0-4d94-8208-2dc26346b2de" />


---

## Instruments

| Instrument | Terminal | Role |
|---|---|---|
| Keithley 2400 SMU | Drain | Forces V_DS, measures I_D |
| Rigol DG822 Pro AWG | Gate | Supplies DC gate voltage V_GS |
| Direct wire to ground | Source | Source pin tied to Keithley LO — no second SMU needed |

---

Readme on work..


MIT License. See `LICENSE` for details.
