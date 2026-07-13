"""Dramatiq listener that feeds the heater plot model.

Runs as its own listener (see ``plot_listener_name``), so the plot pane is
independent of the status pane. It taps telemetry for the measured series and
the heater REQUEST topics for the commanded ones — the green setpoint line
(the PID target) and the open-loop duty echo, neither of which the board
reports in telemetry (the plain stream carries no duty at all, so without the
echo the PWM line froze at its last closed-loop value while in PWM mode).
"""
import json

from pyface.gui import GUI
from traits.api import Instance

from template_status_and_controls.base_message_handler import BaseMessageHandler
from logger.logger_service import get_logger

from heater_controller.consts import DEFAULT_HEATER
from heater_controls_ui.telemetry import telemetry_samples
from .log_model import HeaterLogViewerModel
from .model import HeaterPlotModel

logger = get_logger(__name__)


class HeaterPlotMessageHandler(BaseMessageHandler):
    """Feeds the plot model: telemetry samples, PID-target changes, and the
    commanded open-loop duty. The inherited connected / disconnected /
    realtime handlers never fire here — this listener's topics only."""

    model = Instance(HeaterPlotModel)

    #: Set by the dock pane once the Log Viewer tab exists; DATA_LOG_SAVED
    #: then auto-shows freshly saved logs there.
    log_viewer_model = Instance(HeaterLogViewerModel)

    def _on_data_log_saved_triggered(self, body):
        """A telemetry log finished writing (body = its path): show it in
        the Log Viewer tab. Marshalled onto the GUI thread — this fires on
        a dramatiq worker, and the trait drives folder scanning + Qt."""
        if self.log_viewer_model is None or not body:
            return
        self.log_viewer_model.saved_log_path=str(body)

    def _on_telemetry_triggered(self, body):
        data = self._payload(body)
        if data is None:
            return
        if data.get("_frame") == "INFO":
            # The board is the source of truth for the PID run state: when
            # its PID task ends, gap the closed-loop lines and the target
            # line instead of flatlining them at stale values.
            if data.get("event") == "pid_stopped":
                self.model.drop_pid_series()
                self.model.set_setpoint(None)
            return
        self.model.apply(telemetry_samples(data))

    # --- commanded values (request topics, published by the controller) ----

    def _on_set_temperature_triggered(self, body):
        data = self._payload(body)
        temperature = (data or {}).get("temperature")
        if isinstance(temperature, (int, float)):
            self.model.set_setpoint(float(temperature))

    def _on_set_pwm_triggered(self, body):
        data = self._payload(body)
        pwm = (data or {}).get("pwm")
        if isinstance(pwm, (int, float)):
            self.model.apply({
                "heater": data.get("heater", DEFAULT_HEATER),
                "pwm_percentage": float(pwm),
            })

    def _on_start_stream_triggered(self, body):
        data = self._payload(body)
        if data is None:
            return
        if data.get("pid"):
            temperature = data.get("temperature")
            if isinstance(temperature, (int, float)):
                self.model.set_setpoint(float(temperature))
        else:
            self.model.set_setpoint(None)
            pwm = data.get("pwm")
            if isinstance(pwm, (int, float)):
                self.model.apply({
                    "heater": data.get("heater", DEFAULT_HEATER),
                    "pwm_percentage": float(pwm),
                })

    def _on_stop_stream_triggered(self, body):
        self.model.set_setpoint(None)

    @staticmethod
    def _payload(body):
        try:
            data = json.loads(body)
        except Exception:
            logger.debug("Plot: failed to parse message payload", exc_info=True)
            return None
        return data if isinstance(data, dict) else None
