"""Bước 4: gán mỗi nhãn một loại technology / concept / category / not_skill.

Rẻ trước, đắt sau: luật, rồi LLM. Tầng từ điển chưa có vì KB2 chưa được xây.
Cache theo nhãn ở kb1/out/label_cache.json nên chạy lại không gọi LLM lần nữa.
LLM gọi qua Groq (API tương thích OpenAI), đọc groq_api_key và model từ .env.
Không có key thì phần nhãn còn lại nhận loại unknown và Bước 5 bỏ qua chúng.
"""
import collections
import csv
import json
import os
import random
import re

from dotenv import load_dotenv
from openai import BadRequestError, OpenAI, RateLimitError

from shared.common import norm, read_jsonl, write_jsonl
from kb1.pipeline.config import (
    GOLD_LABEL_SAMPLE, GOLD_SEED, GROQ_BASE_URL, GROQ_DEFAULT_MODEL, LABEL_TYPES, LLM_BATCH,
    LLM_MAX_RETRIES, LLM_PARAMS, NOT_SKILL_PATTERNS, OUT, ROOT,
)

CACHE = OUT / "label_cache.json"

SYSTEM = """Bạn phân loại nhãn trong sơ đồ lộ trình nghề IT. Mỗi nhãn nhận ĐÚNG MỘT loại:
technology (công cụ/ngôn ngữ/framework/dịch vụ cụ thể có tên riêng),
concept (kỹ thuật/khái niệm chuyên môn có thể ghi trong CV, ví dụ RAG, REST, CI/CD),
category (tên một nhóm gồm nhiều mục), not_skill (câu hỏi, lời khuyên, mục giới thiệu).
Chỉ dùng nhãn và nhãn cha được cho. Trả JSON: {"items":[{"id":"...","type":"...","canonical":"..."}]}
canonical: tên chuẩn ngắn gọn của kỹ năng (bỏ chữ thừa như 'API', 'SDK' chỉ khi đó không phải tên riêng); để trống nếu not_skill."""


def rule_type(label):
    """Trả not_skill nếu nhãn khớp luật, ngược lại None."""
    if any(re.search(p, label, re.I) for p in NOT_SKILL_PATTERNS):
        return "not_skill"
    return None


def validate(batch_ids, result):
    """Tách kết quả hợp lệ và các id thiếu hoặc sai loại."""
    items = {str(i.get("id")): i for i in result.get("items", []) if isinstance(i, dict)}
    ok = {i: items[i] for i in batch_ids if i in items and items[i].get("type") in LABEL_TYPES}
    return ok, set(batch_ids) - set(ok)


def ask_llm(client, model, batch):
    """batch: {id: {label, parents}}. Đầu ra không phải JSON hợp lệ thì coi như lô trống."""
    payload = [{"id": i, "label": v["label"], "parents": v["parents"]} for i, v in batch.items()]
    try:
        response = client.chat.completions.create(
            model=model, response_format={"type": "json_object"}, **LLM_PARAMS,
            messages=[{"role": "system", "content": SYSTEM},
                      {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}])
        return json.loads(response.choices[0].message.content)
    except (BadRequestError, json.JSONDecodeError) as error:
        print(f"  [cảnh báo] lô lỗi: {str(error)[:150]}")
        return {}


def classify_with_llm(todo, cache):
    """Gọi LLM theo lô; id thiếu được gọi lại một lần. Ghi cache sau mỗi lô.

    Client tự chờ theo retry-after khi vượt giới hạn token/phút. Vẫn bị chặn sau LLM_MAX_RETRIES lần
    thì dừng; chạy lại script sẽ tiếp tục từ cache.
    """
    client = OpenAI(api_key=os.getenv("groq_api_key"), base_url=GROQ_BASE_URL,
                    max_retries=LLM_MAX_RETRIES)
    model = os.getenv("model", GROQ_DEFAULT_MODEL)
    keys = sorted(todo)
    for start in range(0, len(keys), LLM_BATCH):
        chunk = keys[start:start + LLM_BATCH]
        ids = {str(n): key for n, key in enumerate(chunk)}
        batch = {i: todo[key] for i, key in ids.items()}
        try:
            ok, missing = validate(list(batch), ask_llm(client, model, batch))
            if missing:
                retry, missing = validate(sorted(missing), ask_llm(client, model, {i: batch[i] for i in missing}))
                ok.update(retry)
        except RateLimitError as error:
            print(f"[dừng] Hết hạn mức Groq, chạy lại sau để tiếp tục từ cache: {str(error)[:200]}")
            return
        for i, item in ok.items():
            cache[ids[i]] = {"type": item["type"], "canonical": (item.get("canonical") or "").strip()}
        CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=0), encoding="utf-8")
        print(f"  lô {start // LLM_BATCH + 1}: {len(ok)}/{len(chunk)} nhãn hợp lệ", flush=True)


def collect_labels():
    """Nhãn duy nhất theo dạng chuẩn hoá, kèm các nhãn cha làm ngữ cảnh."""
    labels = {}
    for n in read_jsonl(OUT / "nodes_grouped.jsonl"):
        if n["kind"] in ("main", "sub", "heading"):
            labels.setdefault(norm(n["label"]), {"label": n["label"], "parents": set()})
    for r in read_jsonl(OUT / "groups.jsonl"):
        if r["parent"] and norm(r["child"]) in labels:
            labels[norm(r["child"])]["parents"].add(r["parent"])
    for value in labels.values():
        value["parents"] = sorted(value["parents"])[:3]
    return labels


def write_gold_template(rows):
    """Tạo mẫu 50 nhãn để người kiểm tự gán loại. Không ghi đè, không hiện kết quả máy."""
    path = OUT / "gold_labels.csv"
    if path.exists() or len(rows) < GOLD_LABEL_SAMPLE:
        return
    sample = random.Random(GOLD_SEED).sample(sorted(r["label"] for r in rows), GOLD_LABEL_SAMPLE)
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["label", "type_expected"])
        writer.writerows([label, ""] for label in sorted(sample))


def main():
    load_dotenv(ROOT / ".env")
    labels = collect_labels()
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}

    by_rule = {k for k, v in labels.items() if rule_type(v["label"])}
    todo = {k: v for k, v in labels.items() if k not in by_rule and k not in cache}
    if todo and os.getenv("groq_api_key"):
        print(f"Gọi LLM cho {len(todo)} nhãn, lô {LLM_BATCH}", flush=True)
        classify_with_llm(todo, cache)
    elif todo:
        print(f"[cảnh báo] Chưa có groq_api_key: {len(todo)} nhãn sẽ là unknown")

    rows = []
    for key, value in sorted(labels.items()):
        if key in by_rule:
            row = {"type": "not_skill", "canonical": "", "method": "rule"}
        elif key in cache:
            row = {**cache[key], "method": "llm"}
        else:
            row = {"type": "unknown", "canonical": "", "method": "none"}
        rows.append({"key": key, "label": value["label"], "parents": value["parents"], **row})
    write_jsonl(OUT / "labels.jsonl", rows)
    write_gold_template(rows)

    print(f"{len(rows)} nhãn: {dict(collections.Counter(r['type'] for r in rows))} | "
          f"cách gán: {dict(collections.Counter(r['method'] for r in rows))}")


if __name__ == "__main__":
    main()
