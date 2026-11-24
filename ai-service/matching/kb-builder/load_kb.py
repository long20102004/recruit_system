"""Giữ lệnh cũ: gộp mọi gói trong packs/ bằng thư ký chung (kb_pipeline) rồi nạp Neo4j.

Chạy: python load_kb.py               gộp, ghi out/, nạp Neo4j   (= python -m kb_pipeline --load)
      python load_kb.py --merge-only  chỉ gộp, kiểm, ghi out/   (= python -m kb_pipeline)

Trước khi gộp, mỗi nguồn phải tự đóng gói: kb1.pipeline.s7_pack, kb2.pipeline.s5_pack, kb3.pipeline.build.
"""
import argparse

from kb_pipeline.__main__ import main as pipeline_main


def main():
    parser = argparse.ArgumentParser(description="Gộp mọi gói rồi nạp vào Neo4j")
    parser.add_argument("--merge-only", action="store_true", help="chỉ gộp và kiểm tra, không nạp")
    pipeline_main([] if parser.parse_args().merge_only else ["--load"])


if __name__ == "__main__":
    main()
