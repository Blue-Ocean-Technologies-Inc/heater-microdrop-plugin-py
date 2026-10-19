# (C) Copyright 2024-2026 Blue Ocean Technologies, Inc., Toronto, ON
# All rights reserved.
#
# This software is provided without warranty under the terms of the AGPL-3.0
# license included in LICENSE and may be redistributed only under the
# conditions described in the aforementioned license. The license is also
# available online at https://www.gnu.org/licenses/agpl-3.0.txt
#
# Thanks for using Microdrop open source!

"""Setpoint compensation: evaluating actual = f(expected), and the policy
that keeps an unusable expression or result away from the board."""

# Third-party imports.
import pytest

# Enthought library imports.
from apptools.preferences import package_globals
from apptools.preferences.api import Preferences

# Microdrop package imports.
from heater_controller import compensation
from heater_controller.compensation import (
    HeaterCompensationPreferences,
    compensate_setpoint,
    compensate_setpoint_from_preferences,
)

# Microdrop utils imports.
from microdrop_utils.expression import FitExpressionError

QUADRATIC = "1.04*x^2/100 + 0.9*x + 1.2"


@pytest.fixture
def node(monkeypatch):
    """A fresh default preferences node, Advanced Mode on, no logged texts."""
    preferences = Preferences()
    monkeypatch.setattr(package_globals, "_default_preferences", preferences)
    monkeypatch.setattr(compensation, "is_advanced_mode", lambda: True)
    monkeypatch.setattr(compensation, "_reported_expressions", set())
    return preferences


def _store(expression, use=True):
    HeaterCompensationPreferences(
        heater_use_compensation=use, heater_compensation_expression=expression
    )


def test_compensate_setpoint_evaluates_the_expression():
    assert compensate_setpoint(50.0, QUADRATIC) == 72.2


def test_identity_returns_the_base_untouched():
    assert compensate_setpoint(40, "x") == 40
    assert compensate_setpoint(40, "") == 40


def test_an_integer_base_gives_a_rounded_float():
    assert compensate_setpoint(40, "x + 0.123") == 40.12


def test_compensate_setpoint_raises_on_unparsable_text():
    with pytest.raises(FitExpressionError):
        compensate_setpoint(50.0, "2*a*x")


def test_no_op_unless_checked_and_advanced(node, monkeypatch):
    _store(QUADRATIC, use=False)
    assert compensate_setpoint_from_preferences(50.0) == 50.0
    _store(QUADRATIC, use=True)
    monkeypatch.setattr(compensation, "is_advanced_mode", lambda: False)
    assert compensate_setpoint_from_preferences(50.0) == 50.0


def test_a_quadratic_preference_compensates(node):
    _store(QUADRATIC)
    assert compensate_setpoint_from_preferences(50.0) == 72.2


@pytest.mark.parametrize("text", ["2*a*x", "expected = 0.96*actual - 1.1"])
def test_an_unparsable_preference_sends_the_base_and_logs_once(node, caplog, text):
    _store(text)
    assert compensate_setpoint_from_preferences(50.0) == 50.0
    assert compensate_setpoint_from_preferences(50.0) == 50.0
    errors = [record for record in caplog.records if record.levelname == "ERROR"]
    assert len(errors) == 1 and text in errors[0].getMessage()


def test_the_flipped_trend_error_names_the_direction(node, caplog):
    _store("expected = 0.96*actual - 1.1")
    compensate_setpoint_from_preferences(50.0)
    assert "actual = f(expected)" in caplog.text


def test_a_non_finite_result_sends_the_base_with_an_error(node, caplog):
    _store("log(x - 100)")
    assert compensate_setpoint_from_preferences(50.0) == 50.0
    assert any(record.levelname == "ERROR" for record in caplog.records)


@pytest.mark.parametrize(
    "text, clamped, compensated", [("x + 200", 150, "250"), ("x - 100", 0, "-50")]
)
def test_an_out_of_range_result_is_clamped_with_a_warning(
    node, caplog, text, clamped, compensated
):
    _store(text)
    assert compensate_setpoint_from_preferences(50.0) == clamped
    warning = next(r for r in caplog.records if r.levelname == "WARNING")
    assert compensated in warning.getMessage()
    assert str(clamped) in warning.getMessage()
