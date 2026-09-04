# (C) Copyright 2024-2026 Blue Ocean Technologies, Inc., Toronto, ON
# All rights reserved.
#
# This software is provided without warranty under the terms of the AGPL-3.0
# license included in LICENSE and may be redistributed only under the
# conditions described in the aforementioned license. The license is also
# available online at https://www.gnu.org/licenses/agpl-3.0.txt
#
# Thanks for using Microdrop open source!

# Enthought library imports.
from pyface.action.api import Action
from pyface.action.schema.schema import SMenu
from pyface.tasks.action.api import DockPaneAction
from traits.api import Instance, Str

# Microdrop utils imports.
from microdrop_utils.dramatiq_traits_helpers import DramatiqMessagePublishAction
from microdrop_utils.firmware_upload_dialog.controller import (
    FirmwareUploadDialogController,
)

# Local imports.
from .consts import PKG, START_DEVICE_MONITORING
from .firmware_upload.controller import make_firmware_upload_controller


class UploadFirmwareAction(Action):
    name = Str("Upload &Firmware...")
    tooltip = "Flash the heater board's MicroPython firmware"

    #: One controller for the action's lifetime: reopening raises the live
    #: dialog instead of duplicating it, and the log/options survive reopens.
    controller = Instance(FirmwareUploadDialogController)

    def perform(self, event):
        if self.controller is None:
            self.controller = make_firmware_upload_controller()
        self.controller.open()


def heater_tools_menu_factory():
    """Tools ▸ Heater ▸ {Search Connection, Configure Sensors & Heaters,
    Upload Firmware}."""
    search = DramatiqMessagePublishAction(
        name="&Search Connection", topic=START_DEVICE_MONITORING
    )
    # Opens the modal configurator on the heater dock pane (DockPaneAction
    # resolves the pane by id and calls the method).
    configure = DockPaneAction(
        id="heater_configure_sensors",
        dock_pane_id=PKG + ".dock_pane",
        name="&Configure Sensors && Heaters",
        method="open_sensor_config",
    )
    return SMenu(
        items=[search, configure, UploadFirmwareAction()],
        id="heater_tools",
        name="&Heater",
    )


def tools_menu_factory():
    # The heater contributes its own Tools -> Peripherals -> Heater
    return SMenu(
        items=[heater_tools_menu_factory()], id="peripherals_tools", name="&Peripherals"
    )
