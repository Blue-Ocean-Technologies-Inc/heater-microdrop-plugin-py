"""Package-level constants for heater_protocol_controls.

Topic constants live in heater_controller/consts.py — this plugin imports them
(same layering as peripheral_protocol_controls).
"""

PKG = '.'.join(__name__.split('.')[:-1])
PKG_name = PKG.title().replace("_", " ")

#: Checkbox field (row trait) of the temperature compound column: drive the
#: heater on this step, or leave it untouched (no setpoint publish, no
#: reached-ack wait). Referenced by the handler gate and the cross-cell
#: editability views.
SET_TEMPERATURE_FIELD_ID = "set_temperature"
