# heater-microdrop-plugin

MicroDrop heater plugin, packaged as an installable conda package:

- `heater_controller/` — backend board driver (telemetry, PID/PWM commands,
  sensor/heater config ops, protocol set-temperature with reached ack).
- `heater_controls_ui/` — status/controls dock pane, live temperature/PWM
  plotting pane, Configure Sensors & Heaters dialog, status-bar icon.
- `heater_protocol_controls/` — heater temperature protocol column.
- `standalone_heater_app/` — the original standalone heater control app
  (reference only; not packaged).

`microdrop_plugin.toml` declares the two toggleable plugin groups
(`heater_ui`, `heater_backend`); MicroDrop discovers it through the
`microdrop.plugins` entry point. See `docs/PLUGIN_DEVELOPMENT.md` in the
MicroDrop source tree for the plugin model.

## Build

```bash
pixi build
```

(uses `pixi-build-python`; the wheel force-includes the manifest as package
data of `heater_controller`).
