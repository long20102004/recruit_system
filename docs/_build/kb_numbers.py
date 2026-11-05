"""Write kb_numbers.json for the document from ai-service/kb/seed (counts only)."""
import csv, json, sys
from collections import Counter
from pathlib import Path
seed = Path(sys.argv[1]); out = Path(sys.argv[2]); linkrate = sys.argv[3] if len(sys.argv) > 3 else ""
names = {"skills.csv": "Kỹ năng (skills)", "skill_aliases.csv": "Alias kỹ năng", "skill_edges.csv": "Quan hệ KG (skill_edges)",
         "universities.csv": "Trường học", "university_aliases.csv": "Alias trường", "job_titles.csv": "Chức danh / nghề"}
label = {"stackoverflow-2024": "Stack Overflow 2024", "stackoverflow-2025": "Stack Overflow 2025", "stackoverflow-2026": "Stack Overflow 2026",
         "wikidata": "Wikidata", "linguist": "Linguist", "esco": "ESCO", "wikipedia": "Wikipedia", "stackoverflow-tags": "Stack Overflow tags", "institution": "Website trường"}
rows = []
for f, n in names.items():
    r = list(csv.DictReader(open(seed / f, encoding="utf-8")))
    c = Counter(x.get("source", "").split(":")[0] for x in r)
    rows.append([n, f"{len(r):,}".replace(",", "."), ", ".join(f"{label.get(k, k)} {v}" for k, v in c.most_common())])
note = linkrate or "Độ phủ trên 20 CV thật đang được đo lại sau khi hoàn thiện KB (mốc KB cũ: 77% kỹ năng, 95% tên trường)."
json.dump({"date": "05/11/2026", "table": rows, "coverage_note": note}, open(out, "w"), ensure_ascii=False, indent=1)
print(json.dumps(rows, ensure_ascii=False))
