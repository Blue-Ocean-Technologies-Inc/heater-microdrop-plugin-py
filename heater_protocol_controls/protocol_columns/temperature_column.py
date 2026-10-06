# (C) Copyright 2024-2026 Blue Ocean Technologies, Inc., Toronto, ON
# All rights reserved.
#
# This software is provided without warranty under the terms of the AGPL-3.0
# license included in LICENSE and may be redistributed only under the
# conditions described in the aforementioned license. The license is also
# available online at https://www.gnu.org/licenses/agpl-3.0.txt
#
# Thanks for using Microdrop open source!

"""Heater temperature compound column — drives a heater to a target temperature
for a protocol step and blocks the step until the PID temperature is within a
tolerance band of the target.

Three coupled cells share one model + one handler (the PPT-11 compound
framework):
  * set_temperature      (Bool)  — drive the heater on this step, or leave
    it untouched (unchecked = no setpoint publish, no reached-ack wait)
  * target_temperature_c (Float) — the PID setpoint to drive toward
  * tolerance_c          (Float) — the +/- band that counts as "reached"

For a checked step the handler publishes PROTOCOL_SET_TEMPERATURE; the heater
backend sets the target, watches the PID telemetry, and acks on
TEMPERATURE_REACHED once within tolerance — which the step's ``ctx.wait_for``
is blocking on. If that wait times out, the step's TELEMETRY mailbox supplies
the last PID temperature so the failure says how far off the heater was.
"""

# Standard library imports.
import json

# Enthought library imports.
from pyface.qt.QtCore import Qt
from traits.api import Bool, Float, List, Str

# Microdrop package imports.
from heater_controller.compensation import compensate_setpoint_from_preferences
from heater_controller.consts import (
    DEFAULT_HEATER,
    PROTOCOL_SET_TEMPERATURE,
    STOP_STREAM,
    TELEMETRY,
    TEMPERATURE_REACHED,
)
from pluggable_protocol_tree.interfaces.i_compound_column import FieldSpec
from pluggable_protocol_tree.models.compound_column import (
    BaseCompoundColumnHandler,
    BaseCompoundColumnModel,
    CompoundColumn,
    DictCompoundColumnView,
)
from pluggable_protocol_tree.views.columns.checkbox import CheckboxColumnView
from pluggable_protocol_tree.views.columns.spinbox import DoubleSpinBoxColumnView

# Microdrop utils imports.
from microdrop_utils.dramatiq_pub_sub_helpers import publish_message

# Local imports.
from ..consts import SET_TEMPERATURE_FIELD_ID

# Sensible defaults / spinbox ranges (mirror the heater UI's setpoint range).
TARGET_DEFAULT = 40.0
TOLERANCE_DEFAULT = 1.0
TARGET_MIN, TARGET_MAX = 0.0, 150.0
TOLERANCE_MIN, TOLERANCE_MAX = 0.0, 20.0


class TemperatureCompoundModel(BaseCompoundColumnModel):
    """Three coupled fields; base_id 'heater_temperature' appears as the
    compound id on each field's JSON column entry."""

    base_id = "heater_temperature"

    def field_specs(self):
        return [
            FieldSpec(SET_TEMPERATURE_FIELD_ID, "Set Temp", False),
            FieldSpec("target_temperature_c", "Target Temp (°C)", TARGET_DEFAULT),
            FieldSpec("tolerance_c", "Tolerance (°C)", TOLERANCE_DEFAULT),
        ]

    def trait_for_field(self, field_id):
        if field_id == SET_TEMPERATURE_FIELD_ID:
            return Bool(False)
        if field_id == "target_temperature_c":
            return Float(TARGET_DEFAULT)
        if field_id == "tolerance_c":
            return Float(TOLERANCE_DEFAULT)
        raise KeyError(field_id)


class TemperatureSetpointSpinBoxView(DoubleSpinBoxColumnView):
    """Setpoint cell that is read-only while the step's Set Temp checkbox
    is off (cross-cell editability via the canonical PPT-11 get_flags(row)
    pattern, mirroring the magnet column's height cell)."""

    #: get_flags is a pure function of the step's Set Temp flag; declare it so
    #: the tree repaints this cell the moment the checkbox toggles instead of
    #: waiting for an incidental repaint.
    depends_on_row_traits = List(Str, value=[SET_TEMPERATURE_FIELD_ID])

    def get_flags(self, row):
        flags = super().get_flags(row)
        if not getattr(row, SET_TEMPERATURE_FIELD_ID, False):
            flags &= ~Qt.ItemIsEditable
        return flags


def last_pid_temperature(ctx, heater):
    """Drain the step's TELEMETRY mailbox and return the last PID temperature
    reported for ``heater``, or None when none arrived during the step.

    Reads the same ``pid_temperature`` of the ``PID_<HEATER>`` frames the
    backend's reached-watch compares against the target.
    """
    temperature = None

    while True:
        try:
            payload = ctx.wait_for(TELEMETRY, timeout=0.0)
        except TimeoutError:
            return temperature

        try:
            packet = json.loads(payload)
        except (TypeError, ValueError):
            # A malformed frame says nothing about the heater; keep scanning.
            continue

        if not isinstance(packet, dict):
            continue

        frame = packet.get("_frame", "")
        reading = packet.get("pid_temperature")

        if frame.lower() == f"pid_{heater.lower()}" and isinstance(
            reading, (int, float)
        ):
            temperature = reading


def temperature_not_reached_message(
    heater, target, tolerance, timeout_s, last_temperature
):
    """Explain a reached-ack timeout: the last measured temperature against
    the armed band, or that no reading arrived at all."""
    summary = (
        f"Heater {heater} did not reach {target:g} ± {tolerance:g} °C "
        f"within {timeout_s:g} s"
    )

    if last_temperature is None:
        return (
            f"{summary} — no temperature reading for {heater} arrived during "
            f"the wait. The heater board may be disconnected or not streaming "
            f"telemetry."
        )

    return (
        f"{summary} — last measured {last_temperature:g} °C "
        f"(needs {target - tolerance:g}–{target + tolerance:g} °C)."
    )


class TemperatureHandler(BaseCompoundColumnHandler):
    """Publishes the step's target + tolerance and waits for the reached ack.

    Priority 20 — same bucket as voltage/frequency/magnet, before routes (30).
    The ack wait comes from the Protocol Settings grid; set it to 0 there to run
    fire-and-forget (set the target without blocking).
    """

    priority = 20
    # TELEMETRY is only read after a reached-ack timeout, to report the last
    # measured temperature instead of a generic "no reply".
    wait_for_topics = [TEMPERATURE_REACHED, TELEMETRY]
    # Heating/cooling to a setpoint is slow, so default the ack-wait higher than
    # voltage/frequency (5 s) or magnet (10 s).
    default_ack_time_s = 120.0

    def on_step(self, row, ctx):
        if getattr(ctx.protocol, "preview_mode", False):
            return

        # Unchecked = the step leaves the heater untouched: no setpoint
        # publish, no reached-ack wait (issue #9).
        if not getattr(row, SET_TEMPERATURE_FIELD_ID, False):
            return

        # Compensation (advanced-mode preference) maps the step's base target
        # the same way the controls pane maps its setpoint; the tolerance band
        # stays in raw degrees.
        target = compensate_setpoint_from_preferences(float(row.target_temperature_c))
        tolerance = float(row.tolerance_c)

        publish_message(
            topic=PROTOCOL_SET_TEMPERATURE,
            message=json.dumps(
                {
                    "heater": DEFAULT_HEATER,
                    "temperature": target,
                    "tolerance": tolerance,
                }
            ),
        )

        if self.ack_time_s <= 0:
            return

        try:
            ctx.wait_for(TEMPERATURE_REACHED, timeout=self.ack_time_s)
        except TimeoutError as error:
            message = temperature_not_reached_message(
                DEFAULT_HEATER,
                target,
                tolerance,
                self.ack_time_s,
                last_pid_temperature(ctx, DEFAULT_HEATER),
            )

            raise TimeoutError(message) from error

    def on_post_protocol_end(self, ctx):
        """Stop the PID + telemetry stream the protocol steps started —
        unconditional at the end of every run (normal or aborted), with
        all_off so nothing keeps heating unattended (the heater UI's
        stream-off safety semantics). The backend also closes the
        telemetry log on this."""
        if getattr(ctx, "preview_mode", False):
            return
        publish_message(topic=STOP_STREAM, message=json.dumps({"all_off": True}))


def make_temperature_column():
    """Factory — a fresh heater-temperature CompoundColumn."""
    return CompoundColumn(
        model=TemperatureCompoundModel(),
        view=DictCompoundColumnView(
            cell_views={
                SET_TEMPERATURE_FIELD_ID: CheckboxColumnView(),
                "target_temperature_c": TemperatureSetpointSpinBoxView(
                    low=TARGET_MIN, high=TARGET_MAX, decimals=1, single_step=1.0
                ),
                "tolerance_c": TemperatureSetpointSpinBoxView(
                    low=TOLERANCE_MIN, high=TOLERANCE_MAX, decimals=1, single_step=0.5
                ),
            }
        ),
        handler=TemperatureHandler(),
    )
