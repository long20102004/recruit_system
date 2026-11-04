"""Candidate skill finder matching KB skills in CV text."""

from __future__ import annotations

from collections import defaultdict
import csv
from pathlib import Path
import re

from app.postprocess.text_match import normalize

__all__ = ["CandidateSkillFinder"]


class CandidateSkillFinder:
    """In-memory candidate skill finder matching KB skills against CV text."""

    def __init__(self, surfaces: dict[str, str] | None = None) -> None:
        self._short_patterns: list[tuple[re.Pattern[str], str]] = []
        self._special_long_patterns: list[tuple[re.Pattern[str], str]] = []
        self._batched_long_patterns: list[re.Pattern[str]] = []
        self._norm_to_canonical: dict[str, str] = {}

        if not surfaces:
            return

        short_surfaces: dict[str, str] = {}
        long_surfaces: dict[str, str] = {}

        for surface, canonical_name in surfaces.items():
            s = surface.strip()
            if not s or len(s) > 40:
                continue
            if len(s) <= 3:
                if s not in short_surfaces:
                    short_surfaces[s] = canonical_name
            else:
                if s not in long_surfaces:
                    long_surfaces[s] = canonical_name

        # 1. Compile short patterns (case-sensitive on raw cv_text)
        # Boundary: not alphanumeric or #/+ on either side
        for s, canonical_name in short_surfaces.items():
            pattern = re.compile(rf"(?<![\w#+]){re.escape(s)}(?![\w#+])")
            self._short_patterns.append((pattern, canonical_name))

        # 2. Process long surfaces (case and diacritic insensitive via normalize)
        for s, canonical_name in long_surfaces.items():
            norm_s = normalize(s)
            if not norm_s:
                continue
            if norm_s not in self._norm_to_canonical:
                self._norm_to_canonical[norm_s] = canonical_name

        special_surfaces: list[str] = []
        standard_by_word_count: dict[int, list[str]] = defaultdict(list)

        for norm_s in self._norm_to_canonical:
            if not (norm_s[0].isalnum() and norm_s[-1].isalnum()):
                special_surfaces.append(norm_s)
            else:
                words = norm_s.split()
                standard_by_word_count[len(words)].append(norm_s)

        # 2a. Special boundary patterns (e.g., starting with . like .net)
        for norm_s in special_surfaces:
            prefix = r"\b" if norm_s[0].isalnum() else r"(?<!\w)"
            suffix = r"\b" if norm_s[-1].isalnum() else r"(?!\w)"
            pattern = re.compile(rf"{prefix}{re.escape(norm_s)}{suffix}")
            self._special_long_patterns.append((pattern, self._norm_to_canonical[norm_s]))

        # 2b. Batched standard patterns grouped by word count
        batch_size = 50
        for w_count in sorted(standard_by_word_count.keys()):
            surfaces_list = sorted(standard_by_word_count[w_count], key=len, reverse=True)
            for i in range(0, len(surfaces_list), batch_size):
                batch = surfaces_list[i : i + batch_size]
                regex_str = rf"\b({'|'.join(re.escape(item) for item in batch)})\b"
                self._batched_long_patterns.append(re.compile(regex_str))

    @classmethod
    def from_csv(cls, seed_dir: str | Path) -> CandidateSkillFinder:
        """Load skills and aliases from seed directory CSV files."""
        seed_path = Path(seed_dir)
        skills_csv = seed_path / "skills.csv"
        aliases_csv = seed_path / "skill_aliases.csv"

        skills: dict[int, str] = {}
        if skills_csv.exists():
            with skills_csv.open("r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    raw_id = row.get("id")
                    if not raw_id:
                        continue
                    sid = int(raw_id.strip())
                    name = row.get("name", "").strip()
                    if name:
                        skills[sid] = name

        surfaces: dict[str, str] = {}
        # Skill canonical names as surfaces
        for sid, name in skills.items():
            if 0 < len(name) <= 40:
                surfaces[name] = name

        # Aliases as surfaces
        if aliases_csv.exists():
            with aliases_csv.open("r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    raw_sid = row.get("skill_id")
                    if not raw_sid:
                        continue
                    sid = int(raw_sid.strip())
                    surface = row.get("surface", "").strip()
                    if surface and len(surface) <= 40 and sid in skills:
                        if surface not in surfaces:
                            surfaces[surface] = skills[sid]

        return cls(surfaces=surfaces)

    def find(self, cv_text: str | None, limit: int = 30) -> list[str]:
        """Find KB candidate skills in CV text ordered by first appearance.

        Returns canonical names of matched skills, deduplicated, up to `limit`.
        """
        if not cv_text or not isinstance(cv_text, str) or not cv_text.strip() or limit <= 0:
            return []

        first_pos: dict[str, int] = {}

        # 1. Short surfaces (len <= 3): case-sensitive on raw cv_text
        for pattern, canonical_name in self._short_patterns:
            for m in pattern.finditer(cv_text):
                pos = m.start()
                if canonical_name not in first_pos or pos < first_pos[canonical_name]:
                    first_pos[canonical_name] = pos

        # 2. Long surfaces (len > 3): normalized matching
        norm_cv = normalize(cv_text)
        if norm_cv:
            # 2a. Special boundary patterns
            for pattern, canonical_name in self._special_long_patterns:
                for m in pattern.finditer(norm_cv):
                    pos = m.start()
                    if canonical_name not in first_pos or pos < first_pos[canonical_name]:
                        first_pos[canonical_name] = pos

            # 2b. Batched standard patterns
            for pattern in self._batched_long_patterns:
                for m in pattern.finditer(norm_cv):
                    matched_surface = m.group(1)
                    canonical_name = self._norm_to_canonical[matched_surface]
                    pos = m.start()
                    if canonical_name not in first_pos or pos < first_pos[canonical_name]:
                        first_pos[canonical_name] = pos

        # 3. Sort by position of first appearance (deterministic tie-break on name)
        sorted_skills = sorted(first_pos.keys(), key=lambda name: (first_pos[name], name))
        return sorted_skills[:limit]
