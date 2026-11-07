 
import json
import re
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from html import unescape

OUTPUT = Path("leads.json")

SOURCES = [
    {
        "name": "Reddit InternationalSchools",
        "url": "https://www.reddit.com/r/Internationalteachers/new/.rss",
    },
    {
        "name": "Reddit StudyAbroad",
        "url": "https://www.reddit.com/r/studyAbroad/new/.rss",
    },
    {
        "name": "Reddit Malaysia",
        "url": "https://www.reddit.com/r/malaysia/new/.rss",
    },
]
COUNTRIES = [
    "马来西亚", "新加坡", "malaysia", "singapore"
]

EDUCATION = [
    "留学", "国际学校", "幼儿园", "小学", "中学",
    "大学", "申请", "学费", "签证", "陪读",
    "择校", "转学", "international school",
    "university", "student visa", "tuition",
    "admission", "school"
]


def clean(text):
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", unescape(text)).strip()


def relevant(text):
    value = text.lower()
    return (
        any(word in value for word in COUNTRIES)
        and any(word in value for word in EDUCATION)
    )


def fetch_rss(source):
    request = urllib.request.Request(
        source["url"],
        headers={"User-Agent": "StudyLeadRadar/1.0"}
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        data = response.read()

    root = ET.fromstring(data)
    results = []

    for item in root.findall(".//item"):
        title = clean(item.findtext("title"))
        description = clean(item.findtext("description"))
        link = (item.findtext("link") or "").strip()
        published = clean(item.findtext("pubDate"))

        if not link or not relevant(title + " " + description):
            continue

        country = (
            "马来西亚"
            if "马来西亚" in (title + description)
            or "malaysia" in (title + description).lower()
            else "新加坡"
        )

        results.append({
            "title": title,
            "description": description[:500],
            "url": link,
            "source": source["name"],
            "country": country,
            "published": published,
            "collected_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "status": "待审核"
        })

    return results


def main():
    existing = []
    if OUTPUT.exists():
        try:
            existing = json.loads(
                OUTPUT.read_text(encoding="utf-8")
            )
        except (ValueError, OSError):
            existing = []

    if not isinstance(existing, list):
        existing = []

    seen = {
        item.get("url")
        for item in existing
        if isinstance(item, dict)
    }

    added = 0

    for source in SOURCES:
        try:
            results = fetch_rss(source)
            print(f"{source['name']}: {len(results)} 条匹配")

            for item in results:
                if item["url"] not in seen:
                    existing.append(item)
                    seen.add(item["url"])
                    added += 1

        except Exception as error:
            print(f"{source['name']} 读取失败: {error}")

    OUTPUT.write_text(
        json.dumps(existing, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"本次新增: {added} 条")
    print(f"累计保存: {len(existing)} 条")


if __name__ == "__main__":
    main()
