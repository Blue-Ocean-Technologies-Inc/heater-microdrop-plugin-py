"""Heater Log Viewer demo (standalone).

Opens the Log Viewer panel — the model/view/controller trio from
heater_controls_ui.plots (log_model / LogView / HeaterLogViewerController)
— in its own window, without the Microdrop app, Redis, or a heater board.
A synthetic telemetry log is generated into a temporary heater_logs folder
so the plot opens with data; use the folder button to browse to a real
experiment's heater_logs.

Run:
    python demos/run_heater_log_viewer_demo.py
"""
import json
import math
import os
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from PySide6.QtWidgets import QApplication

from microdrop_style.helpers import style_app

from heater_controls_ui.plots.log_model import HeaterLogViewerModel
from heater_controls_ui.plots.log_view import (
    HeaterLogViewerController, LogView,
)


def write_sample_log(log_dir):
    """A synthetic two-minute stream (2 Hz): two sensors warming up plus a
    PID heater hunting around the bath temperature — the same JSON-Lines
    shape heater_controller.data_logger writes."""
    log_dir.mkdir(parents=True, exist_ok=True)
    start = datetime.now()
    log_path = log_dir / f"{start.strftime('%Y%m%d_%H%M%S')}.jsonl"
    with log_path.open("w", encoding="utf-8") as log_file:
        for tick in range(240):
            stamp = (start + timedelta(seconds=tick / 2)).isoformat()
            bath = 25 + 40 * (1 - math.exp(-tick / 120))
            lid = 24 + 20 * (1 - math.exp(-tick / 160))
            log_file.write(json.dumps({
                "timestamp": stamp, "board_timestamp": tick / 2,
                "_frame": "TEMP",
                "temperatures": {"bath": round(bath, 2),
                                 "lid": round(lid, 2)},
            }) + "\n")
            log_file.write(json.dumps({
                "timestamp": stamp, "board_timestamp": tick / 2,
                "_frame": "PID_TEC1",
                "pid_target": 65.0,
                "pid_temperature": round(bath + 0.6 * math.sin(tick / 5), 2),
                "pwm_percentage": round(max(0.0, 80 * math.exp(-tick / 100)), 1),
            }) + "\n")
    return log_path


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    style_app(app)

    demo_logs_dir = (Path(tempfile.mkdtemp(prefix="heater_log_viewer_demo_"))
                     / "heater_logs")
    sample_log = write_sample_log(demo_logs_dir)
    print(f"Sample log written: {sample_log}")

    model = HeaterLogViewerModel()
    handler = HeaterLogViewerController(model)
    model.directory ="C:\\Users\Info\Documents\Sci-Bots\Microdrop\Experiments\\2026_07_13-19_38_54\heater_logs"
    model.configure_traits(view=LogView, handler=handler)


if __name__ == "__main__":
    main()
