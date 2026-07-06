import json

from traits.api import observe
from pyface.qt.QtWidgets import QSizePolicy

from template_status_and_controls.base_controller import BaseStatusController
from microdrop_utils.decorators import debounce
from microdrop_utils.dramatiq_pub_sub_helpers import publish_message
from microdrop_utils.traitsui_qt_helpers import stretch_group_layouts_horizontally
from logger.logger_service import get_logger

from heater_controller.consts import (
    SET_TEMPERATURE, SET_PWM, START_STREAM, STOP_STREAM,
)

logger = get_logger(__name__)


class HeaterControlsController(BaseStatusController):
    """Heater controls controller.

    Translates model changes into published command topics. The heater has no
    realtime-queue concept (the backend rejects commands while disconnected and
    the view disables controls then), so commands publish directly rather than
    going through the base realtime queue.
    """

    # ------------------------------------------------------------------ #
    # UI build hook                                                        #
    # ------------------------------------------------------------------ #
    def init(self, info):
        """Stretch the collapsible sections to the full pane width once the UI
        is built (TraitsUI otherwise left-hugs each group to its content), and
        stop the heater-readouts list from absorbing spare vertical height."""
        stretch_group_layouts_horizontally(info.ui.control)
        readouts = getattr(info, "heater_readouts", None)
        if readouts is not None and readouts.control is not None:
            # The custom ListEditor pane is Expanding/Expanding; cap it so the
            # group sizes to its 1-3 rows instead of leaving a big gap below them.
            policy = readouts.control.sizePolicy()
            policy.setVerticalPolicy(QSizePolicy.Policy.Maximum)
            readouts.control.setSizePolicy(policy)
        return super().init(info)

    # ------------------------------------------------------------------ #
    # Debounced setattr (prevents flooding while dragging the spinboxes)   #
    # ------------------------------------------------------------------ #
    @debounce(wait_seconds=0.3)
    def temperature_setattr(self, info, obj, traitname, value):
        return super().setattr(info, obj, traitname, value)

    @debounce(wait_seconds=0.3)
    def pwm_setattr(self, info, obj, traitname, value):
        return super().setattr(info, obj, traitname, value)

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #
    def _heater_payload(self, **extra):
        """Payload including the selected heater (omitted when none selected, so
        the backend applies its tec1 default)."""
        payload = dict(extra)
        if self.model.selected_heater:
            payload["heater"] = self.model.selected_heater
        return payload

    def _group_payload(self, **extra):
        """_heater_payload plus the sensor group, matching the legacy UI's
        combo semantics: "None" omits the group suffix entirely (board default
        sensor); anything else — including "all" — is sent as the suffix."""
        payload = self._heater_payload(**extra)
        if self.model.sensor_group != "None":
            payload["sensor_group"] = self.model.sensor_group
        return payload

    @staticmethod
    def _publish(topic, payload):
        publish_message(message=json.dumps(payload), topic=topic)

    def _echo_commanded_pwm(self, value):
        """Reflect the commanded open-loop duty into the selected heater's readout
        (the board doesn't report open-loop duty in telemetry)."""
        for readout in self.model.heater_readouts:
            if readout.name == self.model.selected_heater:
                readout.pwm_display = f"{value} %"
                return

    # ------------------------------------------------------------------ #
    # Run-mode transitions — ports of the legacy standalone UI's slots.    #
    # Each transition is ONE published request; the backend executes the   #
    # legacy stop -> delay -> start serial sequence atomically (separate   #
    # pub/sub messages have no ordering guarantee across the worker pool). #
    # ------------------------------------------------------------------ #
    def start_stream(self):
        """Legacy start_stream(): (re)start the board in the mode the UI shows —
        PID toward the temperature setpoint, or plain telemetry streaming with
        the open-loop duty re-asserted when in PWM mode. The sensor group rides
        along (PID input selection / which sensors stream)."""
        payload = self._group_payload(pid=self.model.pid_enabled)
        if self.model.pid_enabled:
            payload["temperature"] = self.model.temperature
        elif self.model.mode == "PWM":
            payload["pwm"] = self.model.pwm
            self._echo_commanded_pwm(self.model.pwm)
        self._publish(START_STREAM, payload)

    def stop_stream(self):
        """Legacy stop_stream(), plus all_off so nothing keeps heating while
        streaming is off."""
        self._publish(STOP_STREAM, self._heater_payload(all_off=True))

    # ------------------------------------------------------------------ #
    # Observers → published commands                                       #
    # ------------------------------------------------------------------ #
    # Setpoint edits only reach the board while streaming (the master gate) and
    # only for the active mode; otherwise they are staged and pushed by
    # _apply_mode when streaming starts.
    @observe("model:temperature")
    def _on_temperature_changed(self, event):
        if self.model.mode != "Temp":
            logger.debug("Heater in PWM mode. Temperature cannot be changed.")
            return
        if self.model.stream_active and self.model.pid_enabled:
            # Legacy on_setpoint_changed: the live setpoint command carries the
            # sensor group too (pid_<h>_<t>[_<group>]).
            self._publish(SET_TEMPERATURE, self._group_payload(temperature=event.new))
            logger.debug(f"Temperature --> {event.new} °C")
        else:
            logger.debug(f"Temperature setpoint {event.new} °C staged (stream off or pid mode disabled)")
            self.model.stream_off_edit_warning = True

    @observe("model:pwm")
    def _on_pwm_changed(self, event):
        if self.model.mode != "PWM":
            logger.debug("Heater in temperature mode. PWM cannot be changed.")
            return
        if self.model.pid_enabled:
            logger.debug("Heater in PID mode. PWM cannot be changed.")
            return
        if not self.model.stream_active:
            logger.debug(f"PWM duty {event.new} % staged (stream off)")
            self.model.stream_off_edit_warning = True
            return

        self._publish(SET_PWM, self._heater_payload(pwm=event.new))
        self._echo_commanded_pwm(event.new)
        logger.debug(f"PWM → {event.new} %")

    @observe("model:mode")
    def _on_mode_changed(self, event):
        # PID-on forces Temp mode (the view also locks the toggle), so a user
        # mode switch only ever happens with PID off — both modes then run on
        # the board's plain telemetry stream, no task transition needed.
        # Switching to PWM drives the staged duty; switching to Temp stages
        # the setpoint (it only reaches the board when PID is enabled).
        if self.model.updating_from_board or self.model.pid_enabled:
            return
        if self.model.stream_active and event.new == "PWM":
            self._publish(SET_PWM, self._heater_payload(pwm=self.model.pwm))
            self._echo_commanded_pwm(self.model.pwm)
            logger.info("Heater UI: Mode --> PWM (manual duty)")

    @observe("model:sensor_group")
    def _on_sensor_group_changed(self, event):
        """Legacy on_sensor_group_changed(): while streaming, restart the
        stream with the new group; otherwise it applies on the next start."""
        if self.model.updating_from_board:
            return
        if self.model.stream_active:
            logger.info(f"Heater UI: sensor group --> {event.new}, restarting stream")
            self.start_stream()

    @observe("model:pid_enabled")
    def _on_pid_enabled_changed(self, event):
        """Legacy on_pid_toggled(): while streaming, restart the stream in the
        new mode (the backend runs the stop -> delay -> start sequence);
        otherwise the flip is staged for the next stream start."""
        if self.model.updating_from_board:
            return                      # board-reported state, not a user flip
        if event.new:
            # PID owns the temperature loop: force Temp mode. The mode
            # observer skips publishing while pid_enabled is on.
            self.model.mode = "Temp"
        if self.model.stream_active:
            logger.info(f"Heater UI: PID {'enabled' if event.new else 'disabled'}, restarting stream")
            self.start_stream()
        else:
            logger.info(f"Heater UI: PID {'enabled' if event.new else 'disabled'} (applies on next stream start)")

    @observe("model:stream_active")
    def _on_stream_active_changed(self, event):
        if self.model.updating_from_board:
            return
        if event.new:
            self.start_stream()
        else:
            self.stop_stream()
