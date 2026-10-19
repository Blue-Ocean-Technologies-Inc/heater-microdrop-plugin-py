# (C) Copyright 2024-2026 Blue Ocean Technologies, Inc., Toronto, ON
# All rights reserved.
#
# This software is provided without warranty under the terms of the AGPL-3.0
# license included in LICENSE and may be redistributed only under the
# conditions described in the aforementioned license. The license is also
# available online at https://www.gnu.org/licenses/agpl-3.0.txt
#
# Thanks for using Microdrop open source!

"""The Heater Settings compensation field's error label."""

# Enthought library imports.
from apptools.preferences.api import Preferences

# Microdrop package imports.
from heater_controls_ui.preferences import HeaterPreferences


def test_the_field_error_names_the_problem_and_is_not_persisted():
    node = Preferences()
    preferences = HeaterPreferences(
        preferences=node, heater_compensation_expression="a*x"
    )
    assert preferences.heater_compensation_expression_error_ == "unknown name 'a'"
    preferences.heater_compensation_expression = "x"
    assert preferences.heater_compensation_expression_error_ == ""
    assert "heater_compensation_expression_error_" not in node.keys(
        "microdrop.peripheral_settings"
    )
