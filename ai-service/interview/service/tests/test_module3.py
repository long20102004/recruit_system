import json,unittest
from unittest.mock import patch
from pathlib import Path
import numpy as np
from src.io_utils import load_questions,load_answers
from src.coverage import contains_phrase,score_coverage
from src.rubric import evaluate_rubric
from src.scoring import evaluate_question

CALIB={'coefficients':{'bert_P':0,'bert_R':0,'bert_F1':5,'coverage_score':5,'length_norm':0},
       'intercept':0,'model_version':'test-synthetic','label_source':'synthetic_rubric','bert_model_type':'test-model'}
class BankTest(unittest.TestCase):
    def test_bank_and_label_provenance_are_consistent(self):
        bank=load_questions();answers=load_answers()
        self.assertEqual(len(bank['questions']),30)
        self.assertEqual(len(answers),390)
        self.assertNotIn('human_score',answers.columns)
        self.assertEqual(set(answers['label_source']),{'synthetic_rubric'})
        keys=[q['id'] for q in bank['questions']]
        self.assertEqual(len(keys),len(set(keys)))
        self.assertEqual(set(answers.question_id),set(keys))
        for q in bank['questions']:
            self.assertAlmostEqual(sum(c['weight'] for c in q['criteria']),1)
            self.assertEqual(q['review_status'],'needs_expert_review')
            for c in q['criteria']:
                self.assertTrue(c['reference_answers']);self.assertTrue(c['misconceptions'])

    def test_negatives_and_partial_targets_are_not_falsely_human_labels(self):
        data=load_answers()
        for variant in ['misconceptions','unknown','offtopic']:
            self.assertTrue((data.loc[data.variant==variant,'target_score']==0).all())
        self.assertTrue((data.loc[data.variant=='keyword-stuffing','target_score']<=1).all())

class ScoringTest(unittest.TestCase):
    def setUp(self):self.q=load_questions()['questions'][0]
    def test_phrase_boundaries_prevent_short_substring_matches(self):
        self.assertFalse(contains_phrase('different','di'))
        self.assertTrue(contains_phrase('Dùng DI trong service','DI'))
    def test_explicit_wrong_answers_do_not_pass_keyword_coverage(self):
        text=' '.join(c['misconceptions'][0] for c in self.q['criteria'])
        self.assertEqual(score_coverage(text,self.q['criteria'])['coverage_score'],0)
    def test_fast_full_partial_wrong_ordering(self):
        with patch('src.scoring.load_calibration',return_value=CALIB):
            full=evaluate_question(answer=self.q['reference_answer'],question=self.q,mode='fast')
            partial=evaluate_question(answer=self.q['criteria'][0]['reference_answers'][0],question=self.q,mode='fast')
            wrong=evaluate_question(answer='Tôi chưa biết.',question=self.q,mode='fast')
        self.assertGreater(full['predicted_score'],partial['predicted_score'])
        self.assertGreater(partial['predicted_score'],wrong['predicted_score'])
        self.assertIsNone(full['bertscore_f1'])
        self.assertEqual(len(full['criterion_results']),3)
    def test_keyword_stuffing_is_capped(self):
        text=', '.join(h for c in self.q['criteria'] for h in c['hints'])
        with patch('src.scoring.load_calibration',return_value=CALIB):
            result=evaluate_question(answer=text,question=self.q,mode='fast')
        self.assertLessEqual(result['predicted_score'],1)
    def test_semantic_path_returns_real_metric_contract_using_stubbed_model_boundary(self):
        def pairs(candidates,references,**kwargs):
            values=np.array([.30 if ref in [m for c in self.q['criteria'] for m in c['misconceptions']] else .96 for ref in references])
            return values,values,values
        with patch('src.scoring.load_calibration',return_value=CALIB),patch('src.scoring.bertscore_prf',side_effect=pairs) as global_score,patch('src.rubric.bertscore_prf',side_effect=pairs) as rubric_score:
            result=evaluate_question(answer='Tôi giải thích bằng một cách diễn đạt tương đương hoàn toàn.',question=self.q,mode='bertscore')
        self.assertTrue(global_score.called and rubric_score.called)
        self.assertEqual(result['bertscore_f1'],.96)
        self.assertEqual(result['mode'],'bertscore')
        self.assertAlmostEqual(result['coverage_score'],1)
    def test_semantic_failure_does_not_silently_use_lexical_mode(self):
        with patch('src.scoring.load_calibration',return_value=CALIB),patch('src.scoring.bertscore_prf',side_effect=RuntimeError('model missing')):
            with self.assertRaises(RuntimeError):evaluate_question(answer='Có câu trả lời.',question=self.q,mode='bertscore')
    def test_semantic_similarity_does_not_override_explicit_misconception(self):
        text=' '.join(c['misconceptions'][0] for c in self.q['criteria'])
        def pairs(a,r,**kw):return tuple(np.full(len(a),.99) for _ in range(3))
        with patch('src.rubric.bertscore_prf',side_effect=pairs):
            result=evaluate_rubric(text,self.q['criteria'],'bertscore','stub')
        self.assertEqual(result['coverage_score'],0)
        self.assertTrue(all(c['status']=='contradicted' for c in result['criterion_results']))

class ApiValidationTest(unittest.TestCase):
    def test_blank_answer_and_duplicate_rubric_keys_are_rejected(self):
        from src.api import EvaluateRequest,CriterionIn
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):EvaluateRequest(answer='   ',question_id='q')
        c=CriterionIn(key='same',label='Ý',weight=1)
        with self.assertRaises(ValidationError):EvaluateRequest(answer='Nội dung',reference_answer='Mẫu',criteria=[c,c])

if __name__=='__main__':unittest.main()
