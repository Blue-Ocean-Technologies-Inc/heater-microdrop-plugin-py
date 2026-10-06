# (C) Copyright 2024-2026 Blue Ocean Technologies, Inc., Toronto, ON
# All rights reserved.
#
# This software is provided without warranty under the terms of the AGPL-3.0
# license included in LICENSE and may be redistributed only under the
# conditions described in the aforementioned license. The license is also
# available online at https://www.gnu.org/licenses/agpl-3.0.txt
#
# Thanks for using Microdrop open source!

"""An open heater data log rolls over into the new experiment's heater_logs
folder when the experiment changes mid-stream (#33)."""

# Third-party imports.
import pytest

# Microdrop package imports.
import heater_controller.data_logger as data_logger_module
from heater_controller.consts import HEATER_LOGS_DIR_NAME
from heater_controller.data_logger import HeaterDataLogger


@pytest.fixture
def experiment(monkeypatch, tmp_path):
    """Point the logger at a switchable fake experiment directory; mute the
    DATA_LOG_SAVED publish so no broker is needed."""
    current = {"dir": tmp_path / "experiment_a"}
    monkeypatch.setattr(
        data_logger_module, "get_current_experiment_directory", lambda: current["dir"]
    )
    monkeypatch.setattr(data_logger_module, "publish_message", lambda *args: None)

    return current


@pytest.fixture
def data_logger():
    data_logger = HeaterDataLogger()
    yield data_logger
    data_logger.stop()


def test_streaming_experiment_change_rolls_log_over(experiment, tmp_path, data_logger):
    old_dir = tmp_path / "experiment_a" / HEATER_LOGS_DIR_NAME
    new_dir = tmp_path / "experiment_b" / HEATER_LOGS_DIR_NAME
    data_logger.start_new_log(old_dir)
    data_logger.log({"t": 1})

    experiment["dir"] = tmp_path / "experiment_b"
    data_logger.follow_experiment()
    data_logger.log({"t": 2})

    assert data_logger.log_dir == new_dir
    old_files, new_files = list(old_dir.iterdir()), list(new_dir.iterdir())
    assert len(old_files) == 1 and len(new_files) == 1
    assert '"t": 1' in old_files[0].read_text()
    assert '"t": 2' in new_files[0].read_text()


def test_not_streaming_does_nothing(experiment, tmp_path, data_logger):
    experiment["dir"] = tmp_path / "experiment_b"
    data_logger.follow_experiment()

    assert not data_logger.is_active
    assert not (tmp_path / "experiment_b").exists()


def test_same_experiment_keeps_the_file(experiment, tmp_path, data_logger):
    log_dir = tmp_path / "experiment_a" / HEATER_LOGS_DIR_NAME
    data_logger.start_new_log(log_dir)
    open_file = data_logger._log_file

    data_logger.follow_experiment()

    assert data_logger._log_file is open_file
    assert len(list(log_dir.iterdir())) == 1


def test_checks_are_throttled(experiment, tmp_path, data_logger):
    data_logger.start_new_log(tmp_path / "experiment_a" / HEATER_LOGS_DIR_NAME)
    data_logger.follow_experiment()

    # A switch right after a check waits for the next interval.
    experiment["dir"] = tmp_path / "experiment_b"
    data_logger.follow_experiment()
    assert data_logger.log_dir == tmp_path / "experiment_a" / HEATER_LOGS_DIR_NAME

    data_logger._next_experiment_check = 0.0
    data_logger.follow_experiment()
    assert data_logger.log_dir == tmp_path / "experiment_b" / HEATER_LOGS_DIR_NAME
