"""Static matplotlib canvas for a loaded heater telemetry log.

The temperature plot of the live pane, drawn once per loaded log (the
model's ``revision`` bump) instead of on a timer: per-sensor temperatures
solid, per-heater PID temperatures dashed, x-axis in elapsed seconds.
Legend entries are clickable and toggle series exactly like the live
canvas; pan/zoom/save come from the matplotlib toolbar the view adds.
"""
import os

os.environ.setdefault("QT_API", "pyside6")
import matplotlib
matplotlib.use("QtAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg

from microdrop_style.colors import SUCCESS_COLOR

from .canvas import palette_color, theme_colors
from .consts import (
    SENSOR_PALETTE, HEATER_PALETTE, HIDDEN_LEGEND_ENTRY_ALPHA,
    SENSOR_SERIES_PREFIX, PID_SERIES_PREFIX, SETPOINT_SERIES_PREFIX,
)


class HeaterLogPlotCanvas(FigureCanvasQTAgg):
    """Static temperature canvas bound to a :class:`HeaterLogViewerModel`."""

    def __init__(self, model, parent=None):
        self._model = model
        self._figure = Figure(figsize=(6, 4), tight_layout=True)
        super().__init__(self._figure)
        self.setParent(parent)

        self._ax = self._figure.add_subplot(111)
        # Persistent artists: role-prefixed series key -> Line2D.
        self._sensor_lines = {}
        self._pid_lines = {}
        self._setpoint_lines = {}
        # Legend artist (line or text) -> role-prefixed series key.
        self._legend_entry_to_key = {}
        self._theme = None

        self._apply_theme()
        self.mpl_connect("pick_event", self._on_legend_pick)
        model.observe(self._on_revision_changed, "revision")
        self._redraw()

    def showEvent(self, event):
        # The theme may have flipped while the tab was hidden.
        if self._apply_theme():
            self._redraw()
        super().showEvent(event)

    def _on_revision_changed(self, event):
        self._redraw()

    # ------------------------------------------------------------------ #
    def _redraw(self):
        self._apply_theme()
        changed = self._update_lines(
            self._sensor_lines, self._model.sensor_series,
            SENSOR_PALETTE, "-", SENSOR_SERIES_PREFIX, str)
        changed |= self._update_lines(
            self._pid_lines, self._model.pid_series,
            HEATER_PALETTE, "--", PID_SERIES_PREFIX, "{} (PID)".format)
        changed |= self._update_lines(
            self._setpoint_lines, self._model.setpoint_series,
            [SUCCESS_COLOR], "--", SETPOINT_SERIES_PREFIX,
            lambda _name: "Setpoint")
        if changed:
            self._rebuild_legend()
        self._ax.relim(visible_only=True)
        self._ax.autoscale_view()
        self.draw_idle()

    def _update_lines(self, line_map, series, palette, linestyle,
                      key_prefix, label_fn):
        """Sync ``line_map`` to ``series`` (name -> (times, values)): create
        lines for new keys, drop vanished ones, push data into the rest.
        Returns True when the series set changed (legend rebuild)."""
        changed = False
        for name in [n for n in line_map if n not in series]:
            line_map.pop(name).remove()
            changed = True
        for i, name in enumerate(sorted(series)):
            line = line_map.get(name)
            if line is None:
                (line,) = self._ax.plot([], [], linestyle, linewidth=2,
                                        alpha=0.9, label=label_fn(name))
                line_map[name] = line
                changed = True
            line.set_color(palette_color(palette, i))
            line.set_data(*series[name])
            line.set_visible(
                f"{key_prefix}{name}" not in self._model.hidden_series)
        return changed

    # ------------------------------------------------------------------ #
    # Legend picking (show / hide individual lines)                        #
    # ------------------------------------------------------------------ #
    def _rebuild_legend(self):
        bg, text, grid = theme_colors()
        self._legend_entry_to_key.clear()
        keys, handles = [], []
        for key_prefix, line_map in (
                (SENSOR_SERIES_PREFIX, self._sensor_lines),
                (PID_SERIES_PREFIX, self._pid_lines),
                (SETPOINT_SERIES_PREFIX, self._setpoint_lines)):
            for name in sorted(line_map):
                keys.append(f"{key_prefix}{name}")
                handles.append(line_map[name])
        if not handles:
            if self._ax.get_legend() is not None:
                self._ax.get_legend().remove()
            return
        legend = self._ax.legend(
            handles=handles, loc="center left", bbox_to_anchor=(1.005, 0.5),
            facecolor=bg, edgecolor=grid, labelcolor=text, fontsize=8)
        for key, legend_line, legend_text in zip(
                keys, legend.get_lines(), legend.get_texts()):
            legend_line.set_picker(5)
            legend_text.set_picker(True)
            self._legend_entry_to_key[legend_line] = key
            self._legend_entry_to_key[legend_text] = key
            self._style_legend_entry(legend_line, key)

    def _on_legend_pick(self, event):
        key = self._legend_entry_to_key.get(event.artist)
        if key is None:
            return
        hidden = self._model.hidden_series
        if key in hidden:
            hidden.discard(key)
        else:
            hidden.add(key)
        self._apply_visibility()

    def _apply_visibility(self):
        hidden = self._model.hidden_series
        for key_prefix, line_map in (
                (SENSOR_SERIES_PREFIX, self._sensor_lines),
                (PID_SERIES_PREFIX, self._pid_lines),
                (SETPOINT_SERIES_PREFIX, self._setpoint_lines)):
            for name, line in line_map.items():
                line.set_visible(f"{key_prefix}{name}" not in hidden)
        for legend_entry, key in self._legend_entry_to_key.items():
            self._style_legend_entry(legend_entry, key)
        self._ax.relim(visible_only=True)
        self._ax.autoscale_view()
        self.draw_idle()

    def _style_legend_entry(self, legend_entry, key):
        if hasattr(legend_entry, "set_alpha"):
            legend_entry.set_alpha(
                HIDDEN_LEGEND_ENTRY_ALPHA
                if key in self._model.hidden_series else 1.0)

    # ------------------------------------------------------------------ #
    # Theme                                                                #
    # ------------------------------------------------------------------ #
    def _apply_theme(self):
        """Restyle the axis when the app theme flipped. Returns True when a
        restyle happened (the caller redraws)."""
        theme = theme_colors()
        if theme == self._theme:
            return False
        self._theme = theme
        bg, text, grid = theme
        self._figure.patch.set_facecolor(bg)
        self._ax.set_facecolor(bg)
        self._ax.set_title("Temperature", fontsize=11, fontweight="bold",
                           color=text)
        self._ax.set_ylabel("Temperature (°C)", fontsize=9, color=text)
        self._ax.set_xlabel("Elapsed time (s)", fontsize=9, color=text)
        self._ax.grid(True, alpha=0.3, color=grid)
        self._ax.tick_params(colors=text)
        for spine in self._ax.spines.values():
            spine.set_color(grid)
        self._rebuild_legend()
        return True
