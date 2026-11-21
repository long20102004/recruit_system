"""Cấu hình KB2 (nguồn web). Đường dẫn tính từ vị trí file này."""
import pathlib

from shared.config import ROLE_GROUPS

KB2 = pathlib.Path(__file__).resolve().parents[1]    # build_kb/kb2/
SOURCES_CSV = KB2 / "data" / "sources.csv"
OUT = KB2 / "out"

# --- T4: chức danh từ ITviec ---
ITVIEC_PAGES = {"vi": "https://itviec.com/viec-lam-it-theo-chuyen-mon",
                "en": "https://itviec.com/jobs-expertise-index"}
TITLES_RAW_CSV = KB2 / "data" / "itviec_titles_raw.csv"
TITLE_MAP_CSV = KB2 / "data" / "itviec_title_map.csv"     # duyệt tay: cặp Việt - Anh, nhóm vai trò, alias
TITLE_SOURCE_ID = "W01"
AMBIGUOUS_TITLE_ALIASES = {"ba", "director", "giám đốc", "manager", "pm", "po", "quản lý"}

# --- T6: ngành học, danh mục tự sinh ---
MAJORS_CSV = KB2 / "data" / "majors.csv"
MAJOR_SOURCE_ID = "M01"
MAJOR_GROUPS = ("it", "related", "other")          # Knowledge base.md, mục 1
AMBIGUOUS_MAJOR_ALIASES = {"ai", "ce", "cs", "ds", "is", "it", "se"}

# --- T4: cấp bậc ---
LEVELS_CSV = KB2 / "data" / "levels.csv"
LEVEL_SOURCE_ID = "M02"
from shared.config import LEVEL_RANKS  # noqa: E402,F401  (Knowledge base.md, mục 1)
AMBIGUOUS_LEVEL_ALIASES = {"lead", "mid", "nhan vien", "nhân viên"}
