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
transition (run-mode changes mid-stream keep the same file).
"""

# Standard library imports.
import io
import json
import threading
from datetime import datetime
from pathlib import Path

# Enthought library imports.
from traits.api import HasTraits, Instance

# Microdrop utils imports.
from microdrop_utils.dramatiq_pub_sub_helpers import publish_message

# Local imports.
from .consts import DATA_LOG_SAVED

# Logger import.
from logger.logger_service import get_logger

logger = get_logger(__name__)


class HeaterDataLogger(HasTraits):
    """JSON-Lines telemetry logger (one ``{"timestamp": ..., **packet}``
    object per line, flushed per packet so a crash loses nothing).

    ``start_new_log``/``stop`` run on dramatiq worker threads while
    ``log`` runs on the serial reader thread, so every file operation is
    serialized behind one lock.
    """

    #: Open file handle of the active log, or None while not logging.
    _log_file = Instance(io.IOBase)

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
        log_dir = Path(log_dir)
        with self._lock:
            self._close_locked()
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
        logger.info(f"Heater data log started: {log_path}")

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

    def _close_locked(self):
        if self._log_file is None:
            return
        log_name = self._log_file.name
        try:
            self._log_file.close()
        except OSError as e:
            logger.warning(f"Closing heater data log {log_name} failed: {e}")
        self._log_file = None
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
