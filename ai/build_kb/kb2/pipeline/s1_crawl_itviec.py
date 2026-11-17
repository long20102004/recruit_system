"""KB2, bước 1: lấy danh sách chức danh của ITviec (bản Việt và bản Anh) về kb2/data/itviec_titles_raw.csv.

Hai bản sắp theo bảng chữ cái của từng ngôn ngữ và slug khác nhau, nên không ghép được theo vị trí.
Cặp Việt - Anh nằm ở kb2/data/itviec_title_map.csv, s2_titles.py đối chiếu bảng đó với file này.
"""
import csv
import html
import re
import time

import requests

from kb2.pipeline.config import ITVIEC_PAGES, TITLES_RAW_CSV

FIELDS = ["lang", "group", "name", "url"]
ITEM_RE = r"head-divider-text[^>]*>([^<]+)<|skill-tag-link[^>]*href=\"([^\"]+)\"[^>]*>([^<]+)<"
USER_AGENT = "Mozilla/5.0 (compatible; recruit-kb-research/0.1)"


def parse_titles(page, lang):
    """Trả các dòng {lang, group, name, url} theo thứ tự trên trang."""
    rows, group = [], None
    for heading, url, name in re.findall(ITEM_RE, page[page.find("job-expertise-index-headline"):]):
        if heading:
            group = html.unescape(heading).strip()
        else:
            rows.append({"lang": lang, "group": group, "name": html.unescape(name).strip(), "url": url})
    return rows


def main():
    rows = []
    for lang, url in ITVIEC_PAGES.items():
        response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
        response.raise_for_status()
        found = parse_titles(response.text, lang)
        if not found:
            raise SystemExit(f"Không thấy chức danh ở {url}: có thể trang đã đổi cấu trúc")
        print(f"{lang}: {len(found)} chức danh")
        rows += found
        time.sleep(2)
    with open(TITLES_RAW_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
