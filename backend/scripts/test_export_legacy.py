import importlib.util
import json
import unittest
from pathlib import Path
spec = importlib.util.spec_from_file_location('legacy_export', Path(__file__).with_name('export-legacy.py'))
export = importlib.util.module_from_spec(spec)
spec.loader.exec_module(export)

class LegacyExportTest(unittest.TestCase):
    def decode(self, sql):
        return bytes.fromhex(sql.split("'")[1]).decode('utf-8')
    def test_text_retains_quotes_newlines_and_vietnamese(self):
        value = "Ứng viên O'Brien\nREST API"
        self.assertEqual(self.decode(export.literal(value)), value)
    def test_json_columns_remain_valid_json(self):
        value = ['Java', {'name': 'Kỹ năng', 'enabled': True}]
        self.assertEqual(json.loads(self.decode(export.literal(value))), value)
    def test_null_and_numbers_remain_typed(self):
        self.assertEqual(export.literal(None), 'NULL')
        self.assertEqual(export.literal(5), '5')
        self.assertEqual(export.literal(export.Decimal('1.2500')), '1.2500')

if __name__ == '__main__': unittest.main()
