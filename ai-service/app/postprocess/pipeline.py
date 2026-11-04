"""End-to-end post-processing pipeline for extracted CV profiles.

Pure function orchestration: normalises schema keys and types, cleans skills
and project tech stacks, and grounds extracted entities against the original CV text.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from typing import Any

from app.postprocess.grounding import ground_profile
from app.postprocess.schema import normalize_profile
from app.postprocess.skills import clean_skill_list


@dataclass
class PostprocessStats:
    keys_renamed: int = 0
    types_coerced: int = 0
    skills_cleaned: int = 0
    contacts_nulled: int = 0
    names_snapped: int = 0
    experience_removed_ungrounded: int = 0
    experience_removed_type: int = 0
    education_removed: int = 0
    projects_removed: int = 0
    items_removed_ungrounded: int = 0
    bullets_merged: int = 0
    duplicates_removed: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            field.name: getattr(self, field.name)
            for field in dataclasses.fields(self)
            if getattr(self, field.name) > 0
        }


def postprocess(data: Any, cv_text: str) -> tuple[dict, PostprocessStats]:
    stats = PostprocessStats()
    profile = normalize_profile(data, stats)
    profile["skills"] = clean_skill_list(profile["skills"], stats)
    for project in profile.get("personal_projects", []):
        project["tech_stack"] = clean_skill_list(project.get("tech_stack", []), stats)
    profile = ground_profile(profile, cv_text, stats)
    return profile, stats
