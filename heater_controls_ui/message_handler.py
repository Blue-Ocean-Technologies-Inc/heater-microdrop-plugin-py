import json

from traits.api import Instance

from template_status_and_controls.base_message_handler import BaseMessageHandler
from logger.logger_service import get_logger

from heater_controller.consts import (
    FIRMWARE_UPLOAD_FINISHED, FIRMWARE_UPLOAD_LOG, FIRMWARE_UPLOAD_STARTED,
)

from .consts import PWM_MIN, PWM_MAX
from .live_state import heater_live_state
from .model import HeaterStatusModel
from .sensor_config.model import SensorConfigModel
from .telemetry import resolve_selection, format_telemetry

logger = get_logger(__name__)

# ERR kinds that mean the board stopped driving the heater → reflect as halted.
HALTING_ERR_KINDS = ("overtemp", "task_crash", "sensor_fail")


class HeaterMessageHandler(BaseMessageHandler):
    """Dramatiq message handler for the heater UI.

    Inherits the common connected / disconnected handlers from BaseMessageHandler.
    Adds heater-specific handlers for the available-heaters list and telemetry.
    """

    model = Instance(HeaterStatusModel)
    # Shared with the Configure Sensors & Heaters dialog (owned by the dock pane).
    config_model = Instance(SensorConfigModel)

    def _on_connected_triggered(self, body):
        """Base handler flips the connected flag; also ferry the board's
        serial port to live_state so the firmware-upload dialog keeps its
        port combo in sync with the auto-detected port. The monitor
        republishes a "<device>_connected" sentinel (not a port) when asked
        to start monitoring an already-connected board — ignore that."""
        super()._on_connected_triggered(body)
        port = str(body)
        if port and not port.endswith("_connected"):
            heater_live_state.board_port = port

    def _on_disconnected_triggered(self, body):
        """Base handler clears the connected flag; also clear the ferried
        port and board id so the firmware-upload dialog shows no auto-detected
        port and a blank board id while disconnected."""
        super()._on_disconnected_triggered(body)
        heater_live_state.board_port = ""
        heater_live_state.board_device_id = ""

    def _on_board_id_triggered(self, body):
        """Identity from the connect-time whoami probe -> live_state, so the
        firmware-upload dialog shows it read-only and flashes this board."""
        try:
            identity = json.loads(body)
        except Exception:
            logger.error(f"Unparseable board id payload: {body!r}")
            return
        heater_live_state.board_device_id = str(
            identity.get("device_id") or "")

    def _on_firmware_upload_started_triggered(self, body):
        """Backend accepted an upload — ferry to the GUI thread via live_state
        (the dialog's dispatch="ui" observer applies it)."""
        heater_live_state.firmware_upload_message = (
            FIRMWARE_UPLOAD_STARTED, body)

    def _on_firmware_upload_log_triggered(self, body):
        """One uploader progress line — ferry to the GUI thread."""
        heater_live_state.firmware_upload_message = (FIRMWARE_UPLOAD_LOG, body)

    def _on_firmware_upload_finished_triggered(self, body):
        """Upload outcome — ferry to the GUI thread."""
        heater_live_state.firmware_upload_message = (
            FIRMWARE_UPLOAD_FINISHED, body)

    def _on_config_dumped_triggered(self, body):
        """Full dump_config JSON document → the configurator model."""
        if self.config_model is not None and not self.config_model.load_config_text(body):
            logger.error("Failed to parse dumped heater config")

    def _on_sensors_scanned_triggered(self, body):
        """JSON list of 1-Wire ROMs found on the bus → the configurator model."""
        if self.config_model is None:
            return
        try:
            roms = json.loads(body)
        except Exception:
            logger.error("Failed to parse sensors_scanned signal", exc_info=True)
            return
        if isinstance(roms, list):
            self.config_model.set_scanned_roms(roms)

    def _on_config_pushed_triggered(self, body):
        """Result of a save-config-to-board push (JSON {ok, message}) → shown at
        the bottom of the configurator dialog."""
        if self.config_model is None:
            return
        try:
            result = json.loads(body)
        except Exception:
            logger.error("Failed to parse config_pushed signal", exc_info=True)
            return
        prefix = "✓" if result.get("ok") else "✗"
        self.config_model.push_status = f"{prefix} {result.get('message', '')}"

    def _on_searching_triggered(self, body):
        """Backend connection-scan state (JSON bool). Mirrored to the model so the
        dock pane can disable the status-icon 'search connection' click while a
        scan is already running."""
        try:
            self.model.searching = bool(json.loads(body))
        except Exception:
            logger.error("Failed to parse searching signal", exc_info=True)

    def _on_heaters_available_triggered(self, body):
        try:
            heaters = json.loads(body)
        except Exception:
            return
        if not isinstance(heaters, list):
            return
        self.model.available_heaters = list(heaters)
        self.model.trait_set(**resolve_selection(self.model.selected_heater, heaters))

    def _on_telemetry_triggered(self, body):
        try:
            data = json.loads(body)
        except Exception:
            logger.error("Failed to parse telemetry", exc_info=True)
            return
        if not isinstance(data, dict):
            logger.debug("Failed to parse telemetry")
            return

        if data.get("_frame") == "INFO":
            self._on_info_frame(data)
            return

        heater, updates = format_telemetry(data, pid_mode=self.model.pid_enabled)
        if updates:
            if heater is None:
                self.model.trait_set(**updates)        # global readouts
            else:
                readout = self._readout_for(heater)    # per-heater row
                if readout is not None:
                    readout.trait_set(**updates)

        # While PID drives the duty, mirror the selected heater's live duty
        # into the open-loop `pwm` setpoint so the "Set PWM" field tracks the
        # real value (and switching to PWM mode after PID resumes from it, not
        # a stale value). The pwm observer ignores writes while PID is on, so
        # this publishes no command.
        if self.model.pid_enabled and heater == self.model.selected_heater:
            live_pwm = data.get("pwm_percentage")
            if isinstance(live_pwm, (int, float)):
                self.model.pwm = max(PWM_MIN, min(PWM_MAX, round(live_pwm)))

        if data.get("_frame") == "ERR" and data.get("kind") in HALTING_ERR_KINDS:
            self.model.halted = True
            # The board stopped driving the heater — its PID task is gone.
            self._sync_pid_from_board(False)

    def _on_info_frame(self, data):
        """Structured §INFO events. The board is the source of truth for the
        PID run state (pid_started / pid_stopped), exactly like the legacy
        standalone UI's _on_info_frame."""
        event = data.get("event")
        if event == "pid_started":
            self._sync_pid_from_board(True)
        elif event == "pid_stopped":
            self._sync_pid_from_board(False)
        else:
            logger.debug(f"Heater INFO event: {data}")

    def _sync_pid_from_board(self, enabled):
        """Reflect the board-reported PID state into the model WITHOUT
        re-publishing commands: the controller's observers skip while
        ``updating_from_board`` is set."""
        enabled = bool(enabled)
        if self.model.pid_enabled == enabled:
            return
        self.model.updating_from_board = True
        try:
            self.model.pid_enabled = enabled
            if enabled:
                self.model.mode = "Temp"   # PID owns the temperature loop
        finally:
            self.model.updating_from_board = False
        logger.info(f"Heater UI: board reports PID {'started' if enabled else 'stopped'}")

    def _readout_for(self, name):
        """The HeaterReadout row for ``name``, or None if not yet known (the
        heaters_available signal that creates the rows may lag the first frame)."""
        for readout in self.model.heater_readouts:
            if readout.name == name:
                return readout
        return None
