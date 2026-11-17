"""Explainable lexical rubric evidence. Keywords alone do not prove correctness."""
from __future__ import annotations
import re
import unicodedata
from typing import Any

def normalize(text: str) -> str:
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFC', text or '').lower()).strip()

def contains_phrase(text: str, phrase: str) -> bool:
    phrase=normalize(phrase)
    return bool(phrase and re.search(r'(?<!\w)'+re.escape(phrase)+r'(?!\w)', normalize(text)))

def has_conflict(answer, criterion):
    return any(contains_phrase(answer, wrong.rstrip('.!?')) for wrong in criterion.get('misconceptions', []) if wrong)

def keyword_only(answer, criteria):
    words=set(re.findall(r'\w+', normalize(answer)))
    hints=set(re.findall(r'\w+', ' '.join(str(h) for c in criteria for h in c.get('hints', []))))
    return bool(words) and words <= set(normalize(x) for x in hints)

def criterion_covered(answer: str, criterion: dict[str, Any], threshold: int = 2) -> bool:
    if has_conflict(answer, criterion): return False
    refs=criterion.get('reference_answers') or [criterion.get('label','')]
    if any(contains_phrase(answer, ref.rstrip('.!?')) for ref in refs if ref): return True
    hints=[h for h in criterion.get('hints',[]) if h]
    return len(re.findall(r'\w+',answer)) >= 5 and sum(contains_phrase(answer,h) for h in hints) >= min(threshold,max(1,len(hints)))

def score_coverage(answer: str, criteria: list[dict[str, Any]]) -> dict[str, Any]:
    covered=[c['key'] for c in criteria if criterion_covered(answer,c)]
    if keyword_only(answer,criteria): covered=[]
    total=sum(max(0,float(c.get('weight',0))) for c in criteria)
    weighted=sum(max(0,float(c.get('weight',0))) for c in criteria if c['key'] in covered)
    return {'coverage_score':round(weighted/total if total else 0,4),
        'covered_keys':covered,'missing_keys':[c['key'] for c in criteria if c['key'] not in covered],
        'covered_labels':[c['label'] for c in criteria if c['key'] in covered],
        'missing_labels':[c['label'] for c in criteria if c['key'] not in covered]}
