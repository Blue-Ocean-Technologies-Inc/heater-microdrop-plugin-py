# (C) Copyright 2024-2026 Blue Ocean Technologies, Inc., Toronto, ON
# All rights reserved.
#
# This software is provided without warranty under the terms of the AGPL-3.0
# license included in LICENSE and may be redistributed only under the
# conditions described in the aforementioned license. The license is also
# available online at https://www.gnu.org/licenses/agpl-3.0.txt
#
# Thanks for using Microdrop open source!

"""Live temperature / PWM plotting dock pane for the heater UI.

A self-contained pane that taps the heater telemetry stream and draws rolling
Temperature and PWM charts (matplotlib), styled with the microdrop_style brand
palette. Kept decoupled from the status pane: it runs its own telemetry
listener and owns its own Qt-free plot model.
"""
