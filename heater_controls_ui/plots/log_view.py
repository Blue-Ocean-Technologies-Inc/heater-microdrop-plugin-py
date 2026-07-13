"""TraitsUI panel for the heater Log Viewer tab.

Mirrors the Recording Viewer's browsing surface: a folder button (defaults
to the current experiment's heater_logs), home/refresh, a log dropdown,
the loaded log's human-readable start/end times, and the static plot with
the matplotlib pan/zoom/save/configure toolbar. Embedded in the Heater
Plots dock pane as its second tab (``edit_traits(kind="subpanel")``).
"""
from pathlib import Path

from pyface.api import DirectoryDialog, OK
from traits.api import Button, Instance, observe
from traitsui.api import (
    Controller, CustomEditor, EnumEditor, HGroup, Item, Readonly, UItem,
    VGroup, View,
)
from PySide6.QtWidgets import QSizePolicy, QVBoxLayout, QWidget
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT

from microdrop_application.helpers import get_current_experiment_directory
from microdrop_style.icons.icons import (
    ICON_FOLDER_OPEN, ICON_HOME, ICON_REFRESH,
)
from microdrop_utils.traitsui_qt_helpers import IconButtonEditor
from logger.logger_service import get_logger

from heater_controller.consts import HEATER_LOGS_DIR_NAME

from .consts import LOG_FILE_GLOB
from .log_canvas import HeaterLogPlotCanvas
from .log_model import HeaterLogViewerModel

logger = get_logger(__name__)


def log_canvas_factory(parent, editor):
    """TraitsUI CustomEditor factory: the static log canvas stacked under
    its matplotlib navigation toolbar (pan / zoom / save / configure —
    the same controls the live tab offers). ``editor.object`` is the
    :class:`HeaterLogViewerModel` (the Controller's view context).
    ``parent`` is unused: TraitsUI hands the enclosing LAYOUT here (not a
    widget) and reparents the returned control itself."""
    container = QWidget()
    # A bare QWidget defaults to a Preferred policy, which pins the plot
    # at the figure's default pixel size however tall the pane is.
    container.setSizePolicy(QSizePolicy.Policy.Expanding,
                            QSizePolicy.Policy.Expanding)
    layout = QVBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    canvas = HeaterLogPlotCanvas(editor.object, parent=container)
    layout.addWidget(NavigationToolbar2QT(canvas, container))
    # stretch=1: the canvas (not the fixed toolbar) absorbs the height.
    layout.addWidget(canvas, 1)
    # MUST return the container, not the canvas: the canvas is the
    # container's CHILD, and returning only the child leaves the parentless
    # container to the garbage collector, which deletes the canvas's C++
    # object with it before TraitsUI even lays it out.
    return container


LogView = View(
        VGroup(
            HGroup(
                UItem("handler.directory_button", editor=IconButtonEditor(
                    glyph=ICON_FOLDER_OPEN,
                    tooltip="Choose the heater logs folder (defaults to "
                            "the current experiment's heater_logs)")),
                UItem("handler.home_button", editor=IconButtonEditor(
                    glyph=ICON_HOME,
                    tooltip="Back to the current experiment's heater logs "
                            "(newest log)")),
                UItem("handler.refresh_button", editor=IconButtonEditor(
                    glyph=ICON_REFRESH,
                    tooltip="Re-scan the current folder for new logs")),
                Item("selected_log", label="Log",
                     editor=EnumEditor(name="log_names"),
                     springy=True),
            ),
            HGroup(
                Readonly("directory", label="Folder", springy=True),
            ),
            HGroup(
                Readonly("start_time_text", label="Start"),
                Readonly("end_time_text", label="End"),
            ),
            # The canvas rides a model trait so editor.object is the model
            # (which trait doesn't matter — the factory builds once).
            # springy: this row takes ALL leftover vertical space (the
            # toolbar/label rows above stay at their natural heights).
            UItem("sensor_series", editor=CustomEditor(log_canvas_factory),
                  springy=True),
        ),
        resizable=True,
    )


class HeaterLogViewerController(Controller):
    """Owns the log viewer model and its browsing behaviour."""

    model = Instance(HeaterLogViewerModel, ())

    #: Choose the heater logs folder to browse.
    directory_button = Button()
    #: Back to the current experiment's heater logs (newest log).
    home_button = Button()
    #: Re-scan the browsed folder for new logs.
    refresh_button = Button()

    def traits_init(self):
        self._go_home()

    # ------------------------------------------------------------------ #
    # Discovery (mirrors the Recording Viewer's browsing behaviour)        #
    # ------------------------------------------------------------------ #
    @observe("directory_button")
    def _pick_directory(self, event):
        dialog = DirectoryDialog(default_path=self.model.directory or "")
        if dialog.open() == OK:
            self.model.directory = dialog.path

    @observe("refresh_button")
    def _on_refresh(self, event):
        self._refresh_logs()

    @observe("model")
    @observe("home_button")
    def _go_home(self, event=None):
        """Point at the current experiment's heater_logs folder."""
        try:
            experiment_directory = get_current_experiment_directory()
        except Exception as e:
            logger.debug(f"No current experiment directory: {e}")
            return
        logs_directory = Path(experiment_directory) / HEATER_LOGS_DIR_NAME
        if str(logs_directory) == self.model.directory:
            self._refresh_logs()   # same folder: re-scan for new logs
        else:
            self.model.directory = str(logs_directory)

    @observe("model.directory")
    def _refresh_logs(self, event=None):
        directory = (Path(self.model.directory)
                     if self.model.directory else None)
        logs = []
        if directory is not None and directory.is_dir():
            logs = sorted(directory.glob(LOG_FILE_GLOB),
                          key=lambda path: path.stat().st_mtime)
        self.model.log_files = logs
        if logs:
            # Newest log is usually the one of interest.
            newest_log_name = logs[-1].name
            if self.model.selected_log == newest_log_name:
                # Same selection: re-read anyway — an active stream keeps
                # appending to the newest log.
                self._load_selected(None)
            else:
                self.model.selected_log = newest_log_name
        else:
            self.model.selected_log = ""
            self.model.clear()

    @observe("model.selected_log")
    def _load_selected(self, event):
        for path in self.model.log_files:
            if path.name == self.model.selected_log:
                self.model.load(path)
                return

    @observe("model.saved_log_path")
    def _show_saved_log(self, event):
        """The backend finished writing a log (DATA_LOG_SAVED): browse to
        it and select it — the latest COMPLETE log, which on a mid-run
        rollover is not the newest file (that one is still being
        written)."""
        saved_path = Path(event.new)
        if str(saved_path.parent) != self.model.directory:
            self.model.directory = str(saved_path.parent)  # scans + selects
        else:
            self._refresh_logs()
        if (saved_path.name in self.model.log_names
                and self.model.selected_log != saved_path.name):
            self.model.selected_log = saved_path.name
