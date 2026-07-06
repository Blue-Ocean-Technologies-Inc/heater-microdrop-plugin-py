import json

from traits.api import observe
from pyface.qt.QtWidgets import QSizePolicy

from template_status_and_controls.base_controller import BaseStatusController
from microdrop_utils.decorators import debounce
from microdrop_utils.dramatiq_pub_sub_helpers import publish_message
from microdrop_utils.traitsui_qt_helpers import stretch_group_layouts_horizontally
from logger.logger_service import get_logger

from heater_controller.consts import (
    SET_TEMPERATURE, SET_PWM, SET_PID_MODE, SET_STREAM, ALL_OFF,
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

    def _apply_mode(self):
        """Drive the board's active setpoint to the current mode's state. Called
        only while streaming is on (the master gate).

        Temp publishes the temperature setpoint ONLY while PID is on:
        ``pid_<heater>_<temp>`` is itself the board's "start PID" command
        (there is no separate live enable), so sending it with the toggle off
        would engage PID against the UI. With PID off a Temp-mode setpoint
        stays staged. PWM publishes the open-loop duty."""
        if self.model.mode == "Temp":
            if self.model.pid_enabled:
                self._publish(SET_TEMPERATURE, self._heater_payload(temperature=self.model.temperature))
        else:
            self._publish(SET_PWM, self._heater_payload(pwm=self.model.pwm))
            self._echo_commanded_pwm(self.model.pwm)

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
            self._publish(SET_TEMPERATURE, self._heater_payload(temperature=event.new))
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
        # PID-on forces Temp mode (set by _on_pid_enabled_changed / the board
        # sync; the view also locks the mode toggle), so a user mode switch
        # only ever happens with PID off. Both modes then run on the board's
        # plain telemetry stream — no board task transition is needed, just
        # drive the new mode's setpoint. While stream is off the mode is
        # staged (applied by _apply_mode when streaming starts).
        if self.model.updating_from_board or self.model.pid_enabled:
            return
        if self.model.stream_active:
            self._apply_mode()
            logger.info(f"Heater UI: Mode --> {event.new}")

    @observe("model:pid_enabled")
    def _on_pid_enabled_changed(self, event):
        """The PID on/off toggle.

        The board has no live enable/disable: PID mode is ENTERED by sending a
        temperature setpoint (``pid_<heater>_<temp>`` starts the PID-coupled
        stream task) and LEFT via ``pid_<heater>_stop`` followed by restarting
        the plain telemetry stream — the same stop-current/start-other
        sequence the legacy standalone UI used (its start_stream). A flip
        while the stream is off is staged and applied on stream start."""
        if self.model.updating_from_board:
            return                      # board-reported state, not a user flip
        if event.new:
            # PID owns the temperature loop: force Temp mode. The mode
            # observer skips publishing while pid_enabled is on.
            self.model.mode = "Temp"
        if not self.model.stream_active:
            logger.info(f"Heater UI: PID control {'on' if event.new else 'off'} staged (stream off)")
            return
        if event.new:
            # Stop the plain stream, then start PID via the setpoint command
            # (which brings its own PID-coupled stream).
            self._publish(SET_STREAM, {"group": "stop"})
            self._publish(SET_TEMPERATURE, self._heater_payload(temperature=self.model.temperature))
            logger.info("Heater UI: PID control --> enabled (Temp mode, closed-loop)")
        else:
            # Stop PID, then resume the plain stream so telemetry continues
            # and manual PWM takes effect again (in PWM mode).
            self._publish(SET_PID_MODE, self._heater_payload(mode="stop"))
            self._publish(SET_STREAM, {"group": "all"})
            logger.info("Heater UI: PID control --> disabled (manual PWM available in PWM mode)")

    @observe("model:stream_active")
    def _on_stream_active_changed(self, event):
        if event.new:
            # Match the legacy UI's start_stream: with PID on, the temperature
            # setpoint command itself starts the PID-coupled stream; otherwise
            # start the plain telemetry stream and drive the current mode.
            if self.model.pid_enabled:
                self._publish(SET_TEMPERATURE, self._heater_payload(temperature=self.model.temperature))
            else:
                self._publish(SET_STREAM, {"group": "all"})
                self._apply_mode()
            logger.info("Heater UI: Stream on request sent...")
        else:
            # Master-gate off: stop PID if it is running (the board will
            # answer with §INFO pid_stopped, which syncs the toggle off),
            # idle the board, and stop telemetry.
            if self.model.pid_enabled:
                self._publish(SET_PID_MODE, self._heater_payload(mode="stop"))
            self._publish(ALL_OFF, {})
            self._publish(SET_STREAM, {"group": "stop"})
