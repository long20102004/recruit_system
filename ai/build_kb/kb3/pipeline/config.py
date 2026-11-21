"""Cấu hình KB3 (tri thức do AI sinh). Đường dẫn tính từ vị trí file này."""
import pathlib

KB3 = pathlib.Path(__file__).resolve().parents[1]    # build_kb/kb3/
DATA = KB3 / "data"
SOURCES_CSV = DATA / "sources.csv"

# file dữ liệu -> source_id (mỗi file là một nguồn tự sinh, trust = low)
FILES = {
    "new_skills": ("new_skills.csv", "G01"),
    "skill_aliases": ("skill_aliases.csv", "G02"),
    "skill_fixes": ("skill_fixes.csv", "G03"),
    "edges": ("edges.csv", "G04"),
    "categories": ("categories.csv", "G05"),
    "titles": ("titles.csv", "G06"),
    "levels": ("levels.csv", "G07"),
    "majors": ("majors.csv", "G08"),
    "near": ("near.csv", "G09"),
}
