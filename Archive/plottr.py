"""
plottr.py

Live IV curve plotting using plottr.

plottr works by streaming data into an InMemoryDataBuffer which a PlotWindow subscribes to.  We open the window once and push new (vds, id) points into it after every measurement step, so the plot updates in real-time as the sweep runs.

Requirements:
    pip install plottr
"""

from configure_libraries import np, Optional, DataDict, autoplot


class LiveIVPlot:
    """
    Opens a plottr live window and streams IV data into it.

    Usage
    -----
        plotter = LiveIVPlot(title="MOSFET Output IV")
        plotter.start()

        for vgs in vgs_list:
            plotter.new_curve(label=f"VGS={vgs:.1f}V")
            for vds, id in zip(vds_array, id_array):
                plotter.add_point(vds, id)

        plotter.stop()
    """

    def __init__(self, title: str = "MOSFET IV Curves",
                 x_label: str = "V_DS (V)",
                 y_label: str = "I_D (mA)"):
        self.title = title
        self.x_label = x_label
        self.y_label = y_label

        self._app = None
        self._fc = None          # plottr flowchart
        self._datadict = None
        self._curve_idx = 0      # increments with each new curve

    def start(self):
        """
        Open the plottr window.
        Call this BEFORE starting your sweep loop.
        """
        # DataDict defines the axes and the dependent variable we'll stream
        self._datadict = DataDict(
            x=dict(unit="V"),
            y=dict(axes=["x"], unit="mA"),
        )
        self._datadict.validate()

        # autoplot returns (app, flowchart) — the window opens immediately
        self._app, self._fc = autoplot(
            inputData=self._datadict,
            title=self.title,
        )

    def new_curve(self, label: Optional[str] = None):
        """
        Signal that the next add_point() calls belong to a new curve.
        In practice plottr will separate them automatically because we
        reset the internal buffer for each V_GS step.
        """
        self._curve_idx += 1
        self._x_buf = []
        self._y_buf = []
        self._curve_label = label or f"Curve {self._curve_idx}"

    def add_point(self, x: float, y_amps: float):
        """
        Push one (x, y) data point to the live plot.

        Parameters
        ----------
        x       : x-axis value (e.g. V_DS in Volts)
        y_amps  : measured current in Amps — converted to mA internally
        """
        self._x_buf.append(x)
        self._y_buf.append(y_amps * 1e3)   # A → mA

        # Push latest buffer snapshot into the datadict and refresh
        self._datadict["x"]["values"] = np.array(self._x_buf)
        self._datadict["y"]["values"] = np.array(self._y_buf)
        self._datadict.validate()

        # Feed updated data into the plottr flowchart input node
        self._fc.setData(self._datadict)

        # Process Qt events so the window actually redraws
        if self._app is not None:
            self._app.processEvents()

    def stop(self):
        """Keep the window open after sweep ends (user closes manually)."""
        if self._app is not None:
            self._app.exec_()   # Enter Qt event loop — blocks until closed