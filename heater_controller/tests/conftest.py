# (C) Copyright 2024-2026 Blue Ocean Technologies, Inc., Toronto, ON
# All rights reserved.
#
# This software is provided without warranty under the terms of the AGPL-3.0
# license included in LICENSE and may be redistributed only under the
# conditions described in the aforementioned license. The license is also
# available online at https://www.gnu.org/licenses/agpl-3.0.txt
#
# Thanks for using Microdrop open source!

"""Shared fixtures for the hardware-free backend tests."""

# Third-party imports.
import pytest

# Microdrop package imports.
import heater_controller.services.heater_command_setter_service as svc_mod


@pytest.fixture(autouse=True)
def stream_state_published(monkeypatch):
    """Record the command-setter's STREAM_STATE publishes as (topic, message)
    instead of sending them to a broker — none runs in the unit tests."""
    published = []
    monkeypatch.setattr(
        svc_mod,
        "publish_message",
        lambda message, topic, **kwargs: published.append((topic, message)),
    )

    return published
