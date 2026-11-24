"""Criterion evidence combines semantic similarity with explicit misconception guards.
Thresholds are configurable heuristics, not a factual-verification model.
"""
from __future__ import annotations
import os,re
from .coverage import criterion_covered, has_conflict, keyword_only, contains_phrase
from .features import bertscore_prf
from .evidence import evidence_units,local_evidence
from .meaning import credit_from_similarity, criterion_similarities

def _finetune_credit(answer, criterion, exact_reference, lexical):
    """Same meaning earns credit. Scores land on quarter steps, not only all or nothing."""
    if exact_reference or lexical:
        return 1.0, 'covered'
    positive, negative = criterion_similarities(answer, criterion)
    # Only a near-copy of the wrong statement counts as a contradiction.
    # A correct point can still sit near another criterion's misconception.
    if negative >= positive + 0.03 and negative >= 0.90:
        return 0.0, 'contradicted'
    credit = credit_from_similarity(positive)
    if credit >= 1:
        return credit, 'covered'
    if credit > 0:
        return credit, 'partial'
    return 0.0, 'missing'


def evaluate_rubric(answer, criteria, mode, model_type, device=None):
    if not criteria: raise ValueError('Rubric must have at least one criterion')
    total=sum(float(c.get('weight',0)) for c in criteria)
    if total <= 0: raise ValueError('Rubric weights must have positive total')
    threshold=float(os.getenv('HIRELENS_CRITERION_THRESHOLD','0.85'))
    positive={};negative={}
    if mode=='bertscore':
        clauses=evidence_units(answer)
        candidates=[];references=[];locations=[]
        for index,c in enumerate(criteria):
            for kind,refs in [('positive',c.get('reference_answers') or [c['label']]),('negative',c.get('misconceptions',[]))]:
                for ref in refs:
                    for clause in clauses:
                        candidates.append(clause);references.append(ref);locations.append((index,kind))
        _,_,scores=bertscore_prf(candidates,references,model_type=model_type,device=device)
        for (index,kind),score in zip(locations,scores):
            target=positive if kind=='positive' else negative
            target[index]=max(target.get(index,0),float(score))
    stuffing=keyword_only(answer,criteria)
    results=[]
    for index,c in enumerate(criteria):
        semantic=positive.get(index)
        lexical=criterion_covered(answer,c)
        evidence=local_evidence(answer,c)
        exact_reference=any(contains_phrase(answer,ref.rstrip('.!?')) for ref in c.get('reference_answers',[]) if ref)
        conflict=has_conflict(answer,c) or evidence["negated"] or (negative.get(index,0)>=threshold and negative.get(index,0)>(semantic or 0)+.03)
        if conflict or stuffing: credit=0.0;status='contradicted' if conflict else 'missing'
        elif mode=='bertscore':
            # A local assertion of an alternative anchor can support a concise paraphrase.
            # Do not lower the unconditional semantic threshold or count bare keywords.
            supported=evidence['affirmative'] and (semantic or 0)>=.70
            credit=1.0 if exact_reference or supported or (semantic or 0)>=threshold else .5 if lexical or (semantic or 0)>=threshold-.05 else 0
            status='covered' if credit==1 else 'partial' if credit else 'missing'
        elif mode=='finetune':
            credit,status=_finetune_credit(answer,c,exact_reference,lexical)
        else: credit=1.0 if lexical else 0.0;status='covered' if credit else 'missing'
        weight=float(c.get('weight',0))/total
        results.append({'key':c['key'],'label':c['label'],'weight':round(weight,6),
            'status':status,'credit':credit,'points':round(10*weight*credit,3),
            'max_points':round(10*weight,3),'evidence':evidence['evidence'],'semantic_f1':round(semantic,4) if semantic is not None else None,
            'feedback':'Có dấu hiệu mâu thuẫn với tiêu chí.' if status=='contradicted' else 'Đã thể hiện ý chính.' if credit>=1 else
                'Đúng một phần ý này.' if credit>=0.5 else 'Có phần gần nghĩa, cần nói rõ hơn.' if credit else
                'Chưa tìm thấy bằng chứng rõ cho ý này.'})
    coverage=sum(r['weight']*r['credit'] for r in results)
    return {'coverage_score':min(1.0,coverage),'criterion_results':results,'keyword_only':stuffing,
        'covered_labels':[r['label'] for r in results if r['status']=='covered'],
        'missing_labels':[r['label'] for r in results if r['status']!='covered']}
