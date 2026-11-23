import unittest
from app.extraction_adapter import adapt_candidate, experience_years

class ExtractionAdapterTest(unittest.TestCase):
    def test_extraction_schema_keeps_name_jobs_and_degree(self):
        value = adapt_candidate({'personal_info': {'full_name': 'Test'},
            'experience': [{'job_title': 'Developer', 'start_date': '01/2020', 'end_date': '12/2020'}],
            'education': [{'degree': 'Bachelor', 'major': 'IT', 'school': 'PTIT'}]})
        self.assertEqual(value['name'], 'Test')
        self.assertEqual(value['job_titles'], ['Developer'])
        self.assertEqual(value['experience_years'], 1)
        self.assertEqual(value['education']['degree'], 'bachelor')
        self.assertEqual(value['education']['major'], 'IT')

    def test_overlapping_jobs_are_not_double_counted(self):
        self.assertEqual(experience_years([
            {'start_date': '2020-01', 'end_date': '2020-12'},
            {'start_date': '2020-06', 'end_date': '2021-05'}]), 1.42)

    def test_unknown_education_does_not_invent_a_degree(self):
        self.assertEqual(adapt_candidate({'education': [{'school': 'PTIT'}]})['education']['degree'], '')

    def test_confirmed_corrections_override_extracted_titles(self):
        result = adapt_candidate({'experience': [{'job_title': 'Wrong'}], 'experience_text': ['Correct — Company']})
        self.assertEqual(result['job_titles'], ['Correct'])

    def test_clearing_experience_removes_years(self):
        result = adapt_candidate({'experience': [{'start_date': '2020-01', 'end_date': '2020-12'}], 'experience_text': []})
        self.assertEqual(result['job_titles'], [])
        self.assertEqual(result['experience_years'], 0)

    def test_legacy_schema_is_preserved(self):
        result = adapt_candidate({'name': 'Legacy', 'experience_years': 3, 'job_titles': ['Engineer'], 'education': 'bachelor'})
        self.assertEqual(result['experience_years'], 3)
        self.assertEqual(result['education'], 'bachelor')

    def test_invalid_dates_are_ignored(self):
        self.assertEqual(experience_years([{'start_date': 'bad', 'end_date': '2020-12'}]), 0)

if __name__ == '__main__':
    unittest.main()
