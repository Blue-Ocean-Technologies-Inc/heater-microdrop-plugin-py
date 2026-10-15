# (C) Copyright 2024-2026 Blue Ocean Technologies, Inc., Toronto, ON
# All rights reserved.
#
# This software is provided without warranty under the terms of the AGPL-3.0
# license included in LICENSE and may be redistributed only under the
# conditions described in the aforementioned license. The license is also
# available online at https://www.gnu.org/licenses/agpl-3.0.txt
#
# Thanks for using Microdrop open source!

"""The heater pane follows the selected protocol step's target temperature
(PROTOCOL_TREE_ROW_SELECTED) when the step's Set Temp box is checked, except
while a protocol runs and for echoes of its own follow; a follow never pops
the stream-off edit warning a user edit gets."""

# Standard library imports.
import json

# Third-party imports.
import pytest

# Enthought library imports.
from traits.api import Int, observe

# Microdrop package imports.
import heater_controls_ui.controller as controller_mod
from heater_controller.consts import (
    SET_TEMPERATURE_FIELD_ID,
    TARGET_TEMPERATURE_FIELD_ID,
)
from heater_controls_ui.controller import HeaterControlsController
from heater_controls_ui.message_handler import HeaterMessageHandler
from heater_controls_ui.model import HeaterStatusModel
from pluggable_protocol_tree.models.cell_sync import ProtocolTreeRowSelectedMessage

#: Parked pane setpoint — well away from every step target used below.
PANE_TEMPERATURE = 20


class WarningCountingHeaterModel(HeaterStatusModel):
    """The heater model, counting the stream-off edit warnings it fires."""

    #: How many times ``stream_off_edit_warning`` fired.
    warnings_fired = Int(0)

    @observe("stream_off_edit_warning", post_init=True)
    def _count_warning(self, event):
        self.warnings_fired += 1


@pytest.fixture
def handler(request):
    """A handler on a real model with its temperature parked at
    PANE_TEMPERATURE."""
    model = WarningCountingHeaterModel(temperature=PANE_TEMPERATURE)
    message_handler = HeaterMessageHandler(
        model=model, name=f"test_{request.node.name}"
    )

    yield message_handler

    message_handler.teardown()


@pytest.fixture
def published(monkeypatch):
    sink = []
    monkeypatch.setattr(
        controller_mod,
        "publish_message",
        lambda message, topic=None, **kwargs: sink.append((topic, json.loads(message))),
    )

    return sink


@pytest.fixture
def controller(handler):
    """The pane's controller on the handler's model, built without a UI."""

    return HeaterControlsController(model=handler.model)


def _row_selected(step_id="step-1", set_temperature=True, target=42.6):
    cells = {
        SET_TEMPERATURE_FIELD_ID: set_temperature,
        TARGET_TEMPERATURE_FIELD_ID: target,
        "tolerance_c": 1.0,
    }

    return ProtocolTreeRowSelectedMessage(step_id=step_id, cells=cells).serialize()


def test_checked_step_sets_the_rounded_temperature(handler):
    handler._on_row_selected_triggered(_row_selected(target=42.6))

    assert handler.model.temperature == 43


def test_unchecked_step_leaves_the_temperature(handler):
    handler._on_row_selected_triggered(_row_selected(set_temperature=False))

    assert handler.model.temperature == PANE_TEMPERATURE


def test_running_protocol_leaves_the_temperature(handler):
    handler.model.protocol_running = True

    handler._on_row_selected_triggered(_row_selected())

    assert handler.model.temperature == PANE_TEMPERATURE


def test_pane_override_survives_an_echo_with_another_cell_changed(handler):
    handler._on_row_selected_triggered(_row_selected("A", target=50.0))
    assert handler.model.temperature == 50

    handler.model.temperature = 55  # the user overrides it in the pane
    echo = ProtocolTreeRowSelectedMessage(
        step_id="A",
        cells={
            SET_TEMPERATURE_FIELD_ID: True,
            TARGET_TEMPERATURE_FIELD_ID: 50.0,
            "tolerance_c": 2.5,
        },
    ).serialize()
    handler._on_row_selected_triggered(echo)

    assert handler.model.temperature == 55


def test_reselecting_after_an_unchecked_step_follows_again(handler):
    step_a = _row_selected("A", target=50.0)

    handler._on_row_selected_triggered(step_a)
    handler.model.temperature = 55
    handler._on_row_selected_triggered(_row_selected("B", set_temperature=False))
    assert handler.model.temperature == 55

    handler._on_row_selected_triggered(step_a)
    assert handler.model.temperature == 50


def test_follow_with_stream_off_stages_without_the_warning(
    handler, controller, published
):
    handler._on_row_selected_triggered(_row_selected(target=42.6))

    assert handler.model.temperature == 43
    assert handler.model.warnings_fired == 0
    assert published == []

    handler.model.temperature = 45  # a user edit

    assert handler.model.warnings_fired == 1
    assert published == []
