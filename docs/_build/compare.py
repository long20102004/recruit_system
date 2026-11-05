"""Compile the model x dataset comparison (variant B) and draw charts for the report.

Run from ai-service/:  ../docs/_build/plotenv-python compare.py <eval_models_dir or ""> <out_dir>
Cells come, in priority order, from: GPU runs of eval_models_colab.ipynb (same serving code for all
models) -> earlier measured runs -> numbers published in the specs. Counts only, no CV data.
"""
import json
import sys
from pathlib import Path

FIELDS = [("experience.company", "company"), ("education.school", "school"), ("skills", "skills"),
          ("personal_projects.name", "project"), ("experience.job_title", "job_title"),
          ("certificates", "certificates"), ("honours", "honours"), ("languages.language", "languages")]
MODELS = ["rule", "base", "v1", "v2", "v3"]
SPLITS = ["val", "val_swap", "dev", "test_real"]
LABEL = {"rule": "Rule-based", "base": "Qwen3-1.7B gốc", "v1": "LLM v1", "v2": "LLM v2", "v3": "LLM v3"}

# Published numbers (specs 003/006/007) for cells not re-run on GPU.
PUBLISHED = {
    ("rule", "val"): {"experience.company": .103, "education.school": .675, "skills": .710, "personal_projects.name": .525,
                      "certificates": .760, "honours": .625, "languages.language": .726},
    ("rule", "val_swap"): {"experience.company": .551, "education.school": .670, "skills": .700, "personal_projects.name": .521,
                           "certificates": .744, "honours": .625, "languages.language": .727},
    ("v1", "val"): {"experience.company": .918, "education.school": .961, "skills": .839, "personal_projects.name": .949,
                    "certificates": .890, "honours": .768, "languages.language": .849},
    ("v1", "val_swap"): {"experience.company": .926, "education.school": .966, "skills": .829, "personal_projects.name": .949,
                         "certificates": .824, "honours": .693, "languages.language": .799},
    ("v2", "val"): {"experience.company": .995, "education.school": 1.0, "skills": .932, "personal_projects.name": .982,
                    "certificates": .958, "honours": .981, "languages.language": .972},
    ("v2", "val_swap"): {"experience.company": .995, "education.school": .995, "skills": .928, "personal_projects.name": .982,
                         "certificates": .976, "honours": .981, "languages.language": .981},
}


def report_fields(path: Path):
    if not path.exists():
        return None
    split = next(iter(json.load(open(path))["splits"].values()))
    # f1 is null when the model predicted nothing; with gold items present that is F1 = 0
    return {k: (v.get("f1") if v.get("f1") is not None or not (v.get("tp", 0) + v.get("fn", 0)) else 0.0)
            for k, v in split["B"]["metrics"]["fields"].items()}


def main():
    gpu_dir, out = sys.argv[1], Path(sys.argv[2])
    runs = Path("data/real_test/runs")
    local = {("rule", "dev"): runs / "rule_v3/dev/report.json", ("rule", "test_real"): runs / "rule_v3/test_real/report.json",
             ("v1", "test_real"): runs / "v1_test_v3/report.json", ("v2", "test_real"): runs / "v2_test_v3/report.json",
             ("v3", "test_real"): runs / "v3_colab_api/report.json"}
    v3_colab = Path("data/finetune_output_v3/finetune_output_v3/eval_run/report.json")
    table, origin = {}, {}
    for m in MODELS:
        for s in SPLITS:
            cell, src = None, None
            if gpu_dir:
                p = Path(gpu_dir) / m / s / "report.json"
                cell = report_fields(p)
                src = "gpu" if cell else None
            if cell is None and (m, s) in local:
                cell, src = report_fields(local[(m, s)]), "local"
            if cell is None and m == "v3" and s in ("val", "val_swap") and v3_colab.exists():
                sp = json.load(open(v3_colab))["splits"].get(s)
                if sp:
                    cell, src = {k: v.get("f1") for k, v in sp["B"]["metrics"]["fields"].items()}, "colab-train"
            if cell is None and (m, s) in PUBLISHED:
                cell, src = PUBLISHED[(m, s)], "spec"
            table[f"{m}|{s}"], origin[f"{m}|{s}"] = cell, src
    out.mkdir(parents=True, exist_ok=True)
    json.dump({"table": table, "origin": origin, "fields": FIELDS, "models": MODELS, "splits": SPLITS, "label": LABEL},
              open(out / "compare.json", "w"), ensure_ascii=False, indent=1)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["font.family"] = "DejaVu Sans"
    colors = {"rule": "#A6A6A6", "base": "#F4B183", "v1": "#9DC3E6", "v2": "#2E75B6", "v3": "#1F4E79"}

    def mean(cell):
        # 7 fields every source reports (published spec numbers have no job_title)
        vals = [cell.get(f) for f, _ in FIELDS if f != "experience.job_title" and cell and cell.get(f) is not None]
        return sum(vals) / len(vals) if vals else None

    from matplotlib.patches import Patch
    handles = [Patch(facecolor=colors[m], edgecolor="#404040", label=LABEL[m]) for m in MODELS]
    # chart 1: mean F1 per dataset
    fig, ax = plt.subplots(figsize=(10, 4.6))
    w = 0.16
    for i, m in enumerate(MODELS):
        ys = [mean(table[f"{m}|{s}"]) for s in SPLITS]
        xs = [j + (i - 2) * w for j in range(len(SPLITS))]
        bars = ax.bar([x for x, y in zip(xs, ys) if y is not None], [y for y in ys if y is not None], w,
                      label=LABEL[m], color=colors[m], edgecolor="#404040", linewidth=0.5)
        for b in bars:
            ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.01, f"{b.get_height():.2f}", ha="center", fontsize=6.5)
        for x, y in zip(xs, ys):
            if y is None:
                ax.text(x, 0.02, "chờ\nchạy", ha="center", fontsize=6, color="#C00000")
    ax.set_xticks(range(len(SPLITS)))
    ax.set_xticklabels(["val (99 CV tổng hợp)", "val_swap (99, đổi tên)", "dev (45 CV bố cục thật)", "test_real (20 CV thật)"])
    ax.set_ylabel("F1 trung bình 7 trường"); ax.set_ylim(0, 1.08)
    ax.legend(handles=handles, ncol=5, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.12), frameon=False)
    ax.grid(axis="y", alpha=0.3); fig.tight_layout(); fig.savefig(out / "chart_mean_f1.png", dpi=170); plt.close(fig)

    # chart 2: per-field F1 on test_real
    fig, ax = plt.subplots(figsize=(10, 4.6))
    for i, m in enumerate(MODELS):
        cell = table[f"{m}|test_real"] or {}
        ys = [cell.get(f) for f, _ in FIELDS]
        xs = [j + (i - 2) * w for j in range(len(FIELDS))]
        ax.bar([x for x, y in zip(xs, ys) if y is not None], [y for y in ys if y is not None], w, label=LABEL[m],
               color=colors[m], edgecolor="#404040", linewidth=0.5)
    ax.set_xticks(range(len(FIELDS))); ax.set_xticklabels([n for _, n in FIELDS])
    ax.set_ylabel("F1 (20 CV thật)"); ax.set_ylim(0, 1.05)
    ax.legend(handles=handles, ncol=5, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.1), frameon=False)
    ax.grid(axis="y", alpha=0.3); fig.tight_layout(); fig.savefig(out / "chart_test_real_fields.png", dpi=170); plt.close(fig)
    print({k: v for k, v in origin.items()})


if __name__ == "__main__":
    main()
