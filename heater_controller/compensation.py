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
from .consts import (
    LEGACY_COMPENSATION_OFFSET_KEY,
    LEGACY_COMPENSATION_RATE_KEY,
    TEMPERATURE_MAX,
    TEMPERATURE_MIN,
)

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

    def __init__(self, **traits):
        super().__init__(**traits)

        self._migrate_linear_compensation()

    def _migrate_linear_compensation(self):
        """Seed the expression once from the legacy rate/offset preferences.

        Never raises: the helper is constructed on every setpoint send. The
        seeded assignment writes the expression key, so this runs only until
        the first non-identity migration. The legacy keys stay in the node.
        """
        if self.preferences is None:
            return

        path = self.preferences_path
        keys = self.preferences.keys(path)

        if "heater_compensation_expression" in keys:
            return

        legacy_defaults = {
            LEGACY_COMPENSATION_RATE_KEY: 1.0,
            LEGACY_COMPENSATION_OFFSET_KEY: 0.0,
        }

        if not legacy_defaults.keys() & set(keys):
            return

        values = {}

        for key, default in legacy_defaults.items():
            value = self.preferences.get(f"{path}.{key}", default)

            try:
                values[key] = float(value)
            except (TypeError, ValueError):
                logger.warning(
                    f"Ignoring unreadable heater compensation preference {key} = "
                    f'"{value}"; leaving the compensation expression as "x"'
                )

                return

        rate = values[LEGACY_COMPENSATION_RATE_KEY]
        offset = values[LEGACY_COMPENSATION_OFFSET_KEY]

        if (rate, offset) == (1.0, 0.0):
            return

        expression = f"{rate}*x + {offset}"
        self.heater_compensation_expression = expression

        logger.info(
            f"Migrated heater compensation rate {rate} / offset {offset} to "
            f"{expression}"
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
