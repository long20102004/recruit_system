#!/usr/bin/env python3
"""
Lấy toàn bộ tag synonyms (Active) của Stack Overflow -> CSV 2 cột: synonym, target.

Dùng Stack Exchange API chính thức (ổn định hơn parse HTML).
Cài: pip install requests
Chạy: python -m kb1.pipeline.so_tag_synonyms --key YOUR_API_KEY   -> ghi ra kb1/data/tag_synonyms.csv
(Cần key: không có key thì API chỉ cho tới trang 25, tức 2.500 dòng.
 Đăng ký key miễn phí tại https://stackapps.com/apps/oauth/register)
"""
import argparse
import csv
import pathlib
import sys
import time

import requests

API = "https://api.stackexchange.com/2.3/tags/synonyms"
DEFAULT_OUTPUT = pathlib.Path(__file__).resolve().parents[1] / "data" / "tag_synonyms.csv"


def fetch_all(site="stackoverflow", key=None):
    params = {
        "site": site,
        "order": "desc",
        "sort": "creation",   # giống tab "Newest" trên web
        "pagesize": 100,      # tối đa API cho phép
        "page": 1,
    }
    if key:
        params["key"] = key

    session = requests.Session()
    while True:
        r = session.get(API, params=params, timeout=30)
        data = r.json()
        if "error_id" in data:
            sys.exit(f"API error {data['error_id']}: {data.get('error_message')}")

        for item in data.get("items", []):
            yield item["from_tag"], item["to_tag"]

        print(f"Trang {params['page']} xong, quota còn {data.get('quota_remaining')}",
              file=sys.stderr)

        if not data.get("has_more"):
            break
        # API yêu cầu tôn trọng 'backoff' nếu có
        time.sleep(data.get("backoff", 0) or 0.2)
        params["page"] += 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("output", nargs="?", default=DEFAULT_OUTPUT)
    ap.add_argument("--key", help="Stack Exchange API key (tuỳ chọn)")
    ap.add_argument("--site", default="stackoverflow")
    args = ap.parse_args()

    count = 0
    with open(args.output, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["synonym", "target"])
        for synonym, target in fetch_all(args.site, args.key):
            w.writerow([synonym, target])
            count += 1

    print(f"Đã ghi {count} dòng vào {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()