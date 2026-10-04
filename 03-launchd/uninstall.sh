#!/bin/bash
for n in server window; do
  launchctl bootout gui/$(id -u)/com.technews.$n 2>/dev/null
  rm -f ~/Library/LaunchAgents/com.technews.$n.plist
done
pkill -f "01-app/serve.py" 2>/dev/null
echo "Removed. Close the window yourself if it is still open."
