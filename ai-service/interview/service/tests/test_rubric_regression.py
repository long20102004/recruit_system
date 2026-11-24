"""Replay the user's live BERTScore values, not invented higher semantic scores."""
import copy,unittest
from unittest.mock import patch
import numpy as np
from src.evidence import evidence_units
from src.rubric import evaluate_rubric
from src.scoring import evaluate_question

ANSWER='Spring Boot xây trên Spring Framework, hỗ trợ tự động cấu hình và dùng server nhúng như Tomcat.'
CRITERIA=[
 {'key':'spring','label':'Xây trên Spring Framework','weight':.3,'hints':['Spring Framework'],
  'reference_answers':['Spring Boot được xây dựng trên Spring Framework.']},
 {'key':'config','label':'Tự động cấu hình','weight':.4,'hints':['auto-configuration','tự động cấu hình'],
  'reference_answers':['Spring Boot tự động cấu hình ứng dụng theo các điều kiện.']},
 {'key':'server','label':'Server nhúng','weight':.3,'hints':['embedded server','Tomcat','server nhúng'],
  'reference_answers':['Spring Boot hỗ trợ server nhúng như Tomcat.']},
]
VALUES={c['reference_answers'][0]:v for c,v in zip(CRITERIA,[.8156,.7504,.871])}
def recorded_scores(candidates,references,**kwargs):
    a=np.array([VALUES[r] for r in references]);return a,a,a

class LiveRubricRegressionTest(unittest.TestCase):
    def grade(self,answer=ANSWER,criteria=None):
        with patch('src.rubric.bertscore_prf',side_effect=recorded_scores):
            return evaluate_rubric(answer,criteria or CRITERIA,'bertscore','stub')
    def test_three_explicit_ideas_are_covered_at_the_observed_bert_scores(self):
        result=self.grade()
        self.assertAlmostEqual(result['coverage_score'],1)
        self.assertTrue(all(c['status']=='covered' for c in result['criterion_results']))
        self.assertTrue(all(c['evidence'] for c in result['criterion_results']))
    def test_alternative_hints_do_not_require_english_and_vietnamese_together(self):
        self.assertEqual(self.grade()['criterion_results'][1]['status'],'covered')
    def test_comma_and_conjunction_split_ideas_but_not_java_identifiers(self):
        self.assertEqual(len(evidence_units(ANSWER)),3)
        self.assertIn('Objects.equals(a,b)', ' '.join(evidence_units('Dùng Objects.equals(a,b) để xử lý null.')))
    def test_negated_feature_is_not_accepted_even_with_high_similarity(self):
        def high(a,r,**kw):return tuple(np.full(len(a),.99) for _ in range(3))
        with patch('src.rubric.bertscore_prf',side_effect=high):
            result=evaluate_rubric('Spring Boot không hỗ trợ tự động cấu hình.',CRITERIA,'bertscore','stub')
        self.assertEqual(result['criterion_results'][1]['status'],'contradicted')
        self.assertEqual(result['criterion_results'][1]['credit'],0)
    def test_bare_keywords_are_not_promoted_to_full_credit(self):
        result=self.grade('Spring Framework, tự động cấu hình, server nhúng, Tomcat')
        self.assertEqual(result['coverage_score'],0)
    def test_low_similarity_does_not_become_full_credit_on_anchor_alone(self):
        def low(a,r,**kw):return tuple(np.full(len(a),.3) for _ in range(3))
        with patch('src.rubric.bertscore_prf',side_effect=low):
            result=evaluate_rubric('Spring Boot hỗ trợ tự động cấu hình.',CRITERIA,'bertscore','stub')
        self.assertNotEqual(result['criterion_results'][1]['status'],'covered')
    def test_debug_coverage_matches_result_and_separates_ridge_keyword_feature(self):
        calib={'coefficients':{'bert_P':0,'bert_R':0,'bert_F1':5,'coverage_score':5,'length_norm':0},'intercept':0,'model_version':'test'}
        with patch('src.scoring.load_calibration',return_value=calib),patch('src.scoring.bertscore_prf',return_value=(np.array([.8353]),np.array([.9011]),np.array([.8669]))),patch('src.rubric.bertscore_prf',side_effect=recorded_scores):
            result=evaluate_question(answer=ANSWER,question={'reference_answer':'Spring Boot xây trên Spring Framework, hỗ trợ auto-configuration và embedded server.','criteria':CRITERIA},mode='bertscore',include_debug=True)
        self.assertEqual(result['coverage_score'],result['debug']['coverage_score'])
        self.assertIn('keyword_coverage_score',result['debug'])
        self.assertEqual(result['missing_points'],[])
        self.assertTrue(result['model_version'].endswith('+evidence-v3'))

if __name__=='__main__':unittest.main()
