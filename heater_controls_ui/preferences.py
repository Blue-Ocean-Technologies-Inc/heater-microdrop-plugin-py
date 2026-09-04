"""Heater UI preferences.

A small PreferencesHelper on the SAME "Peripheral Settings" node the Z-Stage
preferences use (``microdrop.peripheral_settings``), holding only the heater's
own trait — so the heater plugin needs no import from the Z-Stage/magnet
plugin, and values saved before the split keep working (same node + key).

Shown on the heater's own Heater Settings tab (previously rendered by the
magnet plugin's shared Peripheral Settings pane).
"""

from envisage.ui.tasks.api import PreferencesCategory, PreferencesPane
from traits.api import Bool, Directory
from traitsui.api import Group, Item, View

from heater_controller.compensation import HeaterCompensationPreferences
from microdrop_application.menus import is_advanced_mode

from microdrop_style.text_styles import preferences_group_style_sheet

from microdrop_utils.preferences_UI_helpers import create_item_label_group


class HeaterPreferences(HeaterCompensationPreferences):
    """Heater-owned slice of the shared Peripheral Settings node (the
    compensation traits come from HeaterCompensationPreferences, defined in
    heater_controller so the protocol tree can read them too)."""

    # Whether to warn ("will apply when streaming starts") when the user
    # changes a setpoint while streaming is off.
    heater_show_stream_off_warning = Bool(
        True,
        desc="Show the 'applies when streaming starts' warning when "
        "setting a heater setpoint while streaming is off",
    )

    firmware_source = Directory(desc="Firmware directory or zip file")

    # Transient advanced-mode flag (trailing underscore => never persisted):
    # the preferences dialog is rebuilt on every open, so seeding it once at
    # creation is enough to show/hide the Advanced group below.
    advanced_mode_ = Bool()

    def _advanced_mode__default(self):
        return is_advanced_mode()


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

    # Advanced-mode-only extras: the setpoint compensation preferences.
    # Hidden entirely while Advanced Mode is off (and the message handler
    # force-clears heater_use_compensation on advanced-off, so nothing keeps
    # compensating in normal mode).
    advanced_group = Group(
        create_item_label_group(
            "heater_use_compensation",
            label_text="Use compensation (setpoint sent = base × rate + offset)",
            orientation="horizontal",
            label_position="last",
        ),
        Item(
            "heater_compensation_rate",
            label="Compensation rate",
            enabled_when="heater_use_compensation",
        ),
        Item(
            "heater_compensation_offset",
            label="Compensation offset (°C)",
            enabled_when="heater_use_compensation",
        ),
        label="Advanced",
        show_border=True,
        style_sheet=preferences_group_style_sheet,
        visible_when="advanced_mode_",
    )

    view = View(
        controls_group,
        Item("_"),  # Separator
        advanced_group,
        Item("_"),  # Separator to space this out from further contributions.
        resizable=True,
    )
