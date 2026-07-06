"""Hardware-free tests for the PID on/off toggle and its board transitions.

`publish_message` is monkeypatched at the controller module (same pattern as
`heater_controller/tests/test_config_push.py`). The contract mirrors the
legacy standalone UI: the board enters PID mode via the temperature-setpoint
command (``pid_<h>_<temp>``), leaves it via ``pid_<h>_stop`` + a plain stream
restart, and §INFO pid_started/pid_stopped frames are the source of truth
(synced through ``updating_from_board`` without re-publishing).
"""
import json

import pytest

import heater_controls_ui.controller as controller_mod
from heater_controls_ui.controller import HeaterControlsController
from heater_controls_ui.model import HeaterStatusModel
from heater_controller.consts import (
    SET_PID_MODE, SET_TEMPERATURE, SET_PWM, SET_STREAM,
)


@pytest.fixture
def published(monkeypatch):
    sink = []
    monkeypatch.setattr(
        controller_mod, "publish_message",
        lambda message, topic=None, **k: sink.append((topic, json.loads(message))),
    )
    return sink


def _controller():
    model = HeaterStatusModel()
    return HeaterControlsController(model=model), model


def _topics(published):
    return [topic for topic, _ in published]


# --- model defaults -----------------------------------------------------------

def test_pid_enabled_defaults_off():
    # Closed-loop control is engaged explicitly by the user.
    assert HeaterStatusModel().pid_enabled is False


# --- staging (master gate off) --------------------------------------------------

def test_pid_toggle_while_not_streaming_stages_only(published):
    controller, model = _controller()
    model.pid_enabled = True
    assert published == []
    assert model.mode == "Temp"          # PID-on forces Temp even when staged


# --- PID on/off transitions while streaming -------------------------------------

def test_pid_on_stops_plain_stream_and_starts_pid_via_setpoint(published):
    controller, model = _controller()
    model.stream_active = True
    published.clear()

    model.pid_enabled = True
    assert (SET_STREAM, {"group": "stop"}) in published
    assert (SET_TEMPERATURE, {"temperature": model.temperature}) in published
    # There is no live "enable" on the board — the setpoint command starts PID.
    assert all(topic != SET_PID_MODE for topic, _ in published)
    assert model.mode == "Temp"


def test_pid_off_stops_pid_and_resumes_plain_stream(published):
    controller, model = _controller()
    model.stream_active = True
    model.pid_enabled = True
    published.clear()

    model.pid_enabled = False
    assert (SET_PID_MODE, {"mode": "stop"}) in published
    assert (SET_STREAM, {"group": "all"}) in published


def test_manual_pwm_applies_live_after_pid_off_and_mode_switch(published):
    # The exact user-reported regression: temp set -> PID off -> PWM mode ->
    # PWM edits must publish immediately (no stream restart needed).
    controller, model = _controller()
    model.stream_active = True
    model.pid_enabled = True
    model.temperature = 41    # distinct from the default so the edit fires
    model.pid_enabled = False
    model.mode = "PWM"
    published.clear()

    model.pwm = 25
    assert (SET_PWM, {"pwm": 25}) in published


def test_temperature_publishes_only_with_pid_on(published):
    controller, model = _controller()
    model.stream_active = True
    published.clear()

    model.temperature = 42               # PID off: staged, not published
    assert all(topic != SET_TEMPERATURE for topic, _ in published)

    model.pid_enabled = True
    published.clear()
    model.temperature = 45               # PID on: published live
    assert (SET_TEMPERATURE, {"temperature": 45}) in published


# --- stream start/stop ------------------------------------------------------------

def test_stream_start_with_pid_on_sends_setpoint_only(published):
    controller, model = _controller()
    model.pid_enabled = True

    model.stream_active = True
    assert (SET_TEMPERATURE, {"temperature": model.temperature}) in published
    # The pid setpoint command brings its own stream; no plain stream_all.
    assert all(topic != SET_STREAM for topic, _ in published)


def test_stream_start_with_pid_off_starts_plain_stream(published):
    controller, model = _controller()
    model.mode = "PWM"

    model.stream_active = True
    assert (SET_STREAM, {"group": "all"}) in published
    assert (SET_PWM, {"pwm": model.pwm}) in published
    assert all(topic not in (SET_TEMPERATURE, SET_PID_MODE) for topic, _ in published)


def test_stream_stop_with_pid_on_stops_pid(published):
    controller, model = _controller()
    model.stream_active = True
    model.pid_enabled = True
    published.clear()

    model.stream_active = False
    assert (SET_PID_MODE, {"mode": "stop"}) in published
    assert (SET_STREAM, {"group": "stop"}) in published


# --- board-reported state (telemetry sync) ----------------------------------------

def test_board_sync_does_not_republish(published):
    controller, model = _controller()
    model.stream_active = True
    published.clear()

    model.updating_from_board = True
    try:
        model.pid_enabled = True
        model.mode = "Temp"
    finally:
        model.updating_from_board = False
    assert published == []               # echo guard: no command loop

    published.clear()
    model.temperature = 50               # subsequent USER edits still publish
    assert (SET_TEMPERATURE, {"temperature": 50}) in published
