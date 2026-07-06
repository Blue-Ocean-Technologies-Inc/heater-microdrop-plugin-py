"""Hardware-free tests for the PID toggle / stream transitions (frontend side).

The controller is a direct port of the legacy standalone UI's slots: every
run-mode transition publishes ONE request (START_STREAM / STOP_STREAM) and the
backend executes the legacy stop -> delay -> start serial sequence atomically
(see heater_controller/tests/test_stream_transitions.py for that half).
`publish_message` is monkeypatched at the controller module.
"""
import json

import pytest

import heater_controls_ui.controller as controller_mod
from heater_controls_ui.controller import HeaterControlsController
from heater_controls_ui.model import HeaterStatusModel
from heater_controller.consts import (
    SET_TEMPERATURE, SET_PWM, START_STREAM, STOP_STREAM,
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


# --- model defaults -----------------------------------------------------------

def test_pid_enabled_defaults_off():
    assert HeaterStatusModel().pid_enabled is False


# --- staging (master gate off) --------------------------------------------------

def test_pid_toggle_while_not_streaming_stages_only(published):
    controller, model = _controller()
    model.pid_enabled = True
    assert published == []
    assert model.mode == "Temp"          # PID-on forces Temp even when staged


# --- stream start/stop (one request each, legacy start_stream/stop_stream) ------

def test_stream_start_with_pid_on_requests_pid_start(published):
    controller, model = _controller()
    model.pid_enabled = True

    model.stream_active = True
    assert published == [(START_STREAM, {
        "pid": True, "temperature": model.temperature, "sensor_group": "all"})]


def test_stream_start_in_pwm_mode_carries_the_duty(published):
    controller, model = _controller()
    model.mode = "PWM"

    model.stream_active = True
    assert published == [(START_STREAM, {
        "pid": False, "pwm": model.pwm, "sensor_group": "all"})]


def test_stream_stop_is_one_request_with_all_off(published):
    controller, model = _controller()
    model.stream_active = True
    published.clear()

    model.stream_active = False
    assert published == [(STOP_STREAM, {"all_off": True})]


# --- PID toggle while streaming = restart (legacy on_pid_toggled) ----------------

def test_pid_toggle_while_streaming_restarts_stream(published):
    controller, model = _controller()
    model.stream_active = True
    published.clear()

    model.pid_enabled = True
    assert model.mode == "Temp"
    assert published == [(START_STREAM, {
        "pid": True, "temperature": model.temperature, "sensor_group": "all"})]

    published.clear()
    model.pid_enabled = False
    assert published == [(START_STREAM, {"pid": False, "sensor_group": "all"})]


def test_manual_pwm_applies_live_after_pid_off_and_mode_switch(published):
    # The reported regression: temp set -> PID off -> PWM mode -> PWM edits
    # publish immediately (the PID-off restart put the board on a plain stream).
    controller, model = _controller()
    model.stream_active = True
    model.pid_enabled = True
    model.temperature = 41
    model.pid_enabled = False
    model.mode = "PWM"
    published.clear()

    model.pwm = 25
    assert (SET_PWM, {"pwm": 25}) in published


# --- setpoint edits ---------------------------------------------------------------

def test_temperature_publishes_only_with_pid_on(published):
    controller, model = _controller()
    model.stream_active = True
    published.clear()

    model.temperature = 42               # PID off: staged, not published
    assert all(topic != SET_TEMPERATURE for topic, _ in published)

    model.pid_enabled = True
    published.clear()
    model.temperature = 45               # PID on: published live
    assert (SET_TEMPERATURE, {"temperature": 45, "sensor_group": "all"}) in published


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

    model.temperature = 50               # subsequent USER edits still publish
    assert (SET_TEMPERATURE, {"temperature": 50, "sensor_group": "all"}) in published


# --- sensor group (legacy dropdown) -------------------------------------------

def test_sensor_group_defaults_all():
    assert HeaterStatusModel().sensor_group == "all"


def test_sensor_group_change_while_streaming_restarts(published):
    controller, model = _controller()
    model.stream_active = True
    published.clear()

    model.sensor_group = "thermistors"
    assert published == [(START_STREAM, {"pid": False, "sensor_group": "thermistors"})]


def test_sensor_group_none_omits_suffix(published):
    controller, model = _controller()
    model.sensor_group = "None"
    model.stream_active = True
    assert published == [(START_STREAM, {"pid": False})]
