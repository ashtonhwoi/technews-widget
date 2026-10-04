#!/bin/bash
# Start the widget at every login. Undo with uninstall.sh.
# Run from a folder OUTSIDE ~/Desktop, ~/Documents and ~/Downloads: macOS blocks launchd jobs there.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$(command -v python3)"
mkdir -p "$ROOT/02-data" ~/Library/LaunchAgents
CLAUDE_DIR="$(dirname "$(command -v claude 2>/dev/null || echo "$HOME/.local/bin/claude")")"
write() { # label, program arguments xml, extra xml
  cat > ~/Library/LaunchAgents/com.technews.$1.plist <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>Label</key><string>com.technews.$1</string>
<key>ProgramArguments</key><array>$2</array>
<key>EnvironmentVariables</key><dict><key>PATH</key><string>$CLAUDE_DIR:/usr/bin:/bin</string></dict>
<key>RunAtLoad</key><true/>$3
</dict></plist>
PLIST
  launchctl bootout gui/$(id -u)/com.technews.$1 2>/dev/null
  launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.technews.$1.plist
}
write server "<string>$PY</string><string>$ROOT/01-app/serve.py</string>" "<key>KeepAlive</key><true/><key>StandardErrorPath</key><string>$ROOT/02-data/server.log</string>"
write window "<string>$ROOT/01-app/open-window.sh</string>" ""
echo "Installed. The window opens now and at each login."
