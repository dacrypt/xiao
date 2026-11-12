# matterbridge-xiao — Apple Home & Siri for the Xiaomi X20+

A [Matterbridge](https://github.com/Luligu/matterbridge) plugin that exposes the
Xiaomi Robot Vacuum X20+ (`xiaomi.vacuum.c102gl`) as a **Matter robot vacuum**,
so it shows up in the iPhone **Home** app and Siri can clean rooms:

> In the Home app: pick rooms and press ▶️. By voice: Siri in English («Hey Siri, vacuum the kitchen»), or Siri Shortcuts in Spanish (see «Siri in Spanish»).

The X20+ has no Matter firmware and HomeKit has no vacuum service. This plugin
fills the gap. It doesn't talk to the Xiaomi cloud itself: it calls the
`xiao web` REST API on the same Mac, so login, token refresh and the MIoT
mapping all stay in `xiao`.

```
iPhone / HomePod ──Matter (LAN)──▶ Matterbridge + matterbridge-xiao ──HTTP 127.0.0.1:8120──▶ xiao web ──▶ Xiaomi cloud ──▶ X20+
```

## What you get

| Apple Home / Siri | xiao call |
|---|---|
| Start, with no rooms selected ("Clean everywhere") | `POST /api/start` (full house, fan from the clean mode) |
| Start with rooms selected | `POST /api/clean/rooms` |
| Start with a configured zone selected | `POST /api/clean/zone` |
| Return to dock | `POST /api/dock` |
| Pause | `POST /api/stop` (the X20+ has no pause in cloud mode; Resume starts again) |
| Clean mode Vacuum & Mop / Quiet / Turbo | fan `standard` / `silent` / `turbo` |
| Identify / "Play sound" | `POST /api/find` |
| Status, battery, charging, tank alert | `GET /api/status`, polled every 30 s |

Rooms come from `xiao map rooms`: room ID → Matter area ID, and the xiao alias
becomes the name Siri understands. Zones from the plugin config become extra
"rooms". The X20+ can't mix rooms and zones in one job, so if both are
selected, the rooms are cleaned and the zones are skipped (the log says so).

## Requirements

- A Mac that stays on (Matterbridge and `xiao web` run on it), with `xiao`
  configured (`xiao status` works).
- Node.js 22.13+ (or 24 / 26).
- iPhone on **iOS 18.4 or later**. To control the robot away from home and run
  automations, you also need a **home hub** (HomePod / HomePod mini / Apple TV)
  on 18.4+.
- The iPhone and the Mac on the same network when pairing.

## Install (macOS)

From a checkout of this repo:

```bash
uv tool install --force xiao-cli          # or: uv tool install --force --from . xiao-cli
integrations/matterbridge-xiao/scripts/install-macos.sh
```

The script installs Matterbridge globally, builds and installs the plugin, and
creates two LaunchAgents that start at login:

- `com.xiao.web`: `xiao web --port 8120` on 127.0.0.1. Logs go to `~/Library/Logs/xiao-web.log`.
- `com.xiao.matterbridge`: Matterbridge. The UI is at http://127.0.0.1:8283 and logs go to `~/Library/Logs/matterbridge.log`.

If macOS asks whether `node` may accept incoming connections, choose **Allow**.
Matter needs that.

Uninstall with `scripts/install-macos.sh --uninstall`.

## Pair with the iPhone

1. Get the code for the **Aspiradora** node. It is not the "Matterbridge" bridge.
   ```bash
   grep -E "Aspiradora|Manual pairing code|QR Code URL" ~/Library/Logs/matterbridge.log | tail -6
   ```
   You can also open http://127.0.0.1:8283 and click the QR icon of the
   "Aspiradora" device.
2. iPhone → **Home** → **+** → **Add Accessory** → scan the QR code. Or tap
   **More options…** → choose the accessory → enter the 11-digit code.
3. Accept "Uncertified accessory". Pick the room where the dock is.
4. Test it in the Home app: Aspiradora → Habitaciones → Cocina → ▶️.

Don't pair the "Matterbridge" bridge node: it has no devices. Apple Home and
Siri only control robot vacuums that are their **own** Matter node, which is
why the plugin uses Matterbridge "server mode" (`serverMode: true`).

## Configuration

Edit it from the Matterbridge UI (plugin → ⚙️), or in
`~/.matterbridge/matterbridge-xiao.config.json`, then restart:
`launchctl kickstart -k gui/$(id -u)/com.xiao.matterbridge`.

```json
{
  "deviceName": "Aspiradora",
  "url": "http://127.0.0.1:8120",
  "token": "",
  "serverMode": true,
  "pollIntervalSeconds": 30,
  "roomNames": [{ "id": 7, "name": "Cocina nueva" }],
  "zones": [{ "name": "Comedor", "coords": "1000,500,3000,2500" }]
}
```

- **Room names** come from `xiao rooms alias <id> "<nombre>"`. Use `roomNames`
  only to give Siri a different name. Names must be unique.
- **Zones** use the same `x1,y1,x2,y2` millimetres as `xiao clean -z`.
- **Rooms or zones changed?** Restart Matterbridge. Apple Home picks up the new
  list without re-pairing.
- **`token`** is only needed if `xiao web` runs with `--token`. `XIAO_WEB_TOKEN`
  in the environment also works.

## Siri in Spanish

Apple Home's robot-vacuum voice commands only work with Siri in **US English**.
In Spanish, «Oye Siri, limpia la cocina» goes to another device in the "Cocina"
room, such as a light. The Home app itself (buttons, rooms, status) works in any
language. To use your voice in Spanish, generate Siri Shortcuts with
`xiao shortcuts export` (see the main README, "Siri in Spanish").

## Troubleshooting

- **"Not Responding" or "Updating" in Home**: check that both services are
  running (`launchctl list | grep com.xiao`) and that `curl -s
  127.0.0.1:8120/api/status` answers. If you paired the vacuum while it was
  bridged, remove it from Home and pair the *Aspiradora* node again.
- **Siri says it couldn't do it**: the vacuum rejected the command. The reason
  is in `~/Library/Logs/matterbridge.log`. The usual cause is the state-21
  water-tank alert, which Home shows as an error: refill the clean-water tank
  or empty the dirty one.
- **Re-pair from scratch**: remove the accessory in Home, run
  `launchctl bootout gui/$(id -u)/com.xiao.matterbridge`, run
  `matterbridge --factoryreset`, then run the install script again.

## Development

```bash
cd integrations/matterbridge-xiao
npm ci && npm link matterbridge   # Matterbridge must not be a dependency of the plugin
npm test && npm run typecheck && npm run build
```

The logic lives in `src/mapping.ts` (xiao ↔ Matter values), `src/controller.ts`
(command behaviour) and `src/xiaoClient.ts` (REST). None of them import
Matterbridge, so the unit tests run without it. `src/module.ts` is the thin
Matterbridge glue.
