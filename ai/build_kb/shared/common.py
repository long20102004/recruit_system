"""Hàm dùng chung cho KB1, KB2 và load_kb.py."""
import json
import re
import sys
import unicodedata

sys.stdout.reconfigure(encoding="utf-8")   # console Windows mặc định cp1252


def norm(text):
    """Chuẩn hoá để so khớp: NFC, chữ thường, gộp khoảng trắng."""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", text)).strip().lower()


def read_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
