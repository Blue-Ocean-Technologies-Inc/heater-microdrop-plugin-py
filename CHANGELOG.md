## [v1.10.1](https://github.com/Blue-Ocean-Technologies-Inc/heater-microdrop-plugin-py/releases/tag/v1.10.1) (2026-09-01)

### Fix

- type the data logger and plot locks by the lock class ([`331fdad`](https://github.com/Blue-Ocean-Technologies-Inc/heater-microdrop-plugin-py/commit/331fdad21c7f218d669ed8903c8a4b7525368f8a))

## [v1.10.0](https://github.com/Blue-Ocean-Technologies-Inc/heater-microdrop-plugin-py/releases/tag/v1.10.0) (2026-08-24)

### Feat

- **protocol-controls**: compensate protocol step targets ([`8a1e32b`](https://github.com/Blue-Ocean-Technologies-Inc/heater-microdrop-plugin-py/commit/8a1e32b6593553f347385d1d0df0ed21786f9b52))
- **controls-ui**: compensate setpoints before publishing ([`3da9228`](https://github.com/Blue-Ocean-Technologies-Inc/heater-microdrop-plugin-py/commit/3da922871a90bac1b9190ba528389ea24302986e))
- **controls-ui**: advanced-mode compensation preferences ([`45296bb`](https://github.com/Blue-Ocean-Technologies-Inc/heater-microdrop-plugin-py/commit/45296bb21a8457da3661c7934dc61ba94b71abaa))
- **controller**: add shared setpoint-compensation module ([`499285d`](https://github.com/Blue-Ocean-Technologies-Inc/heater-microdrop-plugin-py/commit/499285d5858e99ed4a41071ce0355763aaa478ae))

### Fix

- **controller**: throttle per-frame telemetry debug log ([`5278a8e`](https://github.com/Blue-Ocean-Technologies-Inc/heater-microdrop-plugin-py/commit/5278a8e193cfc7388b9c84ea9c929562d4d6be2e))

## [v1.9.1](https://github.com/Blue-Ocean-Technologies-Inc/heater-microdrop-plugin-py/releases/tag/v1.9.1) (2026-08-06)

### Fix

- **controller**: adopt the monitor's claimed serial handle ([`6434ff5`](https://github.com/Blue-Ocean-Technologies-Inc/heater-microdrop-plugin-py/commit/6434ff53e68979887db51ff16be40b8cbe367fb3))
- **controller**: relinquish port on wrong-board whoami identity ([`154fcff`](https://github.com/Blue-Ocean-Technologies-Inc/heater-microdrop-plugin-py/commit/154fcff23aab7c0695e614fcdff67a27de7ae7ab))

### Refactor

- **controls-ui**: show fan as sliding switch beside PID toggle ([`db8f8b1`](https://github.com/Blue-Ocean-Technologies-Inc/heater-microdrop-plugin-py/commit/db8f8b16a376ea2527d469bd994031c4e2617854))

## [v1.9.0](https://github.com/Blue-Ocean-Technologies-Inc/heater-microdrop-plugin-py/releases/tag/v1.9.0) (2026-08-05)

### Feat

- **controls-ui**: add fan toggle for TEC heaters ([`62b204b`](https://github.com/Blue-Ocean-Technologies-Inc/heater-microdrop-plugin-py/commit/62b204bfa3cf1a34b9e6f3cc8a088513aab871d5))

### Fix

- **controller**: throttle unparsed heater RX logging ([`c64f0a7`](https://github.com/Blue-Ocean-Technologies-Inc/heater-microdrop-plugin-py/commit/c64f0a7b2443e836319e577230aef62edd39ea5a))

## [v1.8.1](https://github.com/Blue-Ocean-Technologies-Inc/heater-microdrop-plugin-py/releases/tag/v1.8.1) (2026-07-24)

### Fix

- **controls-ui**: show board id in the heater dock pane ([`5a45ad5`](https://github.com/Blue-Ocean-Technologies-Inc/heater-microdrop-plugin-py/commit/5a45ad5b0884ab40333e1f70cf8b1d3a14eeebd9))

## [v1.8.0](https://github.com/Blue-Ocean-Technologies-Inc/heater-microdrop-plugin-py/releases/tag/v1.8.0) (2026-07-23)

### Fix

- **firmware-upload**: drop hardcoded dev firmware path ([`7161f02`](https://github.com/Blue-Ocean-Technologies-Inc/heater-microdrop-plugin-py/commit/7161f02a55617fad6e93689c1fa0764af41297e9))

## [v1.7.0](https://github.com/Blue-Ocean-Technologies-Inc/heater-microdrop-plugin-py/releases/tag/v1.7.0) (2026-07-22)

### Feat

- firmware upload via the shared peripheral base ([`a74e9a4`](https://github.com/Blue-Ocean-Technologies-Inc/heater-microdrop-plugin-py/commit/a74e9a42038118630aac0e5bd351d4e8242d84cc))
- **proxy**: publish port on connect and a board-id whoami signal ([`ac6236d`](https://github.com/Blue-Ocean-Technologies-Inc/heater-microdrop-plugin-py/commit/ac6236d073844b1adb2a623fa5a53471b3710505))

## [v1.6.1](https://github.com/Blue-Ocean-Technologies-Inc/heater-microdrop-plugin-py/releases/tag/v1.6.1) (2026-07-15)

## [v1.6.0](https://github.com/Blue-Ocean-Technologies-Inc/heater-microdrop-plugin-py/releases/tag/v1.6.0) (2026-07-14)

### Feat

- **protocol-columns**: Set Temp checkbox to leave the heater untouched ([`b74deee`](https://github.com/Blue-Ocean-Technologies-Inc/heater-microdrop-plugin-py/commit/b74deee57bc05cc921905cfc7c2bbf3bbf13a9e6))

## [v1.5.0](https://github.com/Blue-Ocean-Technologies-Inc/heater-microdrop-plugin-py/releases/tag/v1.5.0) (2026-07-14)

### Feat

- **controls-ui**: own Heater Settings preferences tab ([`4dd9e89`](https://github.com/Blue-Ocean-Technologies-Inc/heater-microdrop-plugin-py/commit/4dd9e89bce22228eed302d9635c0bf55ea4bb13a))

## [v1.4.0](https://github.com/Blue-Ocean-Technologies-Inc/heater-microdrop-plugin-py/releases/tag/v1.4.0) (2026-07-14)

### Feat

- **protocol-columns**: stop stream and PID at protocol end ([`2f202fe`](https://github.com/Blue-Ocean-Technologies-Inc/heater-microdrop-plugin-py/commit/2f202fe678dfcb0cba90c5ba1ad6d34da61be8db))

## [v1.3.0](https://github.com/Blue-Ocean-Technologies-Inc/heater-microdrop-plugin-py/releases/tag/v1.3.0) (2026-07-13)

### Feat

- **plots**: Log Viewer tab for recorded telemetry logs ([`b78c347`](https://github.com/Blue-Ocean-Technologies-Inc/heater-microdrop-plugin-py/commit/b78c347a6de90d18defa3497046b1d83cb506c59))
- **controller**: collect telemetry logs per stream session ([`be9c358`](https://github.com/Blue-Ocean-Technologies-Inc/heater-microdrop-plugin-py/commit/be9c3587320bd9f506eebd603cd4f419a36fa155))

### Refactor

- **plots**: data_changed event replaces log model revision counter ([`01a7b6a`](https://github.com/Blue-Ocean-Technologies-Inc/heater-microdrop-plugin-py/commit/01a7b6a565fb42b82bb18e8051426983cc109750))

## [v1.2.1](https://github.com/Blue-Ocean-Technologies-Inc/heater-microdrop-plugin-py/releases/tag/v1.2.1) (2026-07-08)

### Fix

- ascii arrow in PWM log message ([`1c0bed9`](https://github.com/Blue-Ocean-Technologies-Inc/heater-microdrop-plugin-py/commit/1c0bed9026a382e3c355068c4fa2fdd7418452c9))
- claim only heater-identified ports ([`7d22a53`](https://github.com/Blue-Ocean-Technologies-Inc/heater-microdrop-plugin-py/commit/7d22a53df1ce6aebf53a082e7528a850373860a7))

## [v1.2.0](https://github.com/Blue-Ocean-Technologies-Inc/heater-microdrop-plugin-py/releases/tag/v1.2.0) (2026-07-06)

### Feat

- **plots**: stop button shows play icon + start tooltip while stopped ([`e205b2e`](https://github.com/Blue-Ocean-Technologies-Inc/heater-microdrop-plugin-py/commit/e205b2e8fc6ee2939bfe2dc8eb91a1483041aaa3))
- **plots**: view-only clear button recalibrates axes ([`e863c29`](https://github.com/Blue-Ocean-Technologies-Inc/heater-microdrop-plugin-py/commit/e863c296b208fb320f3921dbae4d45aafb07b4e7))
- **plots**: pause button shows resume icon while paused ([`8387310`](https://github.com/Blue-Ocean-Technologies-Inc/heater-microdrop-plugin-py/commit/8387310b4768ea61a27afb115e1a8bc42c3820ea))

### Fix

- **plots**: disable clear while paused/stopped; polish tooltips + tests ([`70da926`](https://github.com/Blue-Ocean-Technologies-Inc/heater-microdrop-plugin-py/commit/70da926b611fb17afd9616822255f5bb25ad18a1))

## [v1.1.1](https://github.com/Blue-Ocean-Technologies-Inc/heater-microdrop-plugin-py/releases/tag/v1.1.1) (2026-07-06)

### Fix

- **ui**: drop the redundant side label on the PID toggle ([`ef97205`](https://github.com/Blue-Ocean-Technologies-Inc/heater-microdrop-plugin-py/commit/ef972050a310cd2b07178cf3557771ced7763c25))

## [v1.1.0](https://github.com/Blue-Ocean-Technologies-Inc/heater-microdrop-plugin-py/releases/tag/v1.1.0) (2026-07-06)

### Feat

- sensor-group dropdown (legacy UI parity), default all ([`99f9349`](https://github.com/Blue-Ocean-Technologies-Inc/heater-microdrop-plugin-py/commit/99f934991d28adcaa8ac1ff690243e3638f1a97c))
- couple PID-on to Temp mode and gate setpoint publishes on PID state ([`a1ab3cc`](https://github.com/Blue-Ocean-Technologies-Inc/heater-microdrop-plugin-py/commit/a1ab3cc626936c6ac11f28cadb8fb9fcd610a908))
- add dedicated PID control toggle to the control group ([`49e366a`](https://github.com/Blue-Ocean-Technologies-Inc/heater-microdrop-plugin-py/commit/49e366a70642523f16e0872adc1ef35969e2a477))
- publish SET_PID_MODE from a dedicated pid_enabled observer ([`4fb0a12`](https://github.com/Blue-Ocean-Technologies-Inc/heater-microdrop-plugin-py/commit/4fb0a124636f817a00e43d95a30b08a58beb1104))
- add pid_enabled model trait for dedicated PID toggle ([`50c8a0c`](https://github.com/Blue-Ocean-Technologies-Inc/heater-microdrop-plugin-py/commit/50c8a0cb986ce6e433cf6b75bf0dc679e5b6353e))

### Fix

- probe board connection on extra_plugins_loaded; heater-specific log copy ([`b19f832`](https://github.com/Blue-Ocean-Technologies-Inc/heater-microdrop-plugin-py/commit/b19f832d28da9a3383662ff0b9e22be10f0de326))
- **plots**: trim the setpoint series with the rolling window ([`d4b8feb`](https://github.com/Blue-Ocean-Technologies-Inc/heater-microdrop-plugin-py/commit/d4b8feba8646d75e0b218f59e7243a03608adc8f))
- **plots**: dash the setpoint line ([`89b903f`](https://github.com/Blue-Ocean-Technologies-Inc/heater-microdrop-plugin-py/commit/89b903f7b5c26b4e89dc7c59892cee50b52143e4))
- **plots**: sample all frame keys, gap stale series, add setpoint line + duty echo ([`0f15308`](https://github.com/Blue-Ocean-Technologies-Inc/heater-microdrop-plugin-py/commit/0f15308949975e172910da000486b9dadda05a2f))
- match the legacy UI's PID/stream state machine ([`36b9db1`](https://github.com/Blue-Ocean-Technologies-Inc/heater-microdrop-plugin-py/commit/36b9db13febbab567de2572585f3144ebcf2c85d))

### Refactor

- use the utils toggle editors (SlidingToggleEditor / InPlaceToggleEditor) ([`babca02`](https://github.com/Blue-Ocean-Technologies-Inc/heater-microdrop-plugin-py/commit/babca02d2f38a4a0732a9a1b5c3f5995b1202ce6))
- port the legacy UI's start_stream/stop_stream verbatim into the backend ([`2fb781e`](https://github.com/Blue-Ocean-Technologies-Inc/heater-microdrop-plugin-py/commit/2fb781e2189992d203addae20ebfc6cf40524c9c))

## [v1.0.2](https://github.com/Blue-Ocean-Technologies-Inc/heater-microdrop-plugin-py/releases/tag/v1.0.2) (2026-07-06)

### Refactor

- drop redundant version from plugin manifest ([`8b0c90a`](https://github.com/Blue-Ocean-Technologies-Inc/heater-microdrop-plugin-py/commit/8b0c90adcb41af01941bf1f0af27c31c478b0fb2))

## [v1.0.1](https://github.com/Blue-Ocean-Technologies-Inc/heater-microdrop-plugin-py/releases/tag/v1.0.1) (2026-07-03)
