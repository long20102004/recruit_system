"""
Tính feature (fast hoặc BERTScore) + train Ridge → lưu calibration.json + metrics.

Chạy từ thư mục AI:
  python -m src.train_calibration --mode fast
  python -m src.train_calibration --mode bertscore
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

from .features import FEATURE_COLUMNS, bertscore_prf, build_feature_row, lexical_prf
from .io_utils import OUTPUT, load_answers, load_questions, questions_by_id


def pearson(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    if len(y_true) < 2:
        return float("nan")
    return float(np.corrcoef(y_true, y_pred)[0, 1])


def compute_features(
    answers: pd.DataFrame,
    qmap: dict,
    mode: str,
    model_type: str,
    device: str | None,
) -> pd.DataFrame:
    rows = []
    refs = []
    texts = []
    meta = []

    for _, row in answers.iterrows():
        q = qmap[row["question_id"]]
        texts.append(str(row["answer"]))
        refs.append(q["reference_answer"])
        meta.append(row)

    if mode == "fast":
        prf = [lexical_prf(a, r) for a, r in zip(texts, refs)]
        P = np.array([x[0] for x in prf])
        R = np.array([x[1] for x in prf])
        F1 = np.array([x[2] for x in prf])
    else:
        P, R, F1 = bertscore_prf(texts, refs, model_type=model_type, device=device)

    for i, row in enumerate(meta):
        q = qmap[row["question_id"]]
        feat = build_feature_row(str(row["answer"]), q, float(P[i]), float(R[i]), float(F1[i]))
        rows.append(
            {
                "id": row["id"],
                "question_id": row["question_id"],
                "rank_target": row.get("rank_target", ""),
                "human_score": float(row["human_score"]),
                "answer": row["answer"],
                **{k: feat[k] for k in FEATURE_COLUMNS},
                "covered_keys": feat["covered_keys"],
                "missing_keys": feat["missing_keys"],
            }
        )
    return pd.DataFrame(rows)


def metrics_dict(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    return {
        "mae": round(float(mean_absolute_error(y_true, y_pred)), 4),
        "rmse": round(float(np.sqrt(mean_squared_error(y_true, y_pred))), 4),
        "r2": round(float(r2_score(y_true, y_pred)), 4),
        "pearson": round(pearson(y_true, y_pred), 4),
        "n": int(len(y_true)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Train Ridge calibration for interview scoring")
    parser.add_argument("--mode", choices=["fast", "bertscore"], default="fast")
    parser.add_argument("--model-type", default="bert-base-multilingual-cased")
    parser.add_argument("--device", default=None, help="cpu | cuda — để trống để auto")
    parser.add_argument("--alpha", type=float, default=1.0, help="Ridge L2 strength")
    parser.add_argument("--test-size", type=float, default=0.25)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    OUTPUT.mkdir(parents=True, exist_ok=True)
    bundle = load_questions()
    qmap = questions_by_id(bundle)
    answers = load_answers()

    print(f"[1/4] Tính feature mode={args.mode} trên {len(answers)} mẫu...")
    feats = compute_features(answers, qmap, args.mode, args.model_type, args.device)
    feat_path = OUTPUT / f"features_{args.mode}.csv"
    feats.to_csv(feat_path, index=False)
    print(f"      → {feat_path}")

    X = feats[FEATURE_COLUMNS].values
    y = feats["human_score"].values
    idx = np.arange(len(feats))
    train_idx, test_idx = train_test_split(
        idx, test_size=args.test_size, random_state=args.seed
    )

    print(f"[2/4] Train Ridge alpha={args.alpha} (train={len(train_idx)}, test={len(test_idx)})...")
    model = Ridge(alpha=args.alpha)
    model.fit(X[train_idx], y[train_idx])

    pred_train = np.clip(model.predict(X[train_idx]), 0, 10)
    pred_test = np.clip(model.predict(X[test_idx]), 0, 10)

    # Baseline thô: F1 * 10
    base_test = np.clip(X[test_idx][:, 2] * 10.0, 0, 10)

    train_m = metrics_dict(y[train_idx], pred_train)
    test_m = metrics_dict(y[test_idx], pred_test)
    base_m = metrics_dict(y[test_idx], base_test)

    print("[3/4] Metrics")
    print(f"      Baseline F1*10  test: {base_m}")
    print(f"      Ridge           train: {train_m}")
    print(f"      Ridge           test:  {test_m}")

    pred_all = np.clip(model.predict(X), 0, 10)
    out_pred = feats[["id", "question_id", "human_score"]].copy()
    out_pred["predicted_score"] = np.round(pred_all, 2)
    out_pred["baseline_f1x10"] = np.round(np.clip(X[:, 2] * 10.0, 0, 10), 2)
    pred_path = OUTPUT / f"predictions_{args.mode}.csv"
    out_pred.to_csv(pred_path, index=False)

    calib = {
        "model_version": f"ridge-on-{args.mode}-v1",
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "mode": args.mode,
        "bert_model_type": args.model_type if args.mode == "bertscore" else None,
        "feature_columns": FEATURE_COLUMNS,
        "ridge_alpha": args.alpha,
        "coefficients": {c: float(w) for c, w in zip(FEATURE_COLUMNS, model.coef_)},
        "intercept": float(model.intercept_),
        "metrics": {
            "baseline_f1x10_test": base_m,
            "ridge_train": train_m,
            "ridge_test": test_m,
        },
        "role": bundle["meta"]["role"],
        "n_samples": int(len(feats)),
    }
    calib_path = OUTPUT / f"calibration_{args.mode}.json"
    calib_path.write_text(json.dumps(calib, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[4/4] Đã lưu {calib_path}")
    print(f"      Predictions → {pred_path}")
    print("Xong. Dùng: python -m src.predict_answer --mode", args.mode)


if __name__ == "__main__":
    main()
