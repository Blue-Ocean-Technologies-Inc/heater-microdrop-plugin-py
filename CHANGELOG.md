## v1.1.1 (2026-07-06)

### Fix

- **ui**: drop the redundant side label on the PID toggle

## v1.1.0 (2026-07-06)

### Feat

- sensor-group dropdown (legacy UI parity), default all
- couple PID-on to Temp mode and gate setpoint publishes on PID state
- add dedicated PID control toggle to the control group
- publish SET_PID_MODE from a dedicated pid_enabled observer
- add pid_enabled model trait for dedicated PID toggle

### Fix

- probe board connection on extra_plugins_loaded; heater-specific log copy
- **plots**: trim the setpoint series with the rolling window
- **plots**: dash the setpoint line
- **plots**: sample all frame keys, gap stale series, add setpoint line + duty echo
- match the legacy UI's PID/stream state machine

### Refactor

- use the utils toggle editors (SlidingToggleEditor / InPlaceToggleEditor)
- port the legacy UI's start_stream/stop_stream verbatim into the backend

## v1.0.2 (2026-07-06)

### Refactor

- drop redundant version from plugin manifest

## v1.0.1 (2026-07-03)
