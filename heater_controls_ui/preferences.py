"""Heater UI preferences.

A small PreferencesHelper on the SAME "Peripheral Settings" node the Z-Stage
preferences use (``microdrop.peripheral_settings``), holding only the heater's
own trait — so the heater plugin needs no import from the Z-Stage/magnet
plugin, and values saved before the split keep working (same node + key).

Shown on the heater's own Heater Settings tab (previously rendered by the
magnet plugin's shared Peripheral Settings pane).
"""
from apptools.preferences.api import PreferencesHelper
from envisage.ui.tasks.api import PreferencesCategory, PreferencesPane
from traits.api import Bool
from traitsui.api import Item, View

from microdrop_style.text_styles import preferences_group_style_sheet
from microdrop_utils.preferences_UI_helpers import create_item_label_group


class HeaterPreferences(PreferencesHelper):
    """Heater-owned slice of the shared Peripheral Settings node."""

    preferences_path = "microdrop.peripheral_settings"

    # Whether to warn ("will apply when streaming starts") when the user
    # changes a setpoint while streaming is off.
    heater_show_stream_off_warning = Bool(
        True, desc="Show the 'applies when streaming starts' warning when "
                   "setting a heater setpoint while streaming is off"
    )


heater_tab = PreferencesCategory(
    id="microdrop.peripheral_settings.heater",
    name="Heater Settings",
    after="microdrop.dropbot_settings",
)


class HeaterPreferencesPane(PreferencesPane):
    """The heater plugin's own Heater Settings tab (its traits stay on the
    shared ``microdrop.peripheral_settings`` node, so values saved before
    the tab split keep working)."""

    model_factory = HeaterPreferences

    category = heater_tab.id

    controls_group = create_item_label_group(
        "heater_show_stream_off_warning",
        label_text="Warn when setting a heater setpoint while streaming is off",
        orientation="horizontal",
        label_position="last",
        group_label="Controls",
        group_show_border=True,
        group_style_sheet=preferences_group_style_sheet,
    )

    view = View(
        controls_group,
        Item("_"),  # Separator to space this out from further contributions.
        resizable=True,
    )
