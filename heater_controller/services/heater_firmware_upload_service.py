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
from traits.api import Instance, provides

# Microdrop package imports.
from peripheral_device_controller_base.services.peripheral_firmware_upload_service import (  # noqa: E501 -- dotted module path can't be shortened
    PeripheralFirmwareUploadService,
)

# Local imports.
from ..heater_serial_proxy import HeaterSerialProxy
from ..interfaces.i_heater_control_mixin_service import IHeaterControlMixinService


@provides(IHeaterControlMixinService)
class HeaterFirmwareUploadService(PeripheralFirmwareUploadService):
    """Heater firmware-upload mixin.

    All the logic lives in PeripheralFirmwareUploadService (topics derived
    from the composed controller's ``_device_name``, port finding via its
    ``_default_hwids``); this subclass only provides the heater control-mixin
    interface and narrows the proxy type so the plugin composes exactly the
    heater mixins.
    """

    proxy = Instance(HeaterSerialProxy)
