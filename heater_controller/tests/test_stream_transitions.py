"""Hardware-free tests for the start_stream / stop_stream run-mode transitions
(ports of the legacy standalone UI's start_stream/stop_stream).

The whole stop-current -> delay -> start-new sequence must run inside one
handler invocation, in order — that ordering is the reason these exist as
single requests rather than separate pub/sub messages. ``time.sleep`` is
monkeypatched so the tests record the delay without waiting for it.
"""
import threading

import pytest

import heater_controller.services.heater_command_setter_service as svc_mod
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
    monkeypatch.setattr(
        svc_mod.time, "sleep", lambda s: proxy.sent.append("<sleep>"))
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
    assert service.proxy.sent == [
        "pid_stop", "<sleep>", "stream_all", "pwm_tec1_25"]
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
    assert service.proxy.sent == []      # invalid payload rejected, no commands
