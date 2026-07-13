from peripheral_device_controller_base.consts import connected_topic, disconnected_topic, searching_topic

# This module's package.
PKG = '.'.join(__name__.split('.')[:-1])
PKG_name = PKG.title().replace("_", " ")

DEVICE_NAME = "Heater"

# Heater controller hardware id (RP2040 / MicroPython, VID 2E8A, PID 0005).
# The fluorescence LED board shares this VID:PID, so the monitor also
# matches the whoami device_id before claiming a port.
HEATER_HWID = "VID:PID=2E8A:0005"
DEVICE_ID_FRAGMENT = "heater"
BOARD_BAUDRATE = 115200

# Heater channel targeted when a command payload omits one (mirrors the old UI
# fallback). The set of real channels is discovered on connect and published on
# HEATERS_AVAILABLE so a frontend can offer a selection dropdown.
DEFAULT_HEATER = "tec1"

# Delay between stopping the board's current run mode and starting the next
# one (legacy standalone UI's COMMAND_DELAY_SHORT): the firmware task needs
# time to wind down before a new pid/stream task starts cleanly.
COMMAND_DELAY_SHORT = 1

# Folder inside the current experiment's directory that collects the
# telemetry logs written while the board streams (port of the legacy
# standalone UI's DataLogger, which used the same folder name).
HEATER_LOGS_DIR_NAME = "heater_logs"

# Markers the firmware wraps its `dump_config` JSON response in.
CONFIG_BEGIN = "<<<CONFIG_BEGIN>>>"
CONFIG_END = "<<<CONFIG_END>>>"
CONFIG_ERROR_PREFIX = "<<<CONFIG_ERROR"

# Bus-level keys inside the config's `1-wire-sensors` section that are NOT
# sensor name->ROM entries (so they can never be used as a sensor name).
OW_RESERVED_KEYS = frozenset({"pin", "conv_mode", "resolution"})

# Topics published by this plugin (signals)
CONNECTED = connected_topic(DEVICE_NAME)
DISCONNECTED = disconnected_topic(DEVICE_NAME)
# JSON bool: True while scanning for the board, False once connected/stopped.
SEARCHING = searching_topic(DEVICE_NAME)
HEATERS_AVAILABLE = f"{DEVICE_NAME}/signals/heaters_available"
# Parsed §<FRAME>{json} telemetry packets (temperatures, PWM, board id, events).
TELEMETRY = f"{DEVICE_NAME}/signals/telemetry"
# A telemetry log file finished writing (payload: the saved file's path).
# The Log Viewer tab auto-shows it.
DATA_LOG_SAVED = f"{DEVICE_NAME}/signals/data_log_saved"
# Full dump_config JSON document (the board's current sensor/heater config).
CONFIG_DUMPED = f"{DEVICE_NAME}/signals/config_dumped"
# JSON list of 1-Wire ROM ids discovered on the bus by the last scan.
SENSORS_SCANNED = f"{DEVICE_NAME}/signals/sensors_scanned"
# Result of a save-config-to-board push: JSON {"ok": bool, "message": str}.
CONFIG_PUSHED = f"{DEVICE_NAME}/signals/config_pushed"
# Protocol ack: published when a watched heater's PID temperature reaches the
# protocol target within tolerance. Payload {"heater": str, "temperature": float}.
TEMPERATURE_REACHED = f"{DEVICE_NAME}/signals/temperature_reached"

# Service Request Topics
START_DEVICE_MONITORING = f"{DEVICE_NAME}/requests/start_device_monitoring"
RETRY_CONNECTION = f"{DEVICE_NAME}/requests/retry_connection"
SEND_COMMAND = f"{DEVICE_NAME}/requests/send_command"
# Configure-sensors-and-heaters requests (handled by HeaterConfigService).
SCAN_SENSORS = f"{DEVICE_NAME}/requests/scan_sensors"
DUMP_CONFIG = f"{DEVICE_NAME}/requests/dump_config"
# Write a config (JSON payload) onto the board's filesystem + reboot it.
SAVE_CONFIG_TO_BOARD = f"{DEVICE_NAME}/requests/save_config_to_board"
# Protocol step: set a PID target and block until the PID temperature is within
# tolerance. Request payload {heater, temperature, tolerance}; the backend acks
# on TEMPERATURE_REACHED once reached (so the protocol step can wait_for it).
PROTOCOL_SET_TEMPERATURE = f"{DEVICE_NAME}/requests/protocol_set_temperature"
SET_TEMPERATURE = f"{DEVICE_NAME}/requests/set_temperature"
SET_PWM = f"{DEVICE_NAME}/requests/set_pwm"
SET_PID_MODE = f"{DEVICE_NAME}/requests/set_pid_mode"
SET_STREAM = f"{DEVICE_NAME}/requests/set_stream"
# Run-mode transitions (ports of the legacy standalone UI's start_stream /
# stop_stream): the whole stop-current -> delay -> start-new serial sequence
# runs inside ONE backend handler invocation, because separate pub/sub
# messages are consumed by a multi-threaded worker pool with no ordering
# guarantee.
START_STREAM = f"{DEVICE_NAME}/requests/start_stream"
STOP_STREAM = f"{DEVICE_NAME}/requests/stop_stream"
SET_FAN = f"{DEVICE_NAME}/requests/set_fan"
ALL_OFF = f"{DEVICE_NAME}/requests/all_off"

# Topics actor declared by plugin subscribes to. The listener-name key MUST match
# HeaterControllerBase.listener_name.
ACTOR_TOPIC_DICT = {
    "heater_controller_listener": [
        f"{DEVICE_NAME}/requests/#",
        CONNECTED,
        DISCONNECTED,
    ]}
