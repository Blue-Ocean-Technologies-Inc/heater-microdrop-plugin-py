from traits.api import Instance, provides

from peripheral_device_controller_base.services.peripheral_firmware_upload_service import (  # noqa: E501 -- dotted module path can't be shortened
    PeripheralFirmwareUploadService,
)

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
