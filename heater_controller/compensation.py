# (C) Copyright 2024-2026 Blue Ocean Technologies, Inc., Toronto, ON
# All rights reserved.
#
# This software is provided without warranty under the terms of the AGPL-3.0
# license included in LICENSE and may be redistributed only under the
# conditions described in the aforementioned license. The license is also
# available online at https://www.gnu.org/licenses/agpl-3.0.txt
#
# Thanks for using Microdrop open source!

"""Temperature-setpoint compensation (port of the legacy standalone UI's
compensation controls).

The operator calibrates a linear map between the sensor the PID regulates on
and the temperature that actually matters (e.g. inside the droplet):
``compensated = round(base * rate + offset, 2)``. Every frontend send-site
(controls pane + protocol tree temperature column) pushes its base setpoint
through :func:`compensate_setpoint_from_preferences` before publishing —
mirroring where the legacy UI applied it — so the backend and telemetry stay
in raw board units.

Advanced-mode only: the preferences live on the shared peripheral-settings
node behind a "use compensation" checkbox that the heater UI force-clears when
Advanced Mode turns off, and the from-preferences helper also gates on the
live advanced-mode flag so a stale checkbox can never compensate a
normal-mode run.
"""

# Enthought library imports.
from apptools.preferences.api import PreferencesHelper
from traits.api import Bool, Range

# Microdrop package imports.
from microdrop_application.menus import is_advanced_mode

# Local imports.
from .consts import (
    COMPENSATION_OFFSET_MAX,
    COMPENSATION_OFFSET_MIN,
    COMPENSATION_RATE_MAX,
    COMPENSATION_RATE_MIN,
    DEFAULT_COMPENSATION_OFFSET,
    DEFAULT_COMPENSATION_RATE,
)


class HeaterCompensationPreferences(PreferencesHelper):
    """Compensation slice of the shared Peripheral Settings node.

    Defined here (not in the controls UI) so the protocol tree plugin can
    read the same values without importing another plugin's preferences
    class — the controls UI's ``HeaterPreferences`` subclasses this to render
    the traits on its Heater Settings tab.
    """

    preferences_path = "microdrop.peripheral_settings"

    heater_use_compensation = Bool(
        False,
        desc="Apply the linear compensation to heater setpoints "
        "(Advanced Mode only; auto-cleared when it turns off)",
    )
    heater_compensation_rate = Range(
        value=DEFAULT_COMPENSATION_RATE,
        low=COMPENSATION_RATE_MIN,
        high=COMPENSATION_RATE_MAX,
        desc="Multiplier applied to the base setpoint",
    )
    heater_compensation_offset = Range(
        value=DEFAULT_COMPENSATION_OFFSET,
        low=COMPENSATION_OFFSET_MIN,
        high=COMPENSATION_OFFSET_MAX,
        desc="Offset (°C) added after the rate multiply",
    )


def compensate_setpoint(base_setpoint, compensation_rate, compensation_offset):
    """The legacy standalone UI's compensation map for a PID setpoint."""
    return round((base_setpoint * compensation_rate) + compensation_offset, 2)


def compensate_setpoint_from_preferences(base_setpoint):
    """Compensate ``base_setpoint`` with the stored rate/offset — a no-op
    unless Advanced Mode is on AND the use-compensation preference is
    checked."""
    preferences = HeaterCompensationPreferences()
    if not (preferences.heater_use_compensation and is_advanced_mode()):
        return base_setpoint
    return compensate_setpoint(
        base_setpoint,
        preferences.heater_compensation_rate,
        preferences.heater_compensation_offset,
    )
