#!/usr/bin/env bash
# Install matterbridge-xiao on macOS and run it (plus `xiao web`) as login services.
#
#   integrations/matterbridge-xiao/scripts/install-macos.sh            # install / upgrade
#   integrations/matterbridge-xiao/scripts/install-macos.sh --uninstall
#
# Creates two LaunchAgents in ~/Library/LaunchAgents:
#   com.xiao.web          → `xiao web --port 8120` on \$XIAO_HOST (default 127.0.0.1; REST API for the plugin)
#   com.xiao.matterbridge → Matterbridge with the plugin; Matter on UDP/TCP 5540+, UI on 127.0.0.1:8283
# Logs: ~/Library/Logs/xiao-web.log and ~/Library/Logs/matterbridge.log
set -euo pipefail

MATTERBRIDGE_VERSION="${MATTERBRIDGE_VERSION:-3.11.2}"
XIAO_PORT="${XIAO_PORT:-8120}"
# XIAO_HOST=0.0.0.0 exposes xiao web to the LAN (needed by Siri Shortcuts); it then requires
# the token saved in config.toml ([web] token) from other machines.
XIAO_HOST="${XIAO_HOST:-127.0.0.1}"
AGENTS="$HOME/Library/LaunchAgents"
LOGS="$HOME/Library/Logs"
PLUGIN_DIR="$(cd "$(dirname "$0")/.." && pwd)"
UID_NUM="$(id -u)"

unload() {
  for label in com.xiao.matterbridge com.xiao.web; do
    launchctl bootout "gui/$UID_NUM/$label" 2>/dev/null || true
    # bootout is asynchronous: wait until the job is gone or bootstrap fails with EIO.
    for _ in $(seq 1 50); do
      launchctl print "gui/$UID_NUM/$label" >/dev/null 2>&1 || break
      sleep 0.2
    done
  done
}

if [[ "${1:-}" == "--uninstall" ]]; then
  unload
  rm -f "$AGENTS/com.xiao.web.plist" "$AGENTS/com.xiao.matterbridge.plist"
  echo "Services removed. Matter pairing data stays in ~/.matterbridge (delete it to forget the pairing)."
  exit 0
fi

NODE="$(command -v node)" || { echo "node (>= 22.13) is required" >&2; exit 1; }
NPM="$(command -v npm)"
XIAO="$(command -v xiao)" || { echo "xiao is required: uv tool install xiao-cli" >&2; exit 1; }
NODE_BIN_DIR="$(dirname "$NODE")"

echo "→ Installing Matterbridge $MATTERBRIDGE_VERSION globally"
"$NPM" install -g --no-audit --no-fund "matterbridge@$MATTERBRIDGE_VERSION" >/dev/null

echo "→ Building and installing matterbridge-xiao"
cd "$PLUGIN_DIR"
"$NPM" ci --no-audit --no-fund >/dev/null
"$NPM" link matterbridge >/dev/null
"$NPM" run build >/dev/null
TARBALL="$("$NPM" pack --silent)"
"$NPM" install -g --no-audit --no-fund "./$TARBALL" >/dev/null
rm -f "$TARBALL"
MATTERBRIDGE="$NODE_BIN_DIR/matterbridge"
"$MATTERBRIDGE" --add matterbridge-xiao --no-ansi >/dev/null

mkdir -p "$AGENTS" "$LOGS"
PATH_ENV="$NODE_BIN_DIR:$(dirname "$XIAO"):/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin"

cat > "$AGENTS/com.xiao.web.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.xiao.web</string>
  <key>ProgramArguments</key><array>
    <string>$XIAO</string><string>web</string><string>--port</string><string>$XIAO_PORT</string><string>--host</string><string>$XIAO_HOST</string>
  </array>
  <key>EnvironmentVariables</key><dict><key>PATH</key><string>$PATH_ENV</string></dict>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>ThrottleInterval</key><integer>10</integer>
  <key>StandardOutPath</key><string>$LOGS/xiao-web.log</string>
  <key>StandardErrorPath</key><string>$LOGS/xiao-web.log</string>
</dict></plist>
EOF

cat > "$AGENTS/com.xiao.matterbridge.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.xiao.matterbridge</string>
  <key>ProgramArguments</key><array>
    <string>$NODE</string><string>$MATTERBRIDGE</string>
    <string>--service</string><string>--nosudo</string><string>--no-ansi</string>
    <string>--bind</string><string>127.0.0.1</string>
  </array>
  <key>EnvironmentVariables</key><dict><key>PATH</key><string>$PATH_ENV</string></dict>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>ThrottleInterval</key><integer>10</integer>
  <key>StandardOutPath</key><string>$LOGS/matterbridge.log</string>
  <key>StandardErrorPath</key><string>$LOGS/matterbridge.log</string>
</dict></plist>
EOF

echo "→ (Re)starting services"
unload
launchctl bootstrap "gui/$UID_NUM" "$AGENTS/com.xiao.web.plist"
launchctl bootstrap "gui/$UID_NUM" "$AGENTS/com.xiao.matterbridge.plist"

cat <<EOF

Done. Next:
  1. Wait ~30 s, then get the pairing code:
       grep -E "Manual pairing code|QR Code URL" "$LOGS/matterbridge.log" | tail -4
     (or open http://127.0.0.1:8283 → the "Aspiradora" device → QR code)
  2. On the iPhone: Home → + → Add Accessory → scan the QR / "More options" → enter the code.
     Pair the *Aspiradora* node, not the "Matterbridge" bridge.
  3. Say: "Oye Siri, limpia la cocina".
EOF
