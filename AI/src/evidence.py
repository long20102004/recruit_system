"""Local affirmative/negative evidence for rubric anchors.
Hints are alternatives, not independent requirements. This guard does not verify arbitrary facts.
"""
from __future__ import annotations
import re
from .coverage import normalize,contains_phrase

# Split coordinated statements as well as sentences, preserving dots inside API identifiers.
_SPLIT = re.compile(r'(?<=[.!?])\s+|[,;\n]+|\s+(?:và|nhưng|and|but)\s+', re.I)
_ASSERTION = re.compile(r'(?<!\w)(?:hỗ trợ|cung cấp|xây trên|xây dựng trên|dựa trên|được xây|sử dụng|dùng|là|có|giúp|cho phép|supports?|provides?|uses?|built on|based on|is|are)(?!\w)',re.I)
_NEGATION = re.compile(r'(?<!\w)(?:không|chẳng|chưa|not|never|does not|doesn\x27t|isn\x27t)(?!\w)',re.I)


def evidence_units(answer: str) -> list[str]:
    # Protect separators inside calls such as Objects.equals(a,b).
    depth=0;protected=[]
    for char in answer:
        if char in '([{': depth+=1
        if char in ',;' and depth:
            protected.append('\ue000' if char==',' else '\ue001')
        else: protected.append(char)
        if char in ')]}': depth=max(0,depth-1)
    units=[unit.strip().replace('\ue000',',').replace('\ue001',';')
        for unit in _SPLIT.split(''.join(protected)) if unit.strip()]
    return units[:24] or [answer]


def _negated_before(unit: str, anchor_start: int) -> bool:
    prefix=normalize(unit[:anchor_start])
    # "not only ..." is not a denial of the following proposition.
    prefix=re.sub(r'\bkhông\s+(?:chỉ|những)\b|\bnot\s+only\b','',prefix)
    return bool(_NEGATION.search(' '.join(prefix.split()[-8:])))


def local_evidence(answer: str, criterion: dict) -> dict:
    anchors=[criterion.get('label',''), *criterion.get('hints',[])]
    affirmative=[];negated=[]
    references=criterion.get('reference_answers') or []
    for raw in evidence_units(answer):
        unit=normalize(raw)
        for anchor in anchors:
            anchor=normalize(anchor).rstrip('.!?')
            if not anchor: continue
            match=re.search(r'(?<!\w)'+re.escape(anchor)+r'(?!\w)',unit)
            if match is None: continue
            # A full rubric reference can itself correctly describe a prohibition.
            full_reference=any(contains_phrase(unit,ref.rstrip('.!?')) for ref in references if ref)
            if _negated_before(unit,match.start()) and not full_reference:
                negated.append(raw);continue
            # A list or a question mentioning a term is not affirmative evidence.
            if '?' in raw or not _ASSERTION.search(unit) or len(unit.split())<4: continue
            affirmative.append(raw)
    return {'affirmative':bool(affirmative),'negated':bool(negated),
            'evidence':list(dict.fromkeys(affirmative))[:3]}
