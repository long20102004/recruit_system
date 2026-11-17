"""Bước 1: khảo sát màu ô, cỡ chữ và vẽ khung nhận diện lên ảnh để kiểm bằng mắt."""
import collections

import pymupdf

from kb1.pipeline.pdfs import selected_pdfs
from kb1.pipeline.config import OUT

SURVEY = OUT / "survey"


def main():
    SURVEY.mkdir(parents=True, exist_ok=True)
    for pdf in selected_pdfs(__doc__):
        doc = pymupdf.open(pdf)
        page = doc[0]
        spans = [s for b in page.get_text("dict")["blocks"] for l in b.get("lines", [])
                 for s in l["spans"] if s["text"].strip()]
        boxes = [d for d in page.get_drawings()
                 if d.get("fill") and d["rect"].width > 20 and d["rect"].height > 10]
        fills = collections.Counter(tuple(round(c, 2) for c in d["fill"]) for d in boxes)
        sizes = collections.Counter(round(s["size"], 1) for s in spans)
        print(f"{pdf.name}: {len(doc)} trang, {len(spans)} khối chữ, {len(boxes)} ô | "
              f"màu ô: {fills.most_common(4)} | cỡ chữ: {sizes.most_common(4)}")

        for d in boxes:
            page.draw_rect(d["rect"], color=(1, 0, 0), width=0.6)
        for s in spans:
            page.draw_rect(pymupdf.Rect(s["bbox"]), color=(0, 0, 1), width=0.3)
        page.get_pixmap(dpi=60).save(SURVEY / f"{pdf.stem}.png")


if __name__ == "__main__":
    main()
