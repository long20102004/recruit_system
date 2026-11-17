"""
Fine-tune BERT (regression) for short-answer / interview scoring.

Data:
  - Mohler ASAG (HF: nkazi/MohlerASAG, raw/open_ended) — scores 0–5 → scaled to 0–10
  - Self HireLens answers.csv + questions.json — scores already 0–10

Scenarios (--scenario):
  mohler      train/eval on Mohler only
  self        train/eval on self only
  combined    mix both (stratified by source), eval on each test split
  transfer    train Mohler → continue on self; eval on self test

Colab / local:
  python -m src.finetune_bert --scenario combined --epochs 3
  python -m src.finetune_bert --scenario transfer --epochs 2 --mohler-epochs 2
"""

from __future__ import annotations

import argparse
import json
import random
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from .io_utils import DATA, ROOT, load_answers, load_questions, questions_by_id


def pearson(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    if len(y_true) < 2:
        return float("nan")
    return float(np.corrcoef(y_true, y_pred)[0, 1])


def metrics_dict(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, Any]:
    y_pred = np.clip(y_pred, 0.0, 10.0)
    return {
        "mae": round(float(mean_absolute_error(y_true, y_pred)), 4),
        "rmse": round(float(np.sqrt(mean_squared_error(y_true, y_pred))), 4),
        "r2": round(float(r2_score(y_true, y_pred)), 4),
        "pearson": round(pearson(y_true, y_pred), 4),
        "n": int(len(y_true)),
    }


def build_text(question: str, answer: str, reference: str | None = None) -> str:
    q = (question or "").strip()
    a = (answer or "").strip()
    r = (reference or "").strip()
    if r:
        return f"Question: {q}\nReference: {r}\nAnswer: {a}"
    return f"Question: {q}\nAnswer: {a}"


def load_mohler_dataframe() -> pd.DataFrame:
    from datasets import load_dataset

    ds = load_dataset("nkazi/MohlerASAG", "raw", split="open_ended")
    rows = []
    for row in ds:
        score5 = float(row["score_avg"])
        rows.append(
            {
                "id": f"mohler:{row['id']}",
                "question_id": f"mohler::{row['question']}",
                "source": "mohler",
                "question": row["question"],
                "reference_answer": row["instructor_answer"],
                "answer": row["student_answer"],
                "human_score": score5 * 2.0,  # 0–5 → 0–10
                "human_score_raw": score5,
            }
        )
    return pd.DataFrame(rows)


def answer_score(row: pd.Series) -> float:
    """Bank v2 uses target_score. Older answers.csv uses human_score."""
    for column in ("target_score", "human_score"):
        if column in row and pd.notna(row[column]):
            return float(row[column])
    raise KeyError("answer row has neither target_score nor human_score")


def _rows_from_answers(answers: pd.DataFrame, qmap: dict) -> list[dict]:
    rows = []
    for _, row in answers.iterrows():
        qid = str(row["question_id"])
        question = qmap.get(qid)
        if not question:
            continue
        score = answer_score(row)
        rows.append(
            {
                "id": f"self:{row['id']}",
                "question_id": qid,
                "source": str(row["label_source"]) if "label_source" in row and pd.notna(row["label_source"]) else "self",
                "question": question["question"],
                "reference_answer": question.get("reference_answer", ""),
                "answer": str(row["answer"]),
                "human_score": score,
                "human_score_raw": score,
            }
        )
    return rows


def load_self_dataframe(include_graded: bool = True) -> pd.DataFrame:
    qmap = questions_by_id(load_questions())
    frames = [pd.DataFrame(_rows_from_answers(load_answers(), qmap))]
    graded = DATA / "interview_answers_graded.csv"
    if include_graded and graded.exists():
        frames.append(pd.DataFrame(_rows_from_answers(pd.read_csv(graded), qmap)))
    return pd.concat(frames, ignore_index=True)


@dataclass
class TrainConfig:
    model_name: str = "bert-base-multilingual-cased"
    scenario: str = "combined"
    max_length: int = 256
    epochs: int = 3
    mohler_epochs: int = 2
    batch_size: int = 8
    lr: float = 2e-5
    weight_decay: float = 0.01
    test_size: float = 0.2
    seed: int = 42
    use_reference: bool = True
    output_dir: str = ""


def split_by_question(df: pd.DataFrame, test_size: float, seed: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Keep every answer of a question on one side of the split."""
    if "question_id" not in df.columns:
        raise ValueError("fine-tune frame needs question_id for a grouped split")
    groups = sorted(df["question_id"].astype(str).unique())
    if len(groups) < 2:
        raise ValueError(f"Need at least 2 questions to split, got {len(groups)}")
    order = np.array(groups)
    np.random.RandomState(seed).shuffle(order)
    n_test = int(round(len(order) * test_size))
    n_test = min(max(n_test, 1), len(order) - 1)
    test_ids = set(order[:n_test])
    mask = df["question_id"].astype(str).isin(test_ids)
    train_df = df.loc[~mask].reset_index(drop=True)
    test_df = df.loc[mask].reset_index(drop=True)
    if train_df.empty or test_df.empty:
        raise ValueError("grouped split produced an empty side")
    return train_df, test_df


def split_df(df: pd.DataFrame, test_size: float, seed: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    return split_by_question(df, test_size, seed)


def make_hf_dataset(df: pd.DataFrame, use_reference: bool):
    from datasets import Dataset

    texts = [
        build_text(
            r["question"],
            r["answer"],
            r["reference_answer"] if use_reference else None,
        )
        for _, r in df.iterrows()
    ]
    return Dataset.from_dict(
        {
            "text": texts,
            "label": [float(x) for x in df["human_score"].tolist()],
            "id": df["id"].tolist(),
            "source": df["source"].tolist(),
        }
    )


def run_training(cfg: TrainConfig) -> dict[str, Any]:
    import torch
    from transformers import (
        AutoModelForSequenceClassification,
        AutoTokenizer,
        Trainer,
        TrainingArguments,
        set_seed,
    )

    set_seed(cfg.seed)
    random.seed(cfg.seed)
    np.random.seed(cfg.seed)

    out_dir = Path(cfg.output_dir) if cfg.output_dir else ROOT / "output" / f"bert_finetuned_{cfg.scenario}"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("[1] Load data…")
    self_df = load_self_dataframe()
    print(f"    Self HireLens:     {len(self_df)}")
    if cfg.scenario == "self":
        mohler = self_df.iloc[0:0].copy()
    else:
        mohler = load_mohler_dataframe()
        print(f"    Mohler open_ended: {len(mohler)} (scores scaled 0–10)")

    if cfg.scenario == "self":
        mohler_tr, mohler_te = mohler, mohler
    else:
        mohler_tr, mohler_te = split_df(mohler, cfg.test_size, cfg.seed)
    self_tr, self_te = split_df(self_df, cfg.test_size, cfg.seed)

    if cfg.scenario == "mohler":
        train_df, eval_packs = mohler_tr, {"mohler_test": mohler_te}
        stages = [("mohler", train_df, cfg.epochs)]
    elif cfg.scenario == "self":
        train_df, eval_packs = self_tr, {"self_test": self_te}
        stages = [("self", train_df, cfg.epochs)]
    elif cfg.scenario == "combined":
        train_df = pd.concat([mohler_tr, self_tr], ignore_index=True)
        train_df = train_df.sample(frac=1.0, random_state=cfg.seed).reset_index(drop=True)
        eval_packs = {"mohler_test": mohler_te, "self_test": self_te}
        stages = [("combined", train_df, cfg.epochs)]
    elif cfg.scenario == "transfer":
        eval_packs = {"mohler_test": mohler_te, "self_test": self_te}
        stages = [
            ("mohler_pretrain", mohler_tr, cfg.mohler_epochs),
            ("self_finetune", self_tr, cfg.epochs),
        ]
    else:
        raise ValueError(f"Unknown scenario: {cfg.scenario}")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[2] Model={cfg.model_name} device={device}")

    tokenizer = AutoTokenizer.from_pretrained(cfg.model_name)
    model = AutoModelForSequenceClassification.from_pretrained(
        cfg.model_name,
        num_labels=1,
        problem_type="regression",
    )

    def tokenize(batch):
        return tokenizer(
            batch["text"],
            truncation=True,
            padding="max_length",
            max_length=cfg.max_length,
        )

    def compute_metrics(eval_pred):
        preds, labels = eval_pred
        preds = np.asarray(preds).reshape(-1)
        labels = np.asarray(labels).reshape(-1)
        return metrics_dict(labels, preds)

    last_trainer = None
    for stage_name, stage_df, epochs in stages:
        print(f"[3] Stage={stage_name} n_train={len(stage_df)} epochs={epochs}")
        train_ds = make_hf_dataset(stage_df, cfg.use_reference).map(tokenize, batched=True)
        # tiny val from train for early logging
        n_val = max(1, min(32, len(stage_df) // 10))
        split = train_ds.train_test_split(test_size=n_val, seed=cfg.seed)
        train_ds, val_ds = split["train"], split["test"]

        ta_kwargs = dict(
            output_dir=str(out_dir / stage_name),
            num_train_epochs=epochs,
            per_device_train_batch_size=cfg.batch_size,
            per_device_eval_batch_size=cfg.batch_size,
            learning_rate=cfg.lr,
            weight_decay=cfg.weight_decay,
            save_strategy="epoch",
            load_best_model_at_end=True,
            metric_for_best_model="mae",
            greater_is_better=False,
            logging_steps=20,
            report_to=[],
            fp16=torch.cuda.is_available(),
            seed=cfg.seed,
        )
        # transformers API: eval_strategy (new) vs evaluation_strategy (old)
        try:
            args = TrainingArguments(**ta_kwargs, eval_strategy="epoch")
        except TypeError:
            args = TrainingArguments(**ta_kwargs, evaluation_strategy="epoch")

        trainer = Trainer(
            model=model,
            args=args,
            train_dataset=train_ds,
            eval_dataset=val_ds,
            compute_metrics=compute_metrics,
        )
        trainer.train()
        last_trainer = trainer
        model = trainer.model

    assert last_trainer is not None

    print("[4] Evaluate…")
    results: dict[str, Any] = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "config": asdict(cfg),
        "n_mohler": len(mohler),
        "n_self": len(self_df),
        "device": device,
        "metrics": {},
    }

    for name, edf in eval_packs.items():
        eds = make_hf_dataset(edf, cfg.use_reference).map(tokenize, batched=True)
        pred_out = last_trainer.predict(eds)
        preds = np.asarray(pred_out.predictions).reshape(-1)
        labels = np.asarray(pred_out.label_ids).reshape(-1)
        m = metrics_dict(labels, preds)
        results["metrics"][name] = m
        print(f"    {name}: {m}")

        pred_path = out_dir / f"predictions_{name}.csv"
        pd.DataFrame(
            {
                "id": edf["id"].tolist(),
                "source": edf["source"].tolist(),
                "human_score": labels,
                "predicted_score": np.round(np.clip(preds, 0, 10), 2),
            }
        ).to_csv(pred_path, index=False)

    # Baseline F1*10 on self test (quick lexical) for report contrast on self only
    if "self_test" in eval_packs:
        from .features import lexical_prf

        edf = eval_packs["self_test"]
        base = []
        for _, r in edf.iterrows():
            _, _, f1 = lexical_prf(str(r["answer"]), str(r["reference_answer"]))
            base.append(f1 * 10.0)
        results["metrics"]["self_test_baseline_f1x10"] = metrics_dict(
            edf["human_score"].values, np.array(base)
        )
        print(f"    self_test_baseline_f1x10: {results['metrics']['self_test_baseline_f1x10']}")

    final_dir = out_dir / "model"
    last_trainer.save_model(str(final_dir))
    tokenizer.save_pretrained(str(final_dir))
    meta_path = out_dir / "finetune_metrics.json"
    meta_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[5] Saved model → {final_dir}")
    print(f"    Metrics   → {meta_path}")
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Fine-tune BERT for answer scoring")
    parser.add_argument(
        "--scenario",
        choices=["mohler", "self", "combined", "transfer"],
        default="combined",
    )
    parser.add_argument("--model-name", default="bert-base-multilingual-cased")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--mohler-epochs", type=int, default=2, help="Only for transfer")
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--lr", type=float, default=2e-5)
    parser.add_argument("--max-length", type=int, default=256)
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--no-reference", action="store_true")
    parser.add_argument("--output-dir", default="")
    args = parser.parse_args()

    cfg = TrainConfig(
        model_name=args.model_name,
        scenario=args.scenario,
        epochs=args.epochs,
        mohler_epochs=args.mohler_epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        max_length=args.max_length,
        test_size=args.test_size,
        seed=args.seed,
        use_reference=not args.no_reference,
        output_dir=args.output_dir,
    )
    print(f"ROOT={ROOT}")
    run_training(cfg)


if __name__ == "__main__":
    main()
