# (C) Copyright 2024-2026 Blue Ocean Technologies, Inc., Toronto, ON
# All rights reserved.
#
# This software is provided without warranty under the terms of the AGPL-3.0
# license included in LICENSE and may be redistributed only under the
# conditions described in the aforementioned license. The license is also
# available online at https://www.gnu.org/licenses/agpl-3.0.txt
#
# Thanks for using Microdrop open source!

"""Heater wiring for the shared firmware-upload dialog.

The dialog itself (model / view / controller) is device-agnostic and lives in
``microdrop_utils.firmware_upload_dialog``; here we just build one wired to
the heater live_state, publisher, topics, and defaults.
"""

# Microdrop package imports.
from heater_controller.consts import (
    CANCEL_FIRMWARE_UPLOAD,
    FIRMWARE_UPLOAD_FINISHED,
    FIRMWARE_UPLOAD_LOG,
    FIRMWARE_UPLOAD_STARTED,
    HEATER_BOARD_DEVICE_ID,
)
from heater_controller.datamodels import upload_firmware_publisher

# Microdrop utils imports.
from microdrop_utils.firmware_upload_dialog.controller import (
    FirmwareUploadDialogController,
)

# Local imports.
from ..live_state import heater_live_state
from ..preferences import HeaterPreferences


def make_firmware_upload_controller():
    """A firmware-upload dialog controller wired for the heater board."""
    return FirmwareUploadDialogController(
        live_state=heater_live_state,
        upload_publisher=upload_firmware_publisher,
        cancel_topic=CANCEL_FIRMWARE_UPLOAD,
        started_topic=FIRMWARE_UPLOAD_STARTED,
        log_topic=FIRMWARE_UPLOAD_LOG,
        finished_topic=FIRMWARE_UPLOAD_FINISHED,
        default_device_id=HEATER_BOARD_DEVICE_ID,
        preferences=HeaterPreferences(),
        dialog_title="Upload Heater Firmware",
    )
