from traits.api import provides, Str, List

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

    # The fluorescence LED board shares the Pico 2E8A:0005 id, so the base
    # monitor probes each candidate port's whoami device_id for this fragment
    # before claiming it.
    _device_id_fragment = Str(DEVICE_ID_FRAGMENT)

    def _make_proxy(self, port_name):
        # port_name is the base monitor's ClaimedPort: the proxy adopts its
        # probe-time serial handle instead of reopening the port.
        return HeaterSerialProxy(
            port=str(port_name),
            expected_device_id_fragment=DEVICE_ID_FRAGMENT,
            serial_instance=getattr(port_name, "serial", None))
