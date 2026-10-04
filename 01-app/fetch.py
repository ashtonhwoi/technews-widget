#!/usr/bin/env python3
"""Fetch tech news from Google News RSS, summarise with `claude -p`, write 02-data/index.html."""
import html, json, os, re, subprocess, sys, tempfile, time, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "02-data")
CFG = json.load(open(os.path.join(HERE, "config.json")))
CACHE = os.path.join(DATA, "summaries.json")
STATE = os.path.join(DATA, "news.json")
CLAUDE = __import__("shutil").which("claude") or os.path.expanduser("~/.local/bin/claude")
STOP = set("the a an of to in on for and with as at by from is are be its it this that new says say after over amid".split())


def load(path, default):
    try:
        return json.load(open(path))
    except Exception:
        return default


def atomic_write(path, text):
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path))
    with os.fdopen(fd, "w") as f:
        f.write(text)
    os.replace(tmp, path)


def fetch_company(co):
    out, errs = [], 0
    for hl, gl, ceid in CFG["editions"]:
        q = urllib.parse.quote(f'{co["query"]} when:2d')
        url = f"https://news.google.com/rss/search?q={q}&hl={hl}&gl={gl}&ceid={ceid}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            root = ET.fromstring(urllib.request.urlopen(req, timeout=20).read())
        except Exception:
            errs += 1
            continue
        out += parse_items(root, co)
    if errs == len(CFG["editions"]):
        raise RuntimeError("all editions failed")
    out.sort(key=lambda s: -s["ts"])
    return out


def parse_items(root, co):
    out = []
    for it in root.iter("item"):
        title = html.unescape(it.findtext("title") or "")
        src_el = it.find("source")
        source = src_el.text if src_el is not None else ""
        if source and title.endswith(" - " + source):
            title = title[: -len(source) - 3]
        try:
            ts = parsedate_to_datetime(it.findtext("pubDate")).astimezone(timezone.utc).timestamp()
        except Exception:
            continue
        if time.time() - ts > CFG["max_age_hours"] * 3600:
            continue
        low = title.lower()
        if not any(m in low for m in co["must"]) or any(b in low for b in CFG["block_words"]):
            continue
        out.append({"title": title.strip(), "link": it.findtext("link"), "source": source, "ts": ts})
    return out


def toks(t):
    return {w for w in re.findall(r"[a-z0-9]+", t.lower()) if w not in STOP}


def dedupe(stories, seen_links, limit):
    kept = []
    for s in stories:
        if s["link"] in seen_links:
            continue
        a = toks(s["title"])
        if any(len(a & toks(k["title"])) / max(1, len(a | toks(k["title"]))) > 0.35 for k in kept):
            continue
        kept.append(s)
        if len(kept) == limit:
            break
    return kept


def summarise(stories, cache):
    todo = [s for s in stories if s["link"] not in cache]
    if not todo:
        return
    items = [{"id": i, "company": s["company"], "headline": s["title"], "source": s["source"]} for i, s in enumerate(todo)]
    prompt = (
        "You write one-glance news blurbs. For each item below, write a summary of 1-3 short lines "
        "(max 40 words) in plain English, facts only, no hype, no opinion, no 'this article'. "
        "You only have the headline, so state only what the headline supports; never add details. "
        "If the headline is too vague, restate it in plain words in one line. "
        'Reply with ONLY a JSON object mapping each id (as a string) to its summary string.\n\n'
        + json.dumps(items, ensure_ascii=False)
    )
    r = subprocess.run([CLAUDE, "-p", "--model", "haiku", prompt], capture_output=True, text=True, timeout=240)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[:300] or "claude -p failed")
    m = re.search(r"\{.*\}", r.stdout, re.S)
    got = json.loads(m.group(0))
    for i, s in enumerate(todo):
        v = got.get(str(i))
        if isinstance(v, str) and v.strip():
            cache[s["link"]] = v.strip()


def render(state):
    def age(ts):
        h = (time.time() - ts) / 3600
        return f"{int(h * 60)}m ago" if h < 1 else f"{int(h)}h ago"

    parts = []
    for c in state["companies"]:
        parts.append(f'<section><h2>{html.escape(c["name"])}</h2>')
        if not c["stories"]:
            parts.append('<p class="none">Nothing new</p>')
        for s in c["stories"]:
            parts.append(
                f'<article><p class="sum">{html.escape(s["summary"])}</p>'
                f'<a href="{html.escape(s["link"])}" target="_blank">{html.escape(s["source"])}</a>'
                f'<span class="age"> · {age(s["ts"])}</span></article>'
            )
        parts.append("</section>")
    updated = datetime.fromtimestamp(state["updated"]).strftime("%H:%M %d %b")
    stale = '<span class="stale">stale: last fetch failed</span>' if state.get("stale") else ""
    tpl = open(os.path.join(HERE, "template.html")).read()
    page = tpl.replace("{{BODY}}", "\n".join(parts)).replace("{{UPDATED}}", updated).replace("{{STALE}}", stale)
    page = page.replace("{{REFRESH}}", str(CFG["refresh_page_seconds"]))
    atomic_write(os.path.join(DATA, "index.html"), page)


def main():
    os.makedirs(DATA, exist_ok=True)
    cache = load(CACHE, {})
    prev = load(STATE, None)
    try:
        seen, collected, ok = set(), {}, 0
        for co in CFG["companies"]:
            name = co["name"]
            try:
                collected[name] = dedupe(fetch_company(co), seen, CFG["stories_per_company"])
                ok += 1
            except Exception as e:
                print(f"fetch failed for {name}: {e}", file=sys.stderr)
                collected[name] = None
            for s in collected[name] or []:
                seen.add(s["link"])
        if ok == 0:
            raise RuntimeError("no company could be fetched")
        flat = [dict(s, company=n) for n, ss in collected.items() for s in ss or []]
        summarise(flat, cache)
        atomic_write(CACHE, json.dumps(cache))
        companies = []
        for n in [c["name"] for c in CFG["companies"]]:
            if collected[n] is None:  # fetch failed: keep the previous stories for this company
                old = next((c for c in (prev or {}).get("companies", []) if c["name"] == n), None)
                companies.append(old or {"name": n, "stories": []})
                continue
            stories = [dict(s, summary=cache[s["link"]]) for s in collected[n] if s["link"] in cache]
            companies.append({"name": n, "stories": stories})
        state = {"updated": time.time(), "stale": False, "companies": companies}
    except Exception as e:
        print(f"refresh failed, keeping last data: {e}", file=sys.stderr)
        if not prev:
            sys.exit(1)
        state = dict(prev, stale=True)
    atomic_write(STATE, json.dumps(state))
    render(state)
    print("ok", sum(len(c["stories"]) for c in state["companies"]), "stories")


if __name__ == "__main__":
    main()
