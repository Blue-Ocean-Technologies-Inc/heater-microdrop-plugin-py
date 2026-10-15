# (C) Copyright 2024-2026 Blue Ocean Technologies, Inc., Toronto, ON
# All rights reserved.
#
# This software is provided without warranty under the terms of the AGPL-3.0
# license included in LICENSE and may be redistributed only under the
# conditions described in the aforementioned license. The license is also
# available online at https://www.gnu.org/licenses/agpl-3.0.txt
#
# Thanks for using Microdrop open source!

"""Package-level constants for heater_protocol_controls.

Topic constants live in heater_controller/consts.py — this plugin imports them
(same layering as peripheral_protocol_controls). So do the temperature
compound column's field ids, re-exported here: SET_TEMPERATURE_FIELD_ID is the
Set Temp checkbox (row trait) — drive the heater on this step, or leave it
untouched (no setpoint publish, no reached-ack wait) — referenced by the
handler gate and the cross-cell editability views; TARGET_TEMPERATURE_FIELD_ID
is the setpoint the heater pane follows on step selection.
"""

# Microdrop package imports.
from heater_controller.consts import (  # noqa: F401 (re-export)
    SET_TEMPERATURE_FIELD_ID,
    TARGET_TEMPERATURE_FIELD_ID,
)

PKG = ".".join(__name__.split(".")[:-1])
PKG_name = PKG.title().replace("_", " ")
