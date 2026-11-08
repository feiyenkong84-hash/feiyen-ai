"""Collect public education questions; never bypass access restrictions."""
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from html import unescape
from pathlib import Path

# Public, native Atom feeds. Live availability must be checked in the runner.
# Stack Exchange content requires attribution; retain original links and authors.
SOURCES = [
    {"name": f"Stack Exchange Expatriates / {country}",
     "url": f"https://expatriates.stackexchange.com/feeds/tag?tagnames={country}&sort=newest"}
    for country in ("malaysia", "singapore")
]
COUNTRIES = {"马来西亚": ("马来西亚", "malaysia"), "新加坡": ("新加坡", "singapore")}
EDUCATION = ("留学", "国际学校", "幼儿园", "小学", "中学", "大学", "陪读", "择校", "转学",
             "international school", "university", "student visa", "tuition", "admission", "school", "studying", "study abroad", "student pass")
ATOM = "{http://www.w3.org/2005/Atom}"


def clean(text):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", unescape(text or ""))).strip()


def relevant(text):
    value = text.lower()
    return any(w in value for words in COUNTRIES.values() for w in words) and any(w in value for w in EDUCATION)


def canonical_url(url):
    parts = urllib.parse.urlsplit(url.strip())
    if parts.scheme not in ("http", "https") or not parts.netloc:
        raise ValueError("entry has no valid original HTTP(S) link")
    return urllib.parse.urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path, parts.query, ""))


def parse_feed(data, source):
    root = ET.fromstring(data)
    if root.tag == ATOM + "feed":
        items = root.findall(ATOM + "entry")
        atom = True
    elif root.tag == "rss" and root.find("channel") is not None:
        items = root.findall("./channel/item")
        atom = False
    else:
        raise ValueError(f"unsupported feed root: {root.tag}")
    results = []
    for item in items:
        prefix = ATOM if atom else ""
        title = clean(item.findtext(prefix + "title"))
        description = clean(item.findtext(prefix + ("content" if atom else "description")) or item.findtext(prefix + "summary"))
        if atom:
            links = [e.get("href", "") for e in item.findall(ATOM + "link") if e.get("rel", "alternate") == "alternate"]
            link = links[0] if links else ""
        else:
            link = item.findtext("link") or ""
        text = title + " " + description
        if not relevant(text):
            continue
        link = canonical_url(link)
        countries = [name for name, words in COUNTRIES.items() if any(w in text.lower() for w in words)]
        results.append({"title": title, "description": description[:500], "url": link,
                        "source": source["name"], "country": countries[0],
                        "published": clean(item.findtext(prefix + ("published" if atom else "pubDate")) or item.findtext(prefix + "updated")),
                        "author": clean(item.findtext(ATOM + "author/" + ATOM + "name") if atom else item.findtext("author")),
                        "collected_at": datetime.now(timezone.utc).isoformat(), "status": "待审核"})
    return results, len(items)


def fetch_rss(source):
    request = urllib.request.Request(source["url"], headers={"User-Agent": "StudyLeadRadar/1.0 (public RSS reader)", "Accept": "application/atom+xml, application/rss+xml, application/xml"})
    with urllib.request.urlopen(request, timeout=20) as response:
        data = response.read(5_000_001)
    if len(data) > 5_000_000:
        raise ValueError("feed exceeds 5 MB limit")
    return parse_feed(data, source)


def atomic_json(path, data):
    tmp = path.with_name(path.name + ".tmp")
    try:
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def collect(sources, output, report_path):
    # Invalid history is a hard failure, never silently replaced by an empty list.
    existing = json.loads(output.read_text(encoding="utf-8")) if output.exists() else []
    if not isinstance(existing, list) or any(not isinstance(x, dict) or not isinstance(x.get("url"), str) for x in existing):
        raise ValueError("existing leads must be an array of objects with URL strings")
    seen = {canonical_url(x["url"]) for x in existing}
    report = {"collected_at": datetime.now(timezone.utc).isoformat(), "sources": [], "added": 0}
    for source in sources:
        entry = {"name": source["name"], "url": source["url"]}
        try:
            results, scanned = fetch_rss(source)
            entry.update(status="success", scanned=scanned, matched=len(results), added=0)
            for item in results:
                if item["url"] not in seen:
                    existing.append(item)
                    seen.add(item["url"])
                    entry["added"] += 1
                    report["added"] += 1
        except (urllib.error.URLError, TimeoutError, OSError, ValueError, ET.ParseError) as error:
            entry.update(status="failed", error=str(error))
        report["sources"].append(entry)
        print(json.dumps(entry, ensure_ascii=False))
    failures = sum(x["status"] == "failed" for x in report["sources"])
    report["status"] = "failed" if failures == len(sources) else "partial_failure" if failures else "success"
    report["total"] = len(existing)
    if report["added"]:
        atomic_json(output, existing)
    atomic_json(report_path, report)
    print(json.dumps({k: v for k, v in report.items() if k != "sources"}, ensure_ascii=False))
    return 1 if failures else 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("leads.json"))
    parser.add_argument("--report", type=Path, default=Path("collection-report.json"))
    args = parser.parse_args()
    try:
        return collect(SOURCES, args.output, args.report)
    except (OSError, ValueError) as error:
        print(f"Collection aborted; existing data preserved: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
