"""Qt-free HasTraits model for the heater log viewer tab: the browsed
heater_logs folder, its discovered ``.jsonl`` telemetry logs (written by
heater_controller.data_logger), and the loaded log's plottable series.
Static — a log is parsed once when selected. Mutated only on the GUI
thread (toolbar buttons, combo selection), so no Qt bridging is needed.
"""
import json
from datetime import datetime
from pathlib import Path

from traits.api import (
    Dict, Directory, Event, HasTraits, Int, List, Property, Set, Str,
)

from heater_controls_ui.telemetry import telemetry_samples
from logger.logger_service import get_logger

from .consts import LOG_TIME_DISPLAY_FORMAT

logger = get_logger(__name__)


def parse_heater_log(text):
    """``(start_dt, end_dt, sensor_series, pid_series, setpoint_series)``
    from a JSON-Lines telemetry log. Each series maps a name to
    ``([elapsed_s], [values])``. Packets are filtered through the live
    plot's :func:`telemetry_samples`, so both views drop the same
    sentinels/frames. Torn or foreign lines are skipped.

    The elapsed timeline uses the INSTRUMENT's clock whenever a packet
    carries one — ``board_timestamp`` (the data logger preserves the
    firmware's stamp there), or the bare numeric ``timestamp`` of legacy
    logs — rebased to the first plottable packet (only those, because the
    firmware stamps INFO frames from a different clock). Lines with no
    board clock fall back to the host wall-clock ISO ``timestamp``, which
    always provides start_dt/end_dt (None when a log carries none).
    ``setpoint_series`` is the PID target (``pid_target``) per heater."""
    sensor_series, pid_series, setpoint_series = {}, {}, {}
    start_dt = end_dt = None
    first_board_stamp = None
    previous_board_stamp = None
    board_clock_offset = 0.0
    host_anchor_dt = None
    for line in text.splitlines():
        try:
            record = json.loads(line)
        except Exception:
            continue
        if not isinstance(record, dict):
            continue
        sample = telemetry_samples(record)
        # Wall-clock span from the host ISO timestamps (every line counts).
        stamp = record.get("timestamp")
        stamp_dt = None
        if isinstance(stamp, str):
            try:
                stamp_dt = datetime.fromisoformat(stamp)
            except ValueError:
                stamp_dt = None
            if stamp_dt is not None:
                if start_dt is None:
                    start_dt = stamp_dt
                end_dt = stamp_dt
        if not sample:
            continue
        board_stamp = record.get("board_timestamp")
        if not isinstance(board_stamp, (int, float)):
            # Legacy logs: the firmware's stamp sat directly on timestamp.
            board_stamp = stamp if isinstance(stamp, (int, float)) else None
        if board_stamp is not None:
            board_stamp = float(board_stamp)
            if first_board_stamp is None:
                first_board_stamp = board_stamp
            elif board_stamp < previous_board_stamp:
                # The firmware's stream clock RESTARTS on run-mode changes,
                # and one log spans a whole stream session (PID flips
                # included): keep the timeline monotonic by continuing
                # where the previous clock left off.
                board_clock_offset += previous_board_stamp - board_stamp
            previous_board_stamp = board_stamp
            elapsed_s = board_stamp + board_clock_offset - first_board_stamp
        elif stamp_dt is not None:
            if host_anchor_dt is None:
                host_anchor_dt = stamp_dt
            elapsed_s = (stamp_dt - host_anchor_dt).total_seconds()
        else:
            continue
        for name, value in sample.get("temperatures", {}).items():
            times, values = sensor_series.setdefault(name, ([], []))
            times.append(elapsed_s)
            values.append(value)
        if "pid_temperature" in sample:
            times, values = pid_series.setdefault(sample["heater"], ([], []))
            times.append(elapsed_s)
            values.append(sample["pid_temperature"])
        pid_target = record.get("pid_target")
        if "heater" in sample and isinstance(pid_target, (int, float)):
            times, values = setpoint_series.setdefault(
                sample["heater"], ([], []))
            times.append(elapsed_s)
            values.append(float(pid_target))
    return start_dt, end_dt, sensor_series, pid_series, setpoint_series


def fallback_time_span(log_path):
    """Approximate ``(start_dt, end_dt)`` for legacy logs whose packets
    carry no wall clock (the firmware's uptime clobbered the host
    timestamp before board_timestamp existed): the data logger names every
    file with its start time, and the last write (mtime) marks the end."""
    log_path = Path(log_path)
    name_parts = log_path.stem.split("_")
    try:
        start_dt = datetime.strptime("_".join(name_parts[:2]),
                                     "%Y%m%d_%H%M%S")
    except ValueError:
        return None, None
    try:
        end_dt = datetime.fromtimestamp(log_path.stat().st_mtime)
    except OSError:
        end_dt = None
    return start_dt, end_dt


class HeaterLogViewerModel(HasTraits):
    """State for the static heater-log plot."""

    #: Folder being browsed (a heater_logs folder; the home button points
    #: it at the current experiment's).
    directory = Directory()

    #: Discovered telemetry logs in the browsed folder (Path objects),
    #: oldest first.
    log_files = List()

    #: Basename choices for the log dropdown (mirrors ``log_files``).
    log_names = Property(List(Str), observe="log_files.items")

    #: Basename of the loaded log — the dropdown selection.
    selected_log = Str()

    #: Human-readable first/last packet times of the loaded log.
    start_time_text = Str("-")
    end_time_text = Str("-")

    #: Loaded series: name -> ([elapsed_s], [temperature values]).
    sensor_series = Dict()
    pid_series = Dict()
    #: PID target per heater (the live plot's green Setpoint line).
    setpoint_series = Dict()

    #: Role-prefixed series keys hidden from the plot via the legend
    #: (same key scheme as the live HeaterPlotModel).
    hidden_series = Set()

    #: Bumped whenever a log finished loading; the canvas redraws on this.
    revision = Int(0)

    #: Fired (with the saved file's path) when the backend finishes
    #: writing a log — the controller browses to and selects that log.
    saved_log_path = Event()

    def _get_log_names(self):
        return [path.name for path in self.log_files]

    def load(self, log_path):
        """Parse ``log_path`` into the plottable series and time span."""
        try:
            text = Path(log_path).read_text(encoding="utf-8")
        except OSError as e:
            logger.warning(f"Could not read heater log {log_path}: {e}")
            return
        (start_dt, end_dt, sensor_series, pid_series,
         setpoint_series) = parse_heater_log(text)
        if start_dt is None:
            start_dt, end_dt = fallback_time_span(log_path)
        self.start_time_text = (start_dt.strftime(LOG_TIME_DISPLAY_FORMAT)
                                if start_dt else "-")
        self.end_time_text = (end_dt.strftime(LOG_TIME_DISPLAY_FORMAT)
                              if end_dt else "-")
        self.sensor_series = sensor_series
        self.pid_series = pid_series
        self.setpoint_series = setpoint_series
        self.revision += 1
        logger.info(f"Heater log loaded: {log_path} "
                    f"({self.start_time_text} -> {self.end_time_text})")

    def clear(self):
        """Empty the plot (no log selected / folder empty)."""
        self.start_time_text = "-"
        self.end_time_text = "-"
        self.sensor_series = {}
        self.pid_series = {}
        self.setpoint_series = {}
        self.revision += 1
