"""Chọn PDF roadmap cần chạy."""
import argparse

from kb1.pipeline.config import PDF_DIR


def selected_pdfs(description):
    """Danh sách PDF cần chạy; --only backend,ai-engineer để chạy thử một phần."""
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--only", help="tên file không đuôi, cách nhau bởi dấu phẩy")
    only = parser.parse_args().only
    pdfs = sorted(PDF_DIR.glob("*.pdf"))
    if only:
        wanted = set(only.split(","))
        pdfs = [p for p in pdfs if p.stem in wanted]
        missing = wanted - {p.stem for p in pdfs}
        if missing:
            raise SystemExit(f"Không tìm thấy PDF: {sorted(missing)}")
    return pdfs
