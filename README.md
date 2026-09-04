# heater-microdrop-plugin

[![Managed by Copier](https://img.shields.io/badge/managed%20by-copier-fa4e49)](https://github.com/copier-org/copier)
[![Template](https://img.shields.io/badge/template-microdrop--plugin--template%40v0.1.0-blue)](https://github.com/Blue-Ocean-Technologies-Inc/microdrop-plugin-template)

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
