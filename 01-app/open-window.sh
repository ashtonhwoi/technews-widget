#!/bin/bash
# Open the news widget as a small Chrome app window (own profile, so your normal Chrome is untouched).
# Retries because at login the machine is busy and the first launch can silently fail.
HERE="$(cd "$(dirname "$0")" && pwd)"
PORT=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['port'])" "$HERE/config.json")
PROFILE="$HERE/../02-data/chrome-profile"
for i in $(seq 1 60); do curl -s -o /dev/null "http://127.0.0.1:$PORT/" && break; sleep 1; done
for attempt in 1 2 3 4 5 6; do
  pgrep -f "user-data-dir=$PROFILE" >/dev/null && exit 0
  open -na "Google Chrome" --args --app="http://127.0.0.1:$PORT/" --window-size=420,640 --window-position=20,60 \
    --user-data-dir="$PROFILE" --no-first-run --no-default-browser-check
  sleep 10
done
pgrep -f "user-data-dir=$PROFILE" >/dev/null
