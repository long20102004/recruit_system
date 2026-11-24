import unittest
from unittest.mock import patch

import pandas as pd

from src.finetune_bert import answer_score, load_self_dataframe, split_by_question
from src.io_utils import load_answers, load_questions
from src.scoring import combine_model_and_rubric, evaluate_question


class GradedDataTest(unittest.TestCase):
    def test_assistant_grades_cover_every_question_without_claiming_an_expert(self):
        graded = pd.read_csv("data/interview_answers_graded.csv")
        bank_ids = {q["id"] for q in load_questions()["questions"]}
        self.assertEqual(len(graded), 90)
        self.assertEqual(set(graded.question_id), bank_ids)
        self.assertEqual(set(graded.label_source), {"assistant_graded"})
        self.assertEqual(set(graded.grader), {"coding-assistant"})
        self.assertTrue(graded.target_score.between(0, 10).all())
        synthetic = load_answers()
        self.assertEqual(set(synthetic.label_source), {"synthetic_rubric"})

    def test_score_column_accepts_the_v2_bank_and_groups_questions(self):
        frame = load_self_dataframe()
        self.assertIn("m3-v2-001", set(frame.question_id))
        self.assertGreater(len(frame), 390)
        sample = pd.Series({"target_score": 4.5})
        self.assertEqual(answer_score(sample), 4.5)
        train_df, test_df = split_by_question(frame, 0.25, 7)
        self.assertFalse(set(train_df.question_id) & set(test_df.question_id))
        self.assertEqual(len(train_df) + len(test_df), len(frame))


class FinetuneScoringTest(unittest.TestCase):
    def setUp(self):
        self.q = load_questions()["questions"][0]

    def test_finetune_score_stays_inside_rubric_evidence(self):
        with patch("src.regressor.predict_regression", return_value=8.0):
            result = evaluate_question(answer=self.q["reference_answer"], question=self.q, mode="finetune")
        self.assertEqual(result["mode"], "finetune")
        self.assertIsNone(result["bertscore_f1"])
        self.assertAlmostEqual(result["coverage_score"], 1)
        self.assertEqual(result["predicted_score"], 9.0)
        self.assertIn("bert-finetuned-self", result["model_version"])

    def test_keyword_stuffing_cap_still_applies_when_the_model_is_confident(self):
        text = ", ".join(h for c in self.q["criteria"] for h in c["hints"])
        with patch("src.regressor.predict_regression", return_value=10.0):
            result = evaluate_question(answer=text, question=self.q, mode="finetune")
        self.assertLessEqual(result["predicted_score"], 1)

    def test_blend_matches_the_existing_ceiling(self):
        rubric = {"coverage_score": 0.4, "keyword_only": False}
        self.assertAlmostEqual(combine_model_and_rubric(10, rubric), 6.0)

    def test_same_meaning_paraphrase_earns_full_criterion_points(self):
        question = next(q for q in load_questions()["questions"] if q["id"] == "m3-v2-002")
        answer = "2 đối tượng nếu tính là giống nhau thì phải giống mã hash"
        with patch("src.regressor.predict_regression", return_value=6.0), patch(
            "src.rubric.criterion_similarities", return_value=(0.88, 0.40)
        ):
            result = evaluate_question(answer=answer, question=question, mode="finetune")
        first = result["criterion_results"][0]
        self.assertEqual(first["status"], "covered")
        self.assertEqual(first["credit"], 1.0)
        self.assertEqual(first["points"], 4.0)
        self.assertEqual(first["max_points"], 4.0)

    def test_meaning_credit_uses_quarter_steps(self):
        question = next(q for q in load_questions()["questions"] if q["id"] == "m3-v2-002")
        answer = "Hai đối tượng giống nhau thì mã băm cũng phải giống"
        expected = {0.90: (1.0, 4.0), 0.78: (0.75, 3.0), 0.70: (0.5, 2.0), 0.67: (0.25, 1.0), 0.20: (0.0, 0.0)}
        for similarity, (credit, points) in expected.items():
            with patch("src.regressor.predict_regression", return_value=5.0), patch(
                "src.rubric.criterion_similarities", return_value=(similarity, 0.2)
            ):
                result = evaluate_question(answer=answer, question=question, mode="finetune")
            first = result["criterion_results"][0]
            self.assertEqual(first["credit"], credit, similarity)
            self.assertEqual(first["points"], points, similarity)

    def test_answer_closer_to_the_misconception_stays_at_zero(self):
        question = next(q for q in load_questions()["questions"] if q["id"] == "m3-v2-002")
        answer = "Hai object giống nhau vẫn có thể có mã băm khác"
        with patch("src.regressor.predict_regression", return_value=8.0), patch(
            "src.rubric.criterion_similarities", return_value=(0.80, 0.93)
        ):
            result = evaluate_question(answer=answer, question=question, mode="finetune")
        first = result["criterion_results"][0]
        self.assertEqual(first["status"], "contradicted")
        self.assertEqual(first["points"], 0.0)


if __name__ == "__main__":
    unittest.main()
