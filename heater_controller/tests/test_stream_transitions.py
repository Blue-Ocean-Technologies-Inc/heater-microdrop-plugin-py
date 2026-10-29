# (C) Copyright 2024-2026 Blue Ocean Technologies, Inc., Toronto, ON
# All rights reserved.
#
# This software is provided without warranty under the terms of the AGPL-3.0
# license included in LICENSE and may be redistributed only under the
# conditions described in the aforementioned license. The license is also
# available online at https://www.gnu.org/licenses/agpl-3.0.txt
#
# Thanks for using Microdrop open source!

"""Hardware-free tests for the start_stream / stop_stream run-mode transitions
(ports of the legacy standalone UI's start_stream/stop_stream).

The whole stop-current -> delay -> start-new sequence must run inside one
handler invocation, in order — that ordering is the reason these exist as
single requests rather than separate pub/sub messages. ``time.sleep`` is
monkeypatched so the tests record the delay without waiting for it.

The protocol-start ensure_stream is the transition's opposite: it starts a
plain stream only from idle and never stops or restarts a running one.
Every stream on/off change is announced on STREAM_STATE.
"""

# Standard library imports.
import json
import threading

# Third-party imports.
import pytest

# Microdrop package imports.
import heater_controller.services.heater_command_setter_service as svc_mod
from heater_controller.consts import STREAM_STATE
from heater_controller.heater_serial_proxy import HeaterSerialProxy
from heater_controller.services.heater_command_setter_service import (
    HeaterCommandSetterService,
)


class _Msg:
    def __init__(self, content):
        self.content = content


@pytest.fixture
def service(monkeypatch):
    """A command-setter on a fake proxy; sleeps are recorded as '<sleep>'
    markers in the sent-command list so ordering is assertable."""
    proxy = HeaterSerialProxy.__new__(HeaterSerialProxy)
    proxy.transaction_lock = threading.Lock()
    proxy.sent = []
    proxy.send_command = lambda cmd: proxy.sent.append(cmd)
    monkeypatch.setattr(svc_mod.time, "sleep", lambda s: proxy.sent.append("<sleep>"))
    return HeaterCommandSetterService(proxy=proxy)


def test_start_stream_pid_from_idle(service):
    service.on_start_stream_request(_Msg('{"pid": true, "temperature": 40}'))
    # Not in PID yet -> stream_stop first, then the PID-starting setpoint.
    assert service.proxy.sent == ["stream_stop", "<sleep>", "pid_tec1_40.0"]
    assert service._pid_active is True


def test_start_stream_plain_after_pid(service):
    service.on_start_stream_request(_Msg('{"pid": true, "temperature": 40}'))
    service.proxy.sent.clear()

    service.on_start_stream_request(_Msg('{"pid": false, "pwm": 25}'))
    # Leaving PID -> pid_stop first, then the plain stream + staged duty.
    assert service.proxy.sent == ["pid_stop", "<sleep>", "stream_all", "pwm_tec1_25"]
    assert service._pid_active is False


def test_start_stream_plain_without_pwm(service):
    service.on_start_stream_request(_Msg('{"pid": false}'))
    assert service.proxy.sent == ["stream_stop", "<sleep>", "stream_all"]


def test_stop_stream_branches_on_pid_active(service):
    service.on_stop_stream_request(_Msg('{"all_off": true}'))
    assert service.proxy.sent == ["stream_stop", "all_off"]

    service.proxy.sent.clear()
    service.on_start_stream_request(_Msg('{"pid": true, "temperature": 40}'))
    service.proxy.sent.clear()
    service.on_stop_stream_request(_Msg('{"all_off": true}'))
    assert service.proxy.sent == ["pid_stop", "all_off"]
    assert service._pid_active is False


def test_start_stream_pid_requires_temperature(service):
    service.on_start_stream_request(_Msg('{"pid": true}'))
    assert service.proxy.sent == []  # invalid payload rejected, no commands


# --- protocol-start ensure_stream (start only when not streaming) ------------


def test_ensure_stream_from_idle_starts_plain_stream(service):
    service.on_ensure_stream_request(_Msg('{"heater": "tec1"}'))
    # No stop -> delay transition and no PID change: just the plain stream.
    assert service.proxy.sent == ["stream_all"]
    assert service._stream_active is True
    assert service._pid_active is False


def test_ensure_stream_honours_sensor_group(service):
    service.on_ensure_stream_request(_Msg('{"sensor_group": "thermistors"}'))
    assert service.proxy.sent == ["stream_thermistors"]


@pytest.mark.parametrize(
    "start",
    [
        lambda s: s.on_start_stream_request(_Msg('{"pid": false}')),
        lambda s: s.on_start_stream_request(_Msg('{"pid": true, "temperature": 40}')),
        lambda s: s.on_protocol_set_temperature_request(
            _Msg('{"temperature": 60, "tolerance": 2}')
        ),
    ],
    ids=["plain_stream", "pid_stream", "protocol_pid_stream"],
)
def test_ensure_stream_leaves_running_stream_alone(service, start):
    service.proxy.available_heaters = []
    service.proxy.set_temperature_target = lambda heater, target, tolerance: None

    start(service)
    pid_active = service._pid_active
    service.proxy.sent.clear()

    service.on_ensure_stream_request(_Msg('{"heater": "tec1"}'))

    assert service.proxy.sent == []
    assert service._stream_active is True
    assert service._pid_active is pid_active


def test_ensure_stream_after_stop_starts_again(service):
    service.on_start_stream_request(_Msg('{"pid": false}'))
    service.on_stop_stream_request(_Msg('{"all_off": true}'))
    service.proxy.sent.clear()

    service.on_ensure_stream_request(_Msg('{"heater": "tec1"}'))

    assert service.proxy.sent == ["stream_all"]
    assert service._stream_active is True


def test_ensure_stream_after_all_off_starts_again(service):
    service.on_ensure_stream_request(_Msg('{"heater": "tec1"}'))
    service.on_all_off_request(_Msg(""))
    service.proxy.sent.clear()

    service.on_ensure_stream_request(_Msg('{"heater": "tec1"}'))

    assert service.proxy.sent == ["stream_all"]


# --- STREAM_STATE: one publish per on/off change -----------------------------


def test_stream_state_published_on_each_change(service, stream_state_published):
    service.proxy.available_heaters = []
    service.proxy.set_temperature_target = lambda heater, target, tolerance: None

    def states():
        published = [
            (topic, json.loads(message)["active"])
            for topic, message in stream_state_published
        ]
        stream_state_published.clear()

        return published

    service.on_ensure_stream_request(_Msg("{}"))
    service.on_ensure_stream_request(_Msg("{}"))  # already on: no change
    assert states() == [(STREAM_STATE, True)]

    service.on_stop_stream_request(_Msg('{"all_off": true}'))
    assert states() == [(STREAM_STATE, False)]

    service.on_start_stream_request(_Msg('{"pid": true, "temperature": 40}'))
    service.on_start_stream_request(_Msg('{"pid": false}'))  # restart: still on
    assert states() == [(STREAM_STATE, True)]

    service.on_all_off_request(_Msg(""))
    assert states() == [(STREAM_STATE, False)]

    service.on_protocol_set_temperature_request(
        _Msg('{"temperature": 60, "tolerance": 2}')
    )
    assert states() == [(STREAM_STATE, True)]

    service.on_set_stream_request(_Msg('{"group": "stop"}'))
    assert states() == [(STREAM_STATE, False)]

    service.on_set_stream_request(_Msg('{"group": "thermistors"}'))
    assert states() == [(STREAM_STATE, True)]
