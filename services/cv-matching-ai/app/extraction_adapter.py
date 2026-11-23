"""Translate Module 1 CandidateProfile into the matchmaking input contract."""
from __future__ import annotations
import re
from datetime import date
from typing import Any


def _month(value: Any, *, current: bool = False) -> int | None:
    if not value:
        return date.today().year * 12 + date.today().month - 1 if current else None
    text = str(value).strip().lower()
    if text in {'present', 'now', 'current', 'hiện tại', 'nay'}:
        return date.today().year * 12 + date.today().month - 1
    match = re.fullmatch(r'(\d{4})[-/](\d{1,2})(?:[-/]\d{1,2})?', text)
    if match:
        year, month = map(int, match.groups())
    else:
        match = re.fullmatch(r'(\d{1,2})[-/](\d{4})', text)
        if match:
            month, year = map(int, match.groups())
        elif re.fullmatch(r'\d{4}', text):
            year, month = int(text), 1
        else:
            return None
    return year * 12 + month - 1 if 1900 <= year <= date.today().year + 1 and 1 <= month <= 12 else None


def experience_years(jobs: list[dict[str, Any]]) -> float:
    """Count overlapping employment months once, excluding future months."""
    months: set[int] = set()
    now = _month(None, current=True)
    for job in jobs:
        start = _month(job.get('start_date'))
        end = _month(job.get('end_date'), current=True)
        if start is not None and end is not None and start <= end:
            months.update(range(start, min(end, now) + 1))
    return round(len(months) / 12, 2)


def adapt_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    result = dict(candidate)
    personal = candidate.get('personal_info')
    if isinstance(personal, dict):
        result.setdefault('name', personal.get('full_name'))
    jobs = [item for item in candidate.get('experience', []) if isinstance(item, dict)] if isinstance(candidate.get('experience'), list) else []
    result.setdefault('experience_years', experience_years(jobs))
    titles = [job.get('job_title') for job in jobs if job.get('job_title')]
    if isinstance(candidate.get('experience_text'), list):
        titles = [str(text).split(' — ')[0].split(' @ ')[0] for text in candidate['experience_text'] if text]
        if not titles:
            result['experience_years'] = 0
    result.setdefault('job_titles', titles)
    education = candidate.get('education')
    if isinstance(education, list) or isinstance(candidate.get('education_text'), list):
        entries = [item for item in education if isinstance(item, dict)] if isinstance(education, list) else []
        # A school name alone does not prove a degree. Unknown remains unknown.
        levels = [' '.join(str(item.get(key) or '') for key in ('degree', 'level')) for item in entries]
        text = ' '.join(levels)
        if isinstance(candidate.get('education_text'), list):
            text = ' '.join(str(item) for item in candidate['education_text'])
        ranks = [('phd', 'phd'), ('tiến sĩ', 'phd'), ('master', 'master'), ('thạc sĩ', 'master'),
                 ('bachelor', 'bachelor'), ('cử nhân', 'bachelor'), ('kỹ sư', 'bachelor'),
                 ('associate', 'associate'), ('cao đẳng', 'associate')]
        result['education'] = {'degree': next((level for term, level in ranks if term in text.lower()), ''),
                               'major': next((str(item.get('major')) for item in entries if item.get('major')), '')}
    result.setdefault('summary', candidate.get('objective') or '')
    result.setdefault('raw_context', ' '.join(str(value or '') for value in [result.get('summary'),
        *[job.get('description') for job in jobs], candidate.get('experience_text'), candidate.get('education_text')]))
    return result
