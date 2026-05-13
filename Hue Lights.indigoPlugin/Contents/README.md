# Hue Lights — Indigo Plugin

**Version:** 2022.32.82  
**Bundle ID:** `com.nathansheldon.indigoplugin.HueLights`  
**Platform:** macOS · [Indigo Home Automation](https://www.indigodomo.com/) 3.0+

Controls Philips Hue lights, groups, sensors, and switches from Indigo. Supports both classic Hue bridges (API v1) and the Hue Pro Bridge (API v2 with Server-Sent Events).

---

## Requirements

- **macOS** — Monterey 12+ recommended
- **Indigo** — 2022+ (Server API 3.0)
- **Python** — 3 (bundled with Indigo)
- **Hue Bridge** — Classic bridge (API v1) or Pro bridge (API v2)

---

## Installation

1. Double-click the plugin to install.
2. Open plugin preferences and configure your bridge(s).

---

## Supported Bridges

- **Classic Hue Bridge** — API v1, REST polling
- **Hue Pro Bridge** — API v2, real-time Server-Sent Events (SSE), response under 0.5 s

Up to 4 bridges can be configured simultaneously. Each bridge can be individually enabled or disabled in preferences without removing its devices.

---

## Supported Devices

### Lights (auto-created by plugin)

- `hueBulb` — Extended colour light; on/off, dim, RGB, colour temp
- `hueAmbiance` — Colour temperature light; on/off, dim, colour temp
- `hueLightStrips` — Light strips (extended colour); on/off, dim, RGB, colour temp
- `hueLivingColorsBloom` — Colour light; on/off, dim, RGB
- `hueLivingWhites` — Dimmable light; on/off, dim
- `hueOnOffDevice` — On/off plug; on/off only

### Groups

- `hueGroup` — Room, Zone, or Entertainment zone

Group colour/brightness can be calculated in several ways (configurable per group):
- **calculate** — average member light states directly in the plugin
- **readv1** — fetch group state from bridge via API v1
- **compare** — run both and log differences (development/debug)
- **no** — no group state tracking

Zones and Rooms that share lights automatically sync colour temperature bidirectionally.

### Sensors and Switches (auto-created by plugin)

- `hueMotionSensor` — Hue Motion Sensor (motion)
- `hueMotionTemperatureSensor` — Hue Motion Sensor (temperature)
- `hueMotionLightSensor` — Hue Motion Sensor (light level)
- `hueDimmerSwitch` — Hue Dimmer Switch (RWL020/021/022)
- `hueSmartButton` — Hue Smart Button (ROM001)
- `hueTapSwitch` — Hue Tap Switch
- `hueRotaryWallSwitches` — Hue Tap Dial Switch
- `hueRotaryWallRing` — Hue Tap Dial rotary ring
- `hueWallSwitchModule` — Hue Wall Switch Module
- `hueContactSensor` — Hue Secure Contact Sensor
- `runLessWireSwitch` — Friends of Hue switches

### Bridge Device

One Indigo device is auto-created per bridge, exposing 30+ read-only states: light/sensor/switch counts, software update count, Zigbee channel, firmware version, API version, etc.

---

## Device States (lights)

- `onOffState` — On / off
- `brightnessLevel` — 0–100 %
- `lumen` — Calculated lumen output: `int(brightnessLevel × lumenMax / 100 + 0.5)`; 0 when light is off. For `hueGroup` devices this is the **sum** of the `lumen` state of all ON member lights (off lights contribute 0); group `brightnessLevel` % is unchanged.
- `colorMode` — `hs` (colour), `ct` (white), `xy` (extended colour)
- `colorTemp` — Colour temperature in mirek (153–500)
- `whiteTemperature` — Same as colorTemp
- `hue` — Hue 0–360°
- `saturation` — Saturation 0–100 %
- `redLevel` / `greenLevel` / `blueLevel` — RGB 0–100 %
- `online` — Reachable via Zigbee (true/false)
- `effect` — Active effect name
- `id_v1` — Internal bridge v1 path (e.g. `/lights/3`)

**`lumenMax` device property** — configurable per device in the device edit dialog (default: 600). Set this to the manufacturer-rated lumen output at 100% brightness. The `lumen` state is then auto-calculated and updated whenever brightness or on/off state changes.

---

## Actions

### Light and Group actions

- **Turn on / off / toggle** — basic on/off control
- **Set brightness** — 0–100 %, optional ramp rate
- **Set colour temperature** — mirek value, optional ramp rate
- **Set hue and saturation** — optional ramp rate
- **Set RGB** — red/green/blue 0–255
- **Effect** — classic colour loop (v1 bridge)
- **Effect (pro bridge)** — candle, fire, prism, sparkle, opal, glisten, cosmos, sunbeam, enchant, underwater
- **Save / Recall Preset** — store and restore light state
- **Sunrise Timed Effect** *(pro bridge)* — bridge-managed wake-up simulation, 1–60 min

### Scene actions

- **Recall Scene (not pro bridge)** — activate a v1 scene by room/creator
- **Recall Scene (pro bridge)** — activate a v2 scene; optional brightness, ramp rate, and dynamic speed (0.0–1.0)
- **Recall Smart Scene** *(pro bridge)* — activate or deactivate an adaptive smart scene (adjusts to time of day and natural light)

### Sensor actions

- **Enable / disable sensor** — toggle a sensor on the bridge
- **Set sensor offset** — adjust temperature sensor calibration

### Other actions

- **Alert / Breathe** *(pro bridge)* — single blink or 15× breathe cycle
- **Power-On Behaviour** *(pro bridge)* — set what a light does when power is physically restored: last state / safety (1% warm white) / powerfail / custom (on-mode, brightness, colour temp)

---

## Plugins Menu (one-off actions)

All actions above are also available as one-off Plugins menu items for manual use without creating an action group. Menu items include an execute button at the bottom of the dialog.

Additional menu-only utilities:

- **Find new devices** — scan bridge for unregistered devices
- **Create new light devices from bridge** — bulk-create any missing light devices
- **Move device between bridges** — re-assign an Indigo device to a different bridge number
- **Rename Hue device** — rename a device on the bridge
- **Ignore / un-ignore device** — prevent the plugin auto-creating an Indigo device for a Hue device
- **Delete devices** — remove Indigo devices for selected Hue devices
- **Enable / disable sensor** — toggle sensor state on the bridge
- **Print Hue config** — log full bridge data, device list, or network traffic stats to the Indigo log
- **Track specific device** — enable verbose logging for one device (debug)

---

## Plugin Preferences

- **Bridge IP / host** — address for each bridge (1–4)
- **API key** — Hue application key (v1)
- **API v2 key** — client key for SSE stream (pro bridge only)
- **Enable / disable bridge** — pause communication without removing devices
- **Scan interval** — how often to poll the bridge (seconds)
- **SSE reconnect timeout** — re-establish SSE connection if no events received within N seconds
- **Device name prefixes** — customise auto-created device name format per type (light / group / switch / sensor)
- **Debug flags** — per-area verbose logging: `EditSetup`, `SendCommandsToBridge`, `StateChange`, `NewDevice`, `IpChange`, `TrackedDevice`, …

---

## Architecture Notes

- **Single source file** — `Contents/Server Plugin/plugin.py` (~6 800+ lines), one `Plugin` class subclassing `indigo.PluginBase`.
- **Background threads** — SSE listener, API v1 poll loop, offline watchdog, delayed-action queue, save loop.
- **Delayed-action queue** — group colour recalculations are token-debounced; only the newest queued token for a device executes, preventing redundant bridge calls from rapid SSE bursts.
- **Colour math** — `colormath/` module handles RGB↔XY↔colour-temperature conversions; `add_rgb_temp_to_rgb.py` averages mixed RGB + kelvin lamp lists.
- **Persistent state** — not used for lights (bridge is source of truth). Bridge data cached in `allV2Data` / `allV1Data` in-memory dicts and saved to JSON in the Indigo preferences folder on a throttled schedule.
- **No build system / no test framework.** Testing is manual via the Indigo native or web UI. Reload with **Plugins → Reload Plugins**.

---

## Colour Temperature Reference

- 153 mirek — 6 500 K — cool daylight
- 250 mirek — 4 000 K — neutral white
- 366 mirek — 2 700 K — warm white
- 500 mirek — 2 000 K — candlelight

---

## Version History

See `Contents/VERSION_HISTORY.txt` for the full change log.

**Current release — 2022.32.82 (2026-05-13):**
- New `lumen` device state on all dimmer types and groups: lights auto-calculated as `int(brightnessLevel × lumenMax / 100 + 0.5)` (0 when off); groups aggregated as the sum of member lights' `lumen` (off lights contribute 0). Group `brightnessLevel` % is unchanged.
- New `lumenMax` device property in device edit ConfigUI (default 600); configurable per device
- Reformatted plugin XML files (`Actions.xml`, `Devices.xml`, `MenuItems.xml`, `PluginConfig.xml`) for readability — `type=`/`id=` on opening line, remaining attributes one-per-line; no functional change

**Previous release — 2022.31.82 (2026-05-12):**
- Fixed group colour temperature not updating on member lamp ct change
- Fixed `colorMode` never written in V2 SSE path
- Cross-group ct propagation: Zones and Rooms sharing lights now sync bidirectionally
- Fixed `AttributeError: delayedActionThread` during startup
- New actions: dynamic scene speed, power-on behaviour, sunrise timed effect, smart scene recall
