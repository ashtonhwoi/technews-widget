#!/usr/bin/env python3
"""Serve 02-data on 127.0.0.1 and refresh the news every N minutes (also on POST /refresh)."""
import http.server, json, os, subprocess, sys, threading, time

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "02-data")
CFG = json.load(open(os.path.join(HERE, "config.json")))
lock = threading.Lock()


def refresh():
    with lock:
        subprocess.run([sys.executable, os.path.join(HERE, "fetch.py")], timeout=600)


def loop():
    while True:
        time.sleep(CFG["refresh_minutes"] * 60)
        try:
            refresh()
        except Exception as e:
            print("refresh error:", e, file=sys.stderr)


class H(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=DATA, **k)

    def do_POST(self):
        if self.path == "/refresh":
            try:
                refresh()
            except Exception as e:
                print("refresh error:", e, file=sys.stderr)
            self.send_response(204)
        else:
            self.send_response(404)
        self.end_headers()

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    if not os.path.exists(os.path.join(DATA, "index.html")):
        refresh()
    threading.Thread(target=loop, daemon=True).start()
    http.server.ThreadingHTTPServer(("127.0.0.1", CFG["port"]), H).serve_forever()
