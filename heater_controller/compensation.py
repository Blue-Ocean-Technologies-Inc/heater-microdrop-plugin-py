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
compensation controls, generalised from its linear map).

The operator calibrates the map between the sensor the PID regulates on and
the temperature that actually matters (e.g. inside the droplet) as one typed
expression, ``actual = f(expected)`` — the text the ROI plot's Actual vs
expected trend prints, so a fitted trend can be pasted straight in. ``x`` (or
``expected``) is the base setpoint and the result, rounded to 2 decimals, is
the setpoint sent. Every frontend send-site (controls pane + protocol tree
temperature column) pushes its base setpoint through
:func:`compensate_setpoint_from_preferences` before publishing — mirroring
where the legacy UI applied it — so the backend and telemetry stay in raw
board units.

That helper is also the one place an unusable expression or result is kept
away from the board: text that does not parse and a non-finite result send
the base setpoint, and a result outside the setpoint range is clamped to it.

Advanced-mode only: the preferences live on the shared peripheral-settings
node behind a "use compensation" checkbox that the heater UI force-clears when
Advanced Mode turns off, and the from-preferences helper also gates on the
live advanced-mode flag so a stale checkbox can never compensate a
normal-mode run.
"""

# Standard library imports.
import math

# Enthought library imports.
from apptools.preferences.api import PreferencesHelper
from traits.api import Bool, Str

# Microdrop package imports.
from microdrop_application.menus import is_advanced_mode

# Microdrop utils imports.
from microdrop_utils.expression import FitExpressionError, is_identity, parse_function

# Local imports.
from .consts import TEMPERATURE_MAX, TEMPERATURE_MIN

# Logger import.
from logger.logger_service import get_logger

logger = get_logger(__name__)

#: Expression texts already logged as unparsable. The helper runs on every
#: send, so each distinct text is reported once rather than on every step.
_reported_expressions = set()


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
        desc="Apply the compensation to heater setpoints "
        "(Advanced Mode only; auto-cleared when it turns off)",
    )
    heater_compensation_expression = Str(
        "x",
        desc="setpoint sent = f(base), written as actual = f(expected) — the "
        "Actual vs expected trend",
    )


def compensate_setpoint(base_setpoint, expression):
    """Evaluate the compensation ``expression`` at ``base_setpoint``.

    Returns ``base_setpoint`` untouched for the identity, else the result
    rounded to 2 decimals as a float, which may be non-finite. Raises
    FitExpressionError when ``expression`` does not parse.
    """
    if is_identity(expression):
        return base_setpoint

    function = parse_function(expression)

    return round(float(function(float(base_setpoint))), 2)


def compensate_setpoint_from_preferences(base_setpoint):
    """Compensate ``base_setpoint`` with the stored expression, never raising.

    A no-op unless Advanced Mode is on AND the use-compensation preference is
    checked. Text that does not parse (logged once per distinct text) and a
    non-finite result send ``base_setpoint`` unchanged; a result outside
    [TEMPERATURE_MIN, TEMPERATURE_MAX] is clamped to it with a warning.
    """
    preferences = HeaterCompensationPreferences()

    if not (preferences.heater_use_compensation and is_advanced_mode()):
        return base_setpoint

    expression = preferences.heater_compensation_expression

    try:
        compensated = compensate_setpoint(base_setpoint, expression)
    except FitExpressionError as error:
        if expression not in _reported_expressions:
            _reported_expressions.add(expression)
            logger.error(
                f'Heater compensation "{expression}" cannot be used ({error}); '
                f"sending setpoints uncompensated"
            )

        return base_setpoint

    if not math.isfinite(compensated):
        logger.error(
            f'Heater compensation "{expression}" gives {compensated} at '
            f"{base_setpoint} °C; sending the base setpoint {base_setpoint} °C"
        )

        return base_setpoint

    clamped = float(min(max(compensated, TEMPERATURE_MIN), TEMPERATURE_MAX))

    if clamped == compensated:
        return compensated

    logger.warning(
        f'Heater compensation "{expression}" gives {compensated} °C at '
        f"{base_setpoint} °C, outside [{TEMPERATURE_MIN}, {TEMPERATURE_MAX}] °C; "
        f"sending {clamped} °C"
    )

    return clamped
