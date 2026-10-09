# (C) Copyright 2024-2026 Blue Ocean Technologies, Inc., Toronto, ON
# All rights reserved.
#
# This software is provided without warranty under the terms of the AGPL-3.0
# license included in LICENSE and may be redistributed only under the
# conditions described in the aforementioned license. The license is also
# available online at https://www.gnu.org/licenses/agpl-3.0.txt
#
# Thanks for using Microdrop open source!

"""A lost serial port only suspends the heater data log: the next telemetry
packet after a reconnect resumes it in a fresh file, while an explicit stop
ends the run for good (#42)."""

# Standard library imports.
from pathlib import Path

# Third-party imports.
import pytest

# Microdrop package imports.
import heater_controller.data_logger as data_logger_module
from heater_controller.consts import HEATER_LOGS_DIR_NAME
from heater_controller.data_logger import HeaterDataLogger


@pytest.fixture
def experiment(monkeypatch, tmp_path):
    """Point the logger at a switchable fake experiment directory (None makes
    it unresolvable); mute the DATA_LOG_SAVED publish so no broker is
    needed."""
    current = {"dir": tmp_path / "experiment_a"}

    def get_current_experiment_directory():
        if current["dir"] is None:
            raise RuntimeError("no experiment directory")

        return current["dir"]

    monkeypatch.setattr(
        data_logger_module,
        "get_current_experiment_directory",
        get_current_experiment_directory,
    )
    monkeypatch.setattr(data_logger_module, "publish_message", lambda *args: None)

    return current


@pytest.fixture
def data_logger():
    data_logger = HeaterDataLogger()
    yield data_logger
    data_logger.stop()


def test_packet_after_suspend_resumes_in_a_new_file(experiment, tmp_path, data_logger):
    old_dir = tmp_path / "experiment_a" / HEATER_LOGS_DIR_NAME
    data_logger.start_new_log(old_dir)
    data_logger.log({"t": 1})
    first_file = data_logger._log_file.name

    data_logger.suspend()
    assert data_logger.armed and not data_logger.is_active

    experiment["dir"] = tmp_path / "experiment_b"
    data_logger.log({"t": 2})

    new_dir = tmp_path / "experiment_b" / HEATER_LOGS_DIR_NAME
    new_files = list(new_dir.iterdir())
    assert data_logger.is_active and data_logger.log_dir == new_dir
    assert len(new_files) == 1 and str(new_files[0]) != first_file
    assert '"t": 2' in new_files[0].read_text()
    assert '"t": 2' not in Path(first_file).read_text()


def test_packet_after_stop_opens_nothing(experiment, tmp_path, data_logger):
    log_dir = tmp_path / "experiment_a" / HEATER_LOGS_DIR_NAME
    data_logger.start_new_log(log_dir)
    data_logger.stop()

    data_logger.log({"t": 1})

    assert not data_logger.armed and not data_logger.is_active
    log_files = list(log_dir.iterdir())
    assert len(log_files) == 1 and log_files[0].read_text() == ""


def test_unresolvable_experiment_runs_unlogged_until_it_resolves(
    experiment, tmp_path, data_logger
):
    data_logger.start_new_log(tmp_path / "experiment_a" / HEATER_LOGS_DIR_NAME)
    data_logger.suspend()

    experiment["dir"] = None
    data_logger.log({"t": 1})
    assert data_logger.armed and not data_logger.is_active

    # The directory lookup is throttled; the next interval retries.
    experiment["dir"] = tmp_path / "experiment_b"
    data_logger._next_experiment_check = 0.0
    data_logger.log({"t": 2})

    new_files = list((tmp_path / "experiment_b" / HEATER_LOGS_DIR_NAME).iterdir())
    assert data_logger.is_active and len(new_files) == 1
    assert '"t": 1' not in new_files[0].read_text()
    assert '"t": 2' in new_files[0].read_text()


def test_restarting_the_log_closes_the_previous_handle(
    experiment, tmp_path, data_logger
):
    log_dir = tmp_path / "experiment_a" / HEATER_LOGS_DIR_NAME
    data_logger.start_new_log(log_dir)
    first_file = data_logger._log_file

    data_logger.start_new_log(log_dir)

    assert first_file.closed and data_logger._log_file is not first_file
    assert len(list(log_dir.iterdir())) == 2
