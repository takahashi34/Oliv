"""
Live Plotting Module for Laser Measurement Suite

Provides embedded matplotlib plots that update in real-time during measurements.
"""

import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from tkinter import LabelFrame


class LivePlot:
    """
    A live-updating matplotlib plot embedded in a tkinter window.
    
    Usage:
        # In __init__:
        self.live_plot = LivePlot(parent_frame, "Current (mA)", "Light (W)")
        
        # Before measurement loop:
        self.live_plot.reset()
        
        # Inside measurement loop:
        self.live_plot.add_point(current_value, light_value)
        
        # After measurement (optional - to show final plot in separate window):
        self.live_plot.show_final()
    """
    
    def __init__(self, parent, xlabel="X", ylabel="Y", title="Live Measurement", 
                 color='blue', ylabel2=None, color2='red'):
        """
        Create a live plot embedded in a tkinter parent widget.
        
        Args:
            parent: tkinter parent widget (Frame, LabelFrame, or Toplevel)
            xlabel: Label for x-axis
            ylabel: Label for y-axis (primary)
            title: Plot title
            color: Line color for primary data
            ylabel2: Label for secondary y-axis (if dual-axis plot)
            color2: Line color for secondary data
        """
        self.parent = parent
        self.xlabel = xlabel
        self.ylabel = ylabel
        self.ylabel2 = ylabel2
        self.title = title
        self.color = color
        self.color2 = color2
        self.dual_axis = ylabel2 is not None
        
        # Data storage
        self.x_data = []
        self.y_data = []
        self.y2_data = []  # For dual-axis plots
        
        # Multiple measurement runs
        # Each item in measurement_runs represents one independent measurement.
        self.measurement_runs = []
        self.current_run = None
        self.run_counter = 0

        # Use Matplotlib's default color sequence for different runs.
        self.run_color_cycle = plt.rcParams['axes.prop_cycle'].by_key().get(
            'color',
            ['blue', 'orange', 'green', 'red', 'purple']
        )
       
        # Create the plot frame
        self.frame = LabelFrame(parent, text='Live Plot')
        self.frame.grid(row=0, column=0, padx=10, pady=10, sticky='NSEW')

        # Allow the frame to expand within parent
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)

        # Allow the canvas to expand within self.frame
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(0, weight=1)
        
        # Create figure and axes
        self.fig = Figure(figsize=(6, 4), dpi=100)
        self.ax = self.fig.add_subplot(111)
        
        if self.dual_axis:
            self.ax2 = self.ax.twinx()
        else:
            self.ax2 = None
        
        # Create the canvas
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill='both', expand=True)
        
        # Initialize plot elements
        self._setup_plot()
    
    def _setup_plot(self):
        """Set up the initial plot appearance."""
        self.ax.set_xlabel(self.xlabel)
        self.ax.set_ylabel(self.ylabel, color=self.color)
        self.ax.set_title(self.title)
        self.ax.tick_params(axis='y', labelcolor=self.color)
        self.ax.grid(True, alpha=0.3)
        
        # Create empty line for primary data
        self.line, = self.ax.plot([], [], color=self.color, marker='o', 
                                   markersize=3, linewidth=1.5, label=self.ylabel)
        
        if self.dual_axis and self.ax2:
            self.ax2.set_ylabel(self.ylabel2, color=self.color2)
            self.ax2.tick_params(axis='y', labelcolor=self.color2)
            self.line2, = self.ax2.plot([], [], color=self.color2, marker='s',
                                         markersize=3, linewidth=1.5, label=self.ylabel2)
        
        self.fig.tight_layout()
        
    def start_new_run(self, run_label=None):
        """
        Create a new measurement run without removing previous runs.

        Args:
            run_label: Optional description, such as "20°C".

        Returns:
            Dictionary containing the new run's data and plot objects.
        """
        self.run_counter += 1

        # Select a color according to the run number.
        color_index = (self.run_counter - 1) % len(self.run_color_cycle)
        run_color = self.run_color_cycle[color_index]

        # Build the legend label.
        if run_label:
            label = f"Run {self.run_counter} - {run_label}"
        else:
            label = f"Run {self.run_counter}"

        # Create the primary-axis line for this run.
        run_line, = self.ax.plot(
            [],
            [],
            color=run_color,
            marker='o',
            markersize=3,
            linewidth=1.5,
            label=label
        )

        # LIV uses a second line on the secondary y-axis.
        # Use the same color but a dashed line.
        run_line2 = None
        if self.dual_axis and self.ax2 is not None:
            run_line2, = self.ax2.plot(
                [],
                [],
                color=run_color,
                linestyle=':',
                marker='x',
                markersize=3,
                linewidth=1.5,
                alpha=0.85
            )

        # Store all data and Matplotlib objects belonging to this run.
        new_run = {
            'run_number': self.run_counter,
            'label': label,
            'color': run_color,
            'x_data': [],
            'y_data': [],
            'y2_data': [],
            'line': run_line,
            'line2': run_line2
        }

        self.measurement_runs.append(new_run)
        self.current_run = new_run

        # Only use the primary line from each run in the legend.
        legend_lines = [run['line'] for run in self.measurement_runs]
        legend_labels = [run['label'] for run in self.measurement_runs]
        self.ax.legend(legend_lines, legend_labels, loc='best')

        self.canvas.draw_idle()

        return new_run

    def clear_all_runs(self):
        """Remove all measurement runs from the live plot."""

        # Remove every run's Matplotlib line objects.
        for run in self.measurement_runs:
            run_line = run.get('line')
            run_line2 = run.get('line2')

            if run_line is not None:
                run_line.remove()

            if run_line2 is not None:
                run_line2.remove()

        # Clear all stored run information.
        self.measurement_runs.clear()
        self.current_run = None
        self.run_counter = 0

        # Clear the temporary legacy single-run data.
        self.x_data.clear()
        self.y_data.clear()
        self.y2_data.clear()

        self.line.set_data([], [])

        if self.dual_axis and hasattr(self, 'line2'):
            self.line2.set_data([], [])

        # Remove the legend created for measurement runs.
        legend = self.ax.get_legend()

        if legend is not None:
            legend.remove()

        # Restore empty default axis ranges.
        self.ax.relim()
        self.ax.autoscale_view()

        if self.dual_axis and self.ax2 is not None:
            self.ax2.relim()
            self.ax2.autoscale_view()

        self.canvas.draw_idle()
        self.parent.update()
    
    def reset(self):
        """Clear all data and reset the plot for a new measurement."""
        self.x_data = []
        self.y_data = []
        self.y2_data = []
        
        self.line.set_data([], [])
        if self.dual_axis and hasattr(self, 'line2'):
            self.line2.set_data([], [])
        
        # Reset axis limits
        self.ax.relim()
        self.ax.autoscale_view()
        if self.dual_axis and self.ax2:
            self.ax2.relim()
            self.ax2.autoscale_view()
        
        self.canvas.draw_idle()
        self.parent.update()
    
    def add_point(self, x, y, y2=None):
        """
        Add a data point and update the plot.
        
        Args:
            x: X-axis value
            y: Y-axis value (primary)
            y2: Y-axis value (secondary, for dual-axis plots)
        """
        # Temporary compatibility path:
        # Until gui.py starts each measurement with start_new_run(),
        # continue using the original single-run data objects.
        if self.current_run is None:
            self.x_data.append(x)
            self.y_data.append(y)

            self.line.set_data(self.x_data, self.y_data)

            if self.dual_axis and y2 is not None:
                self.y2_data.append(y2)

                if hasattr(self, 'line2'):
                    self.line2.set_data(self.x_data, self.y2_data)

        else:
            # Store the point in the current measurement run.
            self.current_run['x_data'].append(x)
            self.current_run['y_data'].append(y)

            # Update the current run's primary line.
            self.current_run['line'].set_data(
                self.current_run['x_data'],
                self.current_run['y_data']
            )

            # Update the current run's secondary line for LIV plots.
            if (self.dual_axis and y2 is not None and self.current_run['line2'] is not None):
                self.current_run['y2_data'].append(y2)
                self.current_run['line2'].set_data(
                    self.current_run['x_data'],
                    self.current_run['y2_data']
                )
        
        # Rescale axes
        self.ax.relim()
        self.ax.autoscale_view()
        if self.dual_axis and self.ax2:
            self.ax2.relim()
            self.ax2.autoscale_view()
        
        # Redraw
        self.canvas.draw_idle()
        self.parent.update()
    
    def set_data(self, x_data, y_data, y2_data=None):
        """
        Set all data at once (useful for final update).
        
        Args:
            x_data: List of x values
            y_data: List of y values (primary)
            y2_data: List of y values (secondary, for dual-axis plots)
        """
        self.x_data = list(x_data)
        self.y_data = list(y_data)
        
        self.line.set_data(self.x_data, self.y_data)
        
        if self.dual_axis and y2_data is not None:
            self.y2_data = list(y2_data)
            if hasattr(self, 'line2'):
                self.line2.set_data(self.x_data, self.y2_data)
        
        self.ax.relim()
        self.ax.autoscale_view()
        if self.dual_axis and self.ax2:
            self.ax2.relim()
            self.ax2.autoscale_view()
        
        self.canvas.draw_idle()
        self.parent.update()
    
    def get_figure(self):
        """Return the matplotlib figure for saving."""
        return self.fig
    
    def save(self, filepath):
        """Save the current plot to a file."""
        self.fig.savefig(filepath, bbox_inches='tight', dpi=150)


class LivePlotLI(LivePlot):
    """Preset for L-I (Light vs Current) measurements."""
    
    def __init__(self, parent):
        super().__init__(
            parent,
            xlabel="Device Current (mA)",
            ylabel="Light Output (mW)",
            title="L-I Characteristic (Live)",
            color='blue'
        )


class LivePlotIV(LivePlot):
    """Preset for I-V measurements: voltage on x-axis, current on y-axis."""
    
    def __init__(self, parent):
        super().__init__(
            parent,
            xlabel="Device Voltage (V)",
            ylabel="Device Current (mA)",
            title="I-V Characteristic (Live)",
            color='green'
        )


class LivePlotLIV(LivePlot):
    """Preset for L-I-V (Light and Voltage vs Current) measurements."""
    
    def __init__(self, parent):
        super().__init__(
            parent,
            xlabel="Current (mA)",
            ylabel="Power per facet (mW)",
            ylabel2="Voltage (V)",
            title="LIV Characteristic (Live)",
            color='black',
            color2='blue'
        )


