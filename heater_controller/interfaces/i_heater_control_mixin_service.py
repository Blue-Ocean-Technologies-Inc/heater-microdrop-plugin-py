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
from traits.api import Instance

# Microdrop package imports.
from peripheral_device_controller_base.interfaces.i_peripheral_device_control_mixin_service import (  # noqa: E501 -- dotted module path can't be shortened
    IPeripheralDeviceControlMixinService,
)

# Local imports.
from ..heater_serial_proxy import HeaterSerialProxy


class IHeaterControlMixinService(IPeripheralDeviceControlMixinService):
    """Interface for the heater control mixins. Narrows ``proxy`` to the heater
    serial proxy. This subclass is the heater's OWN service protocol so the plugin
    only composes heater mixins.
    """

    proxy = Instance(HeaterSerialProxy)
