"""
Chấm 1 câu trả lời (sau khi đã train).

  python -m src.predict_answer --mode fast --question-id sb-01 --answer "..."
"""

from __future__ import annotations

import argparse
import json

from .scoring import evaluate_by_id


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["fast", "bertscore"], default="fast")
    parser.add_argument("--question-id", required=True)
    parser.add_argument("--answer", default=None)
    parser.add_argument("--interactive", action="store_true")
    parser.add_argument("--model-type", default=None)
    parser.add_argument("--device", default=None)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    if args.interactive or not args.answer:
        print(f"Nhập câu trả lời cho {args.question_id} (Ctrl+D để kết thúc):")
        lines = []
        try:
            while True:
                lines.append(input())
        except EOFError:
            pass
        answer = "\n".join(lines).strip()
    else:
        answer = args.answer

    if not answer:
        raise SystemExit("Câu trả lời trống.")

    result = evaluate_by_id(
        args.question_id,
        answer,
        mode=args.mode,
        model_type=args.model_type,
        device=args.device,
        include_debug=args.debug,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
