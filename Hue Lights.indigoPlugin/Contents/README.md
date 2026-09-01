# Hue Lights — Indigo Plugin

**Version:** 2022.32.112  
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
- `lastBrightness` — last ON brightness (%); holds the last non-zero `brightnessLevel`, so it survives the light being turned off. This is the level used by the *restore last brightness* ON behaviour.
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
- **Device name prefixes** — customise auto-created device name format per type (light / group / switch / sensor)
- **On-command brightness** — what a light/group does on an ON command with no explicit brightness: use a **Default Brightness**, or **restore the last brightness**. Overridable per device (light edit dialog: *standard / a Default Brightness / last brightness*). Applies to both API v1 and v2 (Pro) bridges.
- **Default Brightness (%)** — the plugin-wide Default Brightness value (default **80 %**), used whenever *On-command brightness* resolves to a Default Brightness and the light's **Default Brightness source** is *use plugin default*.
- **Per-device Default Brightness source** *(light edit dialog)* — each dimmable light/group can choose **use plugin default** (the value above) or **manual value** (a level set on that device). Resolution when the ON command uses a Default Brightness: manual value if the source is *manual*, otherwise the plugin-wide value; if neither yields a usable level the light keeps its last brightness.
- **Debug flags** — per-area verbose logging: `EditSetup`, `SendCommandsToBridge`, `StateChange`, `NewDevice`, `IpChange`, `TrackedDevice`, …

### Event-stream restart thresholds *(expert section, Pro bridge)*

- **(main) restart after no events for N s** — `NumberOfSecondsEventRestart`. Drives the TCP keepalive on the SSE socket (the sole failure detector). A genuinely dead connection is detected roughly this many seconds after it drops; the value is baked into the socket when the listener session is created, so changing it restarts the listener (within ~10 s) to pick up the new value.
- **(read-timeout bound) `NumberOfSecondsEventWoMessage`** — no longer restarts the listener. A quiet stream is expected on the Pro bridge and is **not** treated as a failure; this value now only participates in the stream read-timeout ceiling. (Kept for backward compatibility with saved prefs.)

Both defaults and valid ranges live in `kDefaultPluginPrefs` / `minMaxEventRecovery` in the plugin (single source of truth); out-of-range saved values are clamped to the nearest bound on load.

---

## Architecture Notes

- **Single source file** — `Contents/Server Plugin/plugin.py` (~20 000 lines), one `Plugin` class subclassing `indigo.PluginBase`.
- **Background threads** — SSE listener (one per V2 bridge), API v1 poll loop, offline watchdog, delayed-action queue, save loop.
- **Delayed-action queue** — group colour recalculations are token-debounced; only the newest queued token for a device executes, preventing redundant bridge calls from rapid SSE bursts.
- **Colour math** — `colormath/` module handles RGB↔XY↔colour-temperature conversions; `add_rgb_temp_to_rgb.py` averages mixed RGB + kelvin lamp lists.
- **Persistent state** — not used for lights (bridge is source of truth). Bridge data cached in `allV2Data` / `allV1Data` in-memory dicts and saved to JSON in the Indigo preferences folder on a throttled schedule.
- **No build system / no test framework.** Testing is manual via the Indigo native or web UI. Reload with **Plugins → Reload Plugins**.

---

## Event-stream resilience *(Pro bridge, API v2)*

The Hue Pro bridge periodically drops/recycles its long-lived SSE connection (commonly about once an hour). The plugin absorbs this transparently with no data loss:

- **A quiet stream is not a failure** — the Pro bridge legitimately sends no events for long stretches when nothing is changing, so silence never triggers a restart. The listener is torn down only when a genuine socket failure is detected, or when the restart threshold is reconfigured.
- **TCP keepalive** on the stream socket is the sole health check — it lets the OS detect a dead/black-holed connection (inbound-only TLS connections are otherwise dropped silently). Timing is driven by the *(main)* restart threshold.
- **Fresh session per reconnect** — after any stream failure the `requests.Session` is closed and rebuilt (re-installing the keepalive adapter) before the next attempt, so a poisoned pooled TLS/TCP connection is never reused (which could otherwise wedge all further reconnects).
- **Fast reconnect with backoff** — a dropped *working* connection reconnects immediately (0 s); the delay only escalates (2 → 5 → 10 s) if reconnects keep failing (bridge genuinely down).
- **Last-Event-ID replay** — on reconnect the plugin sends the last received event id, so the bridge replays any events buffered during the gap; those are recovered without loss.
- **True outage timing** — the gap is measured from when the connection actually dropped (`disconnectTime`), not from the last Hue event, so a quiet-but-healthy bridge no longer inflates the measured gap.
- **Conditional full re-read** — the whole bridge is re-read to reconcile device states **only on a real outage** (a true gap longer than the assumed replay-buffer window, `kEventReplayWindowSecs` ≈ 300 s); routine recycles need no re-read.
- **Quiet logging** — routine reconnects log at debug level (10); only a gap long enough to risk missed events logs at level 20.
- **Reconnect history** — the last 100 reconnects (time, gap, events recovered, last/first event id) are viewable via **Plugins → Print Hue config → bytes send/received**.

---

## Colour Temperature Reference

- 153 mirek — 6 500 K — cool daylight
- 250 mirek — 4 000 K — neutral white
- 366 mirek — 2 700 K — warm white
- 500 mirek — 2 000 K — candlelight

---

## Version History

See `Contents/VERSION_HISTORY.txt` for the full change log.

**Current release — 2022.32.112 (2026-07-09):**
- **Code audit (.85 → .86):** ~40 correctness bugs fixed across `plugin.py` (Save Preset, scene recall, V2 colour-temperature/brightness, RGB scaling, white-slider hue scaling, inverted button state, motion-area device creation, bridge-move state transfer, and more — see `VERSION_HISTORY.txt`).
- **Event-stream resilience (.87 → .112):** major rework of the V2 SSE listener — see *Event-stream resilience* above. Eliminated an 8-minute restart stall, added TCP keepalive, fast reconnect with backoff, Last-Event-ID replay, conditional re-read only on a real outage, a 100-entry reconnect-history table in print-stats, and near-silent routine logging.
- **Config thresholds:** the SSE restart control was split into two expert-section parameters (main keepalive + fallback watchdog) with configurable ranges; changes now apply live (within ~10 s) without a plugin reload.
- **Refactors:** config-parameter defaults consolidated into `kDefaultPluginPrefs` (single source of truth); duplicated pref-reading collapsed into `readEventTimerPrefs` / `applyGeneralPrefs`.

**Earlier — 2022.32.82 (2026-05-13):**
- New `lumen` device state on all dimmer types and groups; new `lumenMax` device property (default 600)
- Reformatted plugin XML files for readability (no functional change)
- New actions: dynamic scene speed, power-on behaviour, sunrise timed effect, smart scene recall
