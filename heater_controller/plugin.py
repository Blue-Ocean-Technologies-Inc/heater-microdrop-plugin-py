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
from envisage.api import ServiceOffer
from traits.api import List

# Microdrop package imports.
from message_router.consts import ACTOR_TOPIC_ROUTES
from peripheral_device_controller_base.plugin import PeripheralDeviceControllerPlugin

# Local imports.
from .consts import ACTOR_TOPIC_DICT, PKG, PKG_name
from .heater_controller_base import HeaterControllerBase
from .interfaces.i_heater_control_mixin_service import IHeaterControlMixinService

# Logger import.
from logger.logger_service import get_logger

logger = get_logger(__name__)


class HeaterControllerPlugin(PeripheralDeviceControllerPlugin):
    id = PKG + ".plugin"
    name = f"{PKG_name} Plugin"

    # This plugin contributes actors that can be called using certain routing keys.
    actor_topic_routing = List([ACTOR_TOPIC_DICT], contributes_to=ACTOR_TOPIC_ROUTES)

    # Compose only the heater's own mixins onto the heater's controller base.
    _mixin_protocol = IHeaterControlMixinService
    _controller_base_class = HeaterControllerBase

    def _service_offers_default(self):
        """Return the service offers."""
        return [
            ServiceOffer(
                protocol=IHeaterControlMixinService,
                factory=self._create_monitor_service,
            ),
            ServiceOffer(
                protocol=IHeaterControlMixinService,
                factory=self._create_command_setter_service,
            ),
            ServiceOffer(
                protocol=IHeaterControlMixinService, factory=self._create_config_service
            ),
            ServiceOffer(
                protocol=IHeaterControlMixinService,
                factory=self._create_firmware_upload_service,
            ),
        ]

    def _create_monitor_service(self, *args, **kwargs):
        """Returns the heater monitor mixin service."""
        from .services.heater_monitor_mixin_service import HeaterMonitorMixinService

        return HeaterMonitorMixinService

    def _create_command_setter_service(self, *args, **kwargs):
        """Returns the heater command-setter mixin service."""
        from .services.heater_command_setter_service import HeaterCommandSetterService

        return HeaterCommandSetterService

    def _create_config_service(self, *args, **kwargs):
        """Returns the heater configure-sensors-and-heaters mixin service."""
        from .services.heater_config_service import HeaterConfigService

        return HeaterConfigService

    def _create_firmware_upload_service(self, *args, **kwargs):
        """Returns the heater firmware-upload mixin service."""
        from .services.heater_firmware_upload_service import HeaterFirmwareUploadService

        return HeaterFirmwareUploadService
