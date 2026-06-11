# Link-Tap Domoticz Plugin — English Documentation

## Overview

[Link-Tap](https://www.link-tap.com/) is a wireless smart watering system controlled through a cloud service. This Domoticz plugin connects your Link-Tap installation to [Domoticz](https://www.domoticz.com) via the official Link-Tap REST API, letting you monitor and control your watering directly from your home automation system.

---

## Features

- Reads real-time flow rate and cumulative volume during active watering cycles
- Controls the watering mode (Intervals, Odd/Even, Seven Days, Month)
- Turns watering On or Off immediately in instant mode
- Displays hardware alerts (fall detection, no water, leak, clog, broken valve)
- Reports battery level and wireless signal strength for each device
- Automatic version check against the GitHub release page
- **Bilingual UI**: log messages and status strings follow the language configured in Domoticz (English and French included; additional languages can be added easily)

---

## Requirements

- Domoticz with Python plugin support enabled
- A Link-Tap account with at least one Gateway and one Taplinker
- An API key generated on the [Link-Tap developer page](https://www.link-tap.com/#!/api-for-developers)
- Python `requests` library (usually already present on Domoticz hosts)

---

## Installation

1. Clone or download this repository into your Domoticz plugins directory:
   ```
   cd /opt/domoticz/plugins          # adjust path to your installation
   git clone https://github.com/DebugBill/Link-Tap
   ```
2. Restart Domoticz.
3. Go to **Setup → Hardware**, click **Add**, and select **Link-Tap Watering System** from the dropdown.

---

## Configuration

| Parameter | Description |
|-----------|-------------|
| **User** | Your Link-Tap account username (email address) |
| **Key** | Your Link-Tap API key |
| **Return to previous mode after manual** | When `True`, the controller reverts to the scheduled programme once a manual watering session ends |
| **Maximum watering duration (sec)** | Safety cut-off applied when turning watering On manually (1–1439 s, default 1439) |
| **Debug Level** | Verbosity of Domoticz log output (set to *None* for normal use) |

---

## Devices created

Five Domoticz devices are created automatically for **each Taplinker** found on your account (up to the Domoticz limit of 255 devices per hardware entry):

| Device | Type | Description |
|--------|------|-------------|
| **Flow** | Custom Sensor | Instantaneous flow rate in l/min during active watering |
| **Volume** | Custom Sensor | Cumulative volume (litres) for the current watering session |
| **Watering Modes** | Selector Switch | Activate a scheduled programme: Intervals / Odd-Even / Seven Days / Month |
| **Status** | Alert | Green when idle, Red when a hardware fault is detected (see alert list below) |
| **On/Off** | Switch | Start or stop watering immediately in instant mode |

### Alert conditions reported on the Status device

- Fall detected (device knocked over)
- No water supply
- Leak detected
- Pipe clogged
- Valve broken

---

## Update frequency

| Data | Interval |
|------|----------|
| Watering status (flow, volume, On/Off sync) | 30 seconds |
| Device list refresh (new hardware detection) | 5 minutes |
| Version check (GitHub) | 2 hours |

> Link-Tap enforces rate limiting on its API. Do not reduce the heartbeat interval below 15 seconds.

---

## Automatic version check

Every two hours the plugin queries the [GitHub releases page](https://github.com/DebugBill/Link-Tap/releases/latest) and compares the latest published tag against the running version using **numeric comparison** (e.g. `2.1 > 2.00 > 0.2`):

| Situation | Log level | Message |
|-----------|-----------|---------|
| GitHub has a newer release | `Error` | Update available notice |
| Local version equals latest release | `Log` | Up to date |
| Local version is ahead of latest release | `Log` | Development build notice (no alert) |

The "ahead" case is intentional: during development the running plugin may carry a version number not yet published on GitHub, which should not generate a spurious update alert.

---

## Adding a new language

All user-visible strings are stored in the `STRINGS` dictionary at the top of `plugin.py`. To add a language:

1. Copy the entire `'en'` block.
2. Change the key to the ISO 639-1 code of your language (e.g. `'de'` for German).
3. Translate each value string. Use the same `{placeholder}` tokens — they are filled in at runtime.
4. The plugin automatically selects the language configured in Domoticz (`Setup → Settings → Language`). English is used as a fallback for any missing key.

---

## Changelog

| Version | Date | Notes |
|---------|------|-------|
| 2.00 | 2026 | Bug fixes (boolean condition, dead code, `autoBack` type, HTTP error handling), bilingual EN/FR support, code refactoring, intelligent numeric version comparison (no false alert when running a development build ahead of the latest release) |
| 0.2 | 2024-05 | Better handling of status device updates |
| 0.1 | 2021-06 | Initial release |

---

## Known limitations

- The plugin polls the Link-Tap cloud API. It requires an active internet connection at all times.
- Domoticz limits hardware entries to 255 devices. With many Taplinkers (> 51) you may need multiple hardware entries — this is not currently supported automatically.

---

## Author

**DebugBill** — <DebugBill@thauvin.org>

## License

This project is licensed under the **GNU General Public License v3.0 (GPL-3.0)**.
You are free to use, modify and redistribute it under the terms of that licence.
See [https://www.gnu.org/licenses/gpl-3.0.html](https://www.gnu.org/licenses/gpl-3.0.html) for the full text.
