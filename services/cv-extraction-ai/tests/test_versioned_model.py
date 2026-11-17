"""Regression checks for model-version selection, without loading AI dependencies."""
import tempfile
import unittest
from pathlib import Path
from app.services.model_loader import resolve_versioned_gguf_path

class VersionedModelTest(unittest.TestCase):
    def test_missing_v4_does_not_load_available_v3(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'model-v3-q4_k_m.gguf').write_bytes(b'GGUF')
            path, reason = resolve_versioned_gguf_path(str(root / 'model-v4-q4_k_m.gguf'), 'v4')
            self.assertIsNone(path)
            self.assertIn('refusing another version', reason)

    def test_existing_explicit_v4_is_selected(self):
        with tempfile.TemporaryDirectory() as directory:
            model = Path(directory) / 'model-v4-q4_k_m.gguf'
            model.write_bytes(b'GGUF')
            self.assertEqual(resolve_versioned_gguf_path(str(model), 'v4'), (str(model), None))

    def test_legacy_v1_auto_discovery_still_works(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            model = root / 'legacy.gguf'
            model.write_bytes(b'GGUF')
            self.assertEqual(resolve_versioned_gguf_path(str(root / 'missing.gguf'), 'v1'), (str(model), None))

if __name__ == '__main__': unittest.main()
