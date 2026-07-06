import time

from traits.api import provides, Bool, HasTraits, Instance

from ..interfaces.i_heater_control_mixin_service import IHeaterControlMixinService
from ..heater_serial_proxy import HeaterSerialProxy
from ..consts import COMMAND_DELAY_SHORT
from ..datamodels import (
    SetTemperatureData,
    SetPwmData,
    SetPidModeData,
    SetStreamData,
    SetFanData,
    ProtocolSetTemperatureData,
    StartStreamData,
    StopStreamData,
)

from logger.logger_service import get_logger
logger = get_logger(__name__)


@provides(IHeaterControlMixinService)
class HeaterCommandSetterService(HasTraits):
    """Sends commands to the heater.

    ``on_send_command_request`` is the generic raw-command escape hatch (forwards
    the message content verbatim). The typed handlers validate a small JSON
    payload and format the matching plain-text command, so callers/protocols/UI
    don't have to know the wire syntax:

        set_temperature -> pid_<heater>_<temp>[_<group>]
        set_pwm         -> pwm_<heater>_<pwm>
        set_pid_mode    -> pid_<heater>_<enable|disable|stop>
        set_stream      -> stream_all | stream_<group> | stream_stop
        set_fan         -> fan_on | fan_off
        all_off         -> all_off
    """
    proxy = Instance(HeaterSerialProxy)

    #: True while the board runs the PID-coupled stream task — mirrors the
    #: legacy standalone UI's ``pid_active``, so the stop half of a transition
    #: knows whether to send ``pid_stop`` or ``stream_stop``.
    _pid_active = Bool(False)

    # ------------------------------------------------------------------
    # Generic raw command
    # ------------------------------------------------------------------
    def on_send_command_request(self, message):
        command = message.content
        if not command:
            logger.warning("Heater send_command request with empty content; ignoring")
            return
        self._send(command)

    # ------------------------------------------------------------------
    # Typed commands
    # ------------------------------------------------------------------
    def on_set_temperature_request(self, message):
        data = self._parse(SetTemperatureData, message)
        if data is None:
            return
        if data.sensor_group:
            cmd = f"pid_{data.heater}_{data.temperature}_{data.sensor_group}"
        else:
            cmd = f"pid_{data.heater}_{data.temperature}"
        self._send(cmd)

    def on_set_pwm_request(self, message):
        data = self._parse(SetPwmData, message)
        if data is None:
            return
        self._send(f"pwm_{data.heater}_{data.pwm}")

    def on_set_pid_mode_request(self, message):
        data = self._parse(SetPidModeData, message)
        if data is None:
            return
        self._send(f"pid_{data.heater}_{data.mode}")

    def on_set_stream_request(self, message):
        data = self._parse(SetStreamData, message)
        if data is None:
            return
        if data.group == "stop":
            cmd = "stream_stop"
        elif data.group == "all":
            cmd = "stream_all"
        else:
            cmd = f"stream_{data.group}"
        self._send(cmd)

    def on_set_fan_request(self, message):
        data = self._parse(SetFanData, message)
        if data is None:
            return
        self._send("fan_on" if data.on else "fan_off")

    def on_all_off_request(self, message):
        self._send("all_off")

    # ------------------------------------------------------------------
    # Run-mode transitions — ports of the legacy standalone UI's
    # start_stream() / stop_stream(). The whole stop-current -> delay ->
    # start-new sequence runs inside ONE handler invocation: separate
    # pub/sub messages are consumed by a multi-threaded worker pool with
    # NO ordering guarantee, which is exactly how interleaved stream/pid
    # commands corrupted the board's run mode.
    # ------------------------------------------------------------------
    def on_start_stream_request(self, message):
        data = self._parse(StartStreamData, message)
        if data is None:
            return
        # Stop any existing run mode first (legacy UI: pid_stop vs
        # stream_stop), then give the firmware task time to wind down.
        self._send("pid_stop" if self._pid_active else "stream_stop")
        time.sleep(COMMAND_DELAY_SHORT)
        if data.pid:
            # The setpoint command itself starts PID + its coupled stream —
            # there is no separate live "enable" in this flow.
            if data.sensor_group:
                self._send(f"pid_{data.heater}_{data.temperature}_{data.sensor_group}")
            else:
                self._send(f"pid_{data.heater}_{data.temperature}")
            self._pid_active = True
        else:
            self._send(f"stream_{data.sensor_group}" if data.sensor_group else "stream_all")
            self._pid_active = False
            if data.pwm is not None:
                # Re-assert the staged open-loop duty on the fresh stream.
                self._send(f"pwm_{data.heater}_{data.pwm}")

    def on_stop_stream_request(self, message):
        data = self._parse(StopStreamData, message)
        if data is None:
            return
        self._send("pid_stop" if self._pid_active else "stream_stop")
        self._pid_active = False
        if data.all_off:
            self._send("all_off")

    # ------------------------------------------------------------------
    # Protocol step: set target + arm the "reached within tolerance" ack
    # ------------------------------------------------------------------
    def on_protocol_set_temperature_request(self, message):
        data = self._parse(ProtocolSetTemperatureData, message)
        if data is None:
            return
        # Resolve to a real board channel: the protocol's default ("tec1") often
        # isn't what the board reports (e.g. "heater1"), which would make both the
        # PID command and the reached-watch target the wrong channel.
        heater = data.heater
        available = self.proxy.available_heaters or []
        if available and heater not in available:
            heater = available[0]
            logger.info(f"Protocol heater '{data.heater}' not on board; using '{heater}'")
        # Closed-loop toward the target and make sure telemetry is streaming so
        # the proxy can watch the PID temperature, then arm the ack watcher.
        self._send(f"pid_{heater}_enable")
        self._send(f"pid_{heater}_{data.temperature}")
        self._send("stream_all")
        self._pid_active = True
        self.proxy.set_temperature_target(heater, data.temperature, data.tolerance)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _parse(model, message):
        """Validate the message JSON payload against ``model``; log and return
        None on failure so a bad payload never crashes the listener."""
        try:
            return model.model_validate_json(message.content)
        except Exception as e:
            logger.error(f"Invalid {model.__name__} payload {message.content!r}: {e}")
            return None

    def _send(self, command):
        with self.proxy.transaction_lock:
            self.proxy.send_command(command)
