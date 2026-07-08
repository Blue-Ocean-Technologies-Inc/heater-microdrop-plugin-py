from traits.api import provides, Str, List

from microdrop_utils.hardware_device_monitoring_helpers import find_port_by_device_id

from peripheral_device_controller_base.services.peripheral_device_monitor_mixin_service import (
    PeripheralDeviceMonitorMixinService,
)
from logger.logger_service import get_logger

from ..interfaces.i_heater_control_mixin_service import IHeaterControlMixinService
from ..heater_serial_proxy import HeaterSerialProxy
from ..consts import HEATER_HWID, DEVICE_NAME, DEVICE_ID_FRAGMENT

logger = get_logger(__name__)


@provides(IHeaterControlMixinService)
class HeaterMonitorMixinService(PeripheralDeviceMonitorMixinService):
    """Monitors for the heater controller (RP2040) connection."""
    id = Str(f"{DEVICE_NAME}_monitor_mixin_service")
    name = Str(f'{DEVICE_NAME.title()} Monitor Mixin')

    _default_hwids = List(Str, [HEATER_HWID])

    def _make_proxy(self, port_name):
        return HeaterSerialProxy(port=port_name)

    def _find_port(self, hwids):
        """Locate the heater by VID:PID AND whoami identity: the fluorescence
        LED board shares the Pico 2E8A:0005 id, so each candidate port is
        probed for a device_id containing "heater" before it is claimed."""
        return find_port_by_device_id(hwids, DEVICE_ID_FRAGMENT)
