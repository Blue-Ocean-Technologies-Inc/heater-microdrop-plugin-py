# (C) Copyright 2024-2026 Blue Ocean Technologies, Inc., Toronto, ON
# All rights reserved.
#
# This software is provided without warranty under the terms of the AGPL-3.0
# license included in LICENSE and may be redistributed only under the
# conditions described in the aforementioned license. The license is also
# available online at https://www.gnu.org/licenses/agpl-3.0.txt
#
# Thanks for using Microdrop open source!

"""Telemetry log collection — port of the legacy standalone UI's
DataLogger. While the board streams, every telemetry packet is appended
as one timestamped JSON line to a file under the current experiment's
``heater_logs`` folder; a fresh file starts on every stream OFF -> ON
transition (run-mode changes mid-stream keep the same file), and an open
log rolls over into the new experiment's folder when the experiment
changes mid-stream.
"""

# Standard library imports.
import io
import json
import threading
import time
from datetime import datetime
from pathlib import Path

# Enthought library imports.
from traits.api import Float, HasTraits, Instance

# Microdrop package imports.
from microdrop_application.helpers import get_current_experiment_directory

# Microdrop utils imports.
from microdrop_utils.dramatiq_pub_sub_helpers import publish_message

# Local imports.
from .consts import DATA_LOG_SAVED, EXPERIMENT_CHECK_INTERVAL_S, HEATER_LOGS_DIR_NAME

# Logger import.
from logger.logger_service import get_logger

logger = get_logger(__name__)


def current_heater_logs_directory():
    """Return the current experiment's heater_logs folder, re-read from
    app-globals on every call so experiment switches are picked up."""
    return get_current_experiment_directory() / HEATER_LOGS_DIR_NAME


class HeaterDataLogger(HasTraits):
    """JSON-Lines telemetry logger (one ``{"timestamp": ..., **packet}``
    object per line, flushed per packet so a crash loses nothing).

    ``start_new_log``/``stop`` run on dramatiq worker threads while
    ``log`` runs on the serial reader thread, so every file operation is
    serialized behind one lock.
    """

    #: Open file handle of the active log, or None while not logging.
    _log_file = Instance(io.IOBase)

    #: Folder of the active log, or None while not logging.
    log_dir = Instance(Path)

    #: Monotonic time of the next experiment re-check (follow_experiment).
    _next_experiment_check = Float(0.0)

    # Typed by the lock object's class: threading.Lock is only a class from
    # Python 3.12 on (a factory function before, which Traits would validate
    # against instead -- rejecting every real lock).
    _lock = Instance(type(threading.Lock()))

    def __lock_default(self):
        return threading.Lock()

    @property
    def is_active(self) -> bool:
        """True while a log file is open (i.e. a stream is being logged)."""
        with self._lock:
            return self._log_file is not None

    def start_new_log(self, log_dir):
        """Close any active log and start a fresh timestamped file in
        ``log_dir`` (created if needed)."""
        with self._lock:
            self._close_locked()
            self._open_locked(Path(log_dir))

    def roll_over_to(self, log_dir):
        """Move an active log into ``log_dir``: close the current file and
        start a fresh one there. No-op while not logging or when the log
        already writes into ``log_dir`` — checked under the lock, so a
        concurrent ``stop`` can never be undone by a reopen."""
        log_dir = Path(log_dir)

        with self._lock:
            if self._log_file is None or log_dir == self.log_dir:
                return

            logger.info(
                f"Experiment changed while streaming; heater data log rolls "
                f"over from {self.log_dir} to {log_dir}"
            )
            self._close_locked()
            self._open_locked(log_dir)

    def follow_experiment(self):
        """Roll an active log over into the current experiment's
        heater_logs folder once the experiment has changed. Throttled to
        one app-globals read per EXPERIMENT_CHECK_INTERVAL_S, so it is
        cheap to call per telemetry packet."""
        now = time.monotonic()

        if not self.is_active or now < self._next_experiment_check:
            return

        self._next_experiment_check = now + EXPERIMENT_CHECK_INTERVAL_S

        try:
            log_dir = current_heater_logs_directory()
        except Exception as e:
            # Keep logging into the current folder; the next check retries.
            logger.debug(f"Could not re-resolve the experiment directory: {e}")
            return

        self.roll_over_to(log_dir)

    def log(self, packet):
        """Append one telemetry packet with a host wall-clock ISO
        ``timestamp`` (mirrors the legacy DataLogger.log_data). Some
        firmware frames carry their OWN ``timestamp`` (board uptime
        seconds) — that moves to ``board_timestamp`` so it can't clobber
        the wall clock the viewer's timeline needs. No-op while no log is
        active."""
        record = dict(packet)
        if "timestamp" in record:
            record["board_timestamp"] = record.pop("timestamp")
        record = {"timestamp": datetime.now().isoformat(), **record}
        with self._lock:
            if self._log_file is None:
                return
            try:
                self._log_file.write(json.dumps(record) + "\n")
                self._log_file.flush()
            except OSError as e:
                logger.warning(f"Heater data log write failed: {e}")
                self._close_locked()

    def stop(self):
        """Close the active log (no-op when none is active)."""
        with self._lock:
            self._close_locked()

    def _open_locked(self, log_dir):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = log_dir / f"{timestamp}.jsonl"

        try:
            log_dir.mkdir(parents=True, exist_ok=True)

            # Same-second restarts must not truncate the previous log.
            counter = 1

            while log_path.exists():
                log_path = log_dir / f"{timestamp}_{counter}.jsonl"
                counter += 1

            self._log_file = log_path.open("w", encoding="utf-8")
        except OSError as e:
            logger.warning(f"Could not start heater data log {log_path}: {e}")
            return

        self.log_dir = log_dir
        logger.info(f"Heater data log started: {log_path}")

    def _close_locked(self):
        if self._log_file is None:
            return
        log_name = self._log_file.name
        try:
            self._log_file.close()
        except OSError as e:
            logger.warning(f"Closing heater data log {log_name} failed: {e}")
        self._log_file = None
        self.log_dir = None
        logger.info(f"Heater data log saved: {log_name}")
        # Announce the finished log (the Log Viewer tab auto-shows it).
        try:
            publish_message(log_name, DATA_LOG_SAVED)
        except Exception as e:
            # Tolerated no-broker path (tests / standalone demos).
            logger.debug(f"Could not publish {DATA_LOG_SAVED}: {e}")


#: Process-wide logger: the serial proxy's reader thread feeds it telemetry
#: packets; the command service starts/stops files around the stream
#: transitions. One instance regardless of proxy reconnects.
heater_data_logger = HeaterDataLogger()
