from envisage.api import PREFERENCES_CATEGORIES, PREFERENCES_PANES
from heater_controller.consts import HEATER_HWID, START_DEVICE_MONITORING
from microdrop_utils.dramatiq_pub_sub_helpers import publish_message
from microdrop_utils.hardware_device_monitoring_helpers import check_connected_ports_hwid
from template_status_and_controls.base_plugin import BaseStatusPlugin
from traits.api import List, observe

from logger.logger_service import get_logger
logger = get_logger(__name__)

from .consts import PKG, PKG_name, ACTOR_TOPIC_DICT


class HeaterControlsUiPlugin(BaseStatusPlugin):
    """Envisage plugin for heater status display and controls.

    Contributes a Tools ▸ Heater ▸ Search Connection menu entry (the heater's
    connection scan, also reachable by clicking the status-bar heater icon).
    """

    id = PKG + ".plugin"
    name = f"{PKG_name} Plugin"

    # Heater group on its own Heater Settings preferences tab (previously
    # rendered by the magnet plugin's shared Peripheral Settings pane).
    preferences_panes = List(contributes_to=PREFERENCES_PANES)
    preferences_categories = List(contributes_to=PREFERENCES_CATEGORIES)

    def _preferences_panes_default(self):
        from .preferences import HeaterPreferencesPane
        return [HeaterPreferencesPane]

    def _preferences_categories_default(self):
        from .preferences import heater_tab
        return [heater_tab]

    def _get_dock_pane_class(self):
        from .dock_pane import HeaterStatusDockPane
        return HeaterStatusDockPane

    def _get_extra_dock_pane_classes(self) -> list:
        # Second dock pane: live Temperature / PWM plots.
        from .plots.dock_pane import HeaterPlotDockPane
        return [HeaterPlotDockPane]

    def _get_actor_topic_dict(self) -> dict:
        return ACTOR_TOPIC_DICT

    def _get_menu_additions(self) -> list:
        from pyface.action.schema.schema_addition import SchemaAddition
        from .menus import tools_menu_factory
        return [
            SchemaAddition(
                factory=tools_menu_factory,
                path="MenuBar/Tools",
            )
        ]

    @observe("application:extra_plugins_loaded")
    def _on_app_initialized(self, event):

        # check if peripheral board connected
        if check_connected_ports_hwid(HEATER_HWID):
            logger.critical(
                "Heater Board Maybe Connected: Requesting Heater Board Search"
            )
            publish_message(message="", topic=START_DEVICE_MONITORING)
        else:
            logger.info(
                "Heater Board not connected. To start search, goto tools menu:"
                "Tools -> Peripherals -> Heater -> Search Connection or use Heater UI status bar Button."
            )
