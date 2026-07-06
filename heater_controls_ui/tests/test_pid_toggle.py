"""Hardware-free tests for the dedicated PID on/off toggle (decoupled from the
Temp/PWM mode toggle).

`publish_message` is monkeypatched at the controller module (same pattern as
`heater_controller/tests/test_config_push.py`), so these exercise only the
publish-gating logic: the master-gate (stream_active) semantics, and that
`pid_enabled` is independent of `mode`.
"""
import json

import pytest

import heater_controls_ui.controller as controller_mod
from heater_controls_ui.controller import HeaterControlsController
from heater_controls_ui.model import HeaterStatusModel
from heater_controller.consts import SET_PID_MODE, SET_TEMPERATURE, SET_PWM


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


# --- model default ----------------------------------------------------------

def test_pid_enabled_defaults_true():
    # Preserves the legacy Temp-mode behavior (PID on) as the out-of-the-box state.
    assert HeaterStatusModel().pid_enabled is True


# --- publish gating: master gate (stream_active) ----------------------------

def test_pid_toggle_while_not_streaming_does_not_publish(published):
    controller, model = _controller()
    model.pid_enabled = False
    assert published == []


def test_pid_toggle_while_streaming_publishes_set_pid_mode(published):
    controller, model = _controller()
    model.stream_active = True
    published.clear()  # drop the stream-start SET_STREAM/_apply_pid_mode/_apply_mode publishes

    model.pid_enabled = False
    assert (SET_PID_MODE, {"mode": "disable"}) in published

    model.pid_enabled = True
    assert (SET_PID_MODE, {"mode": "enable"}) in published


# --- decoupling from mode ----------------------------------------------------

def test_pid_enabled_independent_of_mode(published):
    # PWM mode + PID on is allowed: flipping mode must not itself touch SET_PID_MODE.
    controller, model = _controller()
    model.mode = "PWM"
    model.stream_active = True
    published.clear()

    model.mode = "Temp"
    assert all(topic != SET_PID_MODE for topic, _ in published)
    assert (SET_TEMPERATURE, {"temperature": model.temperature}) in published

    model.mode = "PWM"
    assert all(topic != SET_PID_MODE for topic, _ in published)


def test_stream_start_reasserts_current_pid_enabled_state(published):
    # Board sync on stream start uses the CURRENT pid_enabled toggle, not a
    # mode-derived value: PWM mode + PID enabled must still assert "enable".
    controller, model = _controller()
    model.mode = "PWM"
    model.pid_enabled = True

    model.stream_active = True
    assert (SET_PID_MODE, {"mode": "enable"}) in published
    assert (SET_PWM, {"pwm": model.pwm}) in published
