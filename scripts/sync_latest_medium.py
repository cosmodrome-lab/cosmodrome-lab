#!/usr/bin/env python3

import html
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

FEED_URL = "https://medium.com/feed/@Cosmodrome-eng."
README_FILE = Path("README.md")
START_MARKER = "<!-- LATEST_MEDIUM_START -->"
END_MARKER = "<!-- LATEST_MEDIUM_END -->"
CONTENT_NAMESPACE = "{http://purl.org/rss/1.0/modules/content/}encoded"


def clean_url(url: str) -> str:
    return html.unescape(url.strip()).split("?", 1)[0]


def get_latest_publication() -> tuple[str, str, str, str]:
    request = urllib.request.Request(
        FEED_URL,
        headers={"User-Agent": "COSMODROME-Latest-Research/1.0"},
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        root = ET.fromstring(response.read())

    item = root.find("./channel/item")

    if item is None:
        raise RuntimeError("Medium RSS contains no publications")

    title = item.findtext("title", "").strip()
    link = clean_url(item.findtext("link", ""))
    published = item.findtext("pubDate", "").strip()
    content = item.findtext(CONTENT_NAMESPACE, "")

    images = re.findall(
        r'<img[^>]+src=["\']([^"\']+)["\']',
        content,
        flags=re.IGNORECASE,
    )
    image = next(
        (
            clean_url(candidate)
            for candidate in images
            if "cdn-images" in candidate or "miro.medium.com" in candidate
        ),
        "",
    )

    if not title or not link or not published or not image:
        raise RuntimeError(
            "Medium RSS publication is missing required fields"
        )

    date = parsedate_to_datetime(published).astimezone(timezone.utc)
    display_date = f"{date.strftime('%B')} {date.day}, {date.year}"

    return title, link, image, display_date


def build_block(
    title: str,
    link: str,
    image: str,
    date: str,
) -> str:
    safe_alt = html.escape(title, quote=True)
    safe_title = title.replace("[", r"\[").replace("]", r"\]")

    return "\n".join(
        [
            START_MARKER,
            f'<a href="{link}">',
            f'  <img src="{image}" alt="{safe_alt}" width="720">',
            "</a>",
            "",
            f"### [{safe_title}]({link})",
            "",
            f"*Published {date}*",
            END_MARKER,
        ]
    )


def main() -> None:
    readme = README_FILE.read_text(encoding="utf-8")

    if START_MARKER not in readme or END_MARKER not in readme:
        raise RuntimeError(
            "Latest Research markers not found in README.md"
        )

    title, link, image, date = get_latest_publication()
    replacement = build_block(title, link, image, date)

    pattern = re.compile(
        re.escape(START_MARKER)
        + ".*?"
        + re.escape(END_MARKER),
        flags=re.DOTALL,
    )
    updated, count = pattern.subn(
        replacement,
        readme,
        count=1,
    )

    if count != 1:
        raise RuntimeError(
            "Latest Research block replacement failed"
        )

    if updated != readme:
        README_FILE.write_text(updated, encoding="utf-8")


if __name__ == "__main__":
    main()
