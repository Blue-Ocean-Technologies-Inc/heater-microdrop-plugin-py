"""Hardware-free tests for the heater temperature protocol column."""
import json

import heater_protocol_controls.protocol_columns.temperature_column as tc_mod
from heater_protocol_controls.consts import SET_TEMPERATURE_FIELD_ID
from heater_protocol_controls.protocol_columns.temperature_column import (
    make_temperature_column, TemperatureCompoundModel, TemperatureHandler,
    TemperatureSetpointSpinBoxView,
)
from heater_protocol_controls.plugin import HeaterProtocolControlsPlugin
from heater_controller.consts import PROTOCOL_SET_TEMPERATURE, TEMPERATURE_REACHED


class _Row:
    set_temperature = True
    target_temperature_c = 55.0
    tolerance_c = 1.5


class _Ctx:
    def __init__(self, preview=False):
        self.protocol = type("P", (), {"preview_mode": preview})()
        self.waited = None

    def wait_for(self, topic, timeout=None):
        self.waited = (topic, timeout)


def test_model_has_three_fields():
    specs = TemperatureCompoundModel().field_specs()
    assert [s.field_id for s in specs] == [
        SET_TEMPERATURE_FIELD_ID, "target_temperature_c", "tolerance_c"]
    assert specs[0].default_value is False


def test_factory_and_plugin_contribution():
    col = make_temperature_column()
    assert col.handler.wait_for_topics == [TEMPERATURE_REACHED]
    assert col.handler.priority == 20
    cols = HeaterProtocolControlsPlugin()._contributed_protocol_columns_default()
    assert len(cols) == 1


def test_on_step_publishes_and_waits(monkeypatch):
    pub = []
    monkeypatch.setattr(tc_mod, "publish_message",
                        lambda topic, message: pub.append((topic, message)))
    handler = TemperatureHandler()
    handler.ack_time_s = 30.0
    ctx = _Ctx()
    handler.on_step(_Row(), ctx)

    topic, payload = pub[0]
    assert topic == PROTOCOL_SET_TEMPERATURE
    assert json.loads(payload) == {"heater": "tec1", "temperature": 55.0, "tolerance": 1.5}
    assert ctx.waited == (TEMPERATURE_REACHED, 30.0)


def test_preview_mode_skips(monkeypatch):
    pub = []
    monkeypatch.setattr(tc_mod, "publish_message",
                        lambda topic, message: pub.append((topic, message)))
    handler = TemperatureHandler()
    handler.ack_time_s = 30.0
    ctx = _Ctx(preview=True)
    handler.on_step(_Row(), ctx)
    assert pub == [] and ctx.waited is None


def test_zero_ack_publishes_without_waiting(monkeypatch):
    pub = []
    monkeypatch.setattr(tc_mod, "publish_message",
                        lambda topic, message: pub.append((topic, message)))
    handler = TemperatureHandler()
    handler.ack_time_s = 0.0
    ctx = _Ctx()
    handler.on_step(_Row(), ctx)
    assert len(pub) == 1 and ctx.waited is None


def test_unchecked_step_leaves_heater_untouched(monkeypatch):
    """Set Temp off = no setpoint publish and no reached-ack wait (#9)."""
    pub = []
    monkeypatch.setattr(tc_mod, "publish_message",
                        lambda topic, message: pub.append((topic, message)))
    handler = TemperatureHandler()
    handler.ack_time_s = 30.0

    class _UncheckedRow(_Row):
        set_temperature = False

    ctx = _Ctx()
    handler.on_step(_UncheckedRow(), ctx)
    assert pub == [] and ctx.waited is None


def test_setpoint_cells_read_only_until_checked():
    view = TemperatureSetpointSpinBoxView(low=0.0, high=150.0)

    class _UncheckedRow(_Row):
        set_temperature = False

    from pyface.qt.QtCore import Qt
    assert not (view.get_flags(_UncheckedRow()) & Qt.ItemIsEditable)
    assert view.get_flags(_Row()) & Qt.ItemIsEditable
