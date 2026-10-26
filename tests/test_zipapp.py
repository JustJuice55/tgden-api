"""The downloadable app contains only the runnable public package and license."""
import importlib.util
import io
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build_zipapp', ROOT / 'scripts' / 'build_zipapp.py')
packager = importlib.util.module_from_spec(spec)
spec.loader.exec_module(packager)


class ZipappTests(unittest.TestCase):
    def test_download_builds_runs_and_excludes_caches_and_other_repo_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(ROOT / 'tgden_tools', root / 'tgden_tools')
            shutil.copy2(ROOT / 'LICENSE', root / 'LICENSE')
            (root / 'private.txt').write_text('Not a runtime file')
            cache = root / 'tgden_tools' / '__pycache__'
            cache.mkdir(exist_ok=True)
            (cache / 'private.pyc').write_text('Exclude')
            with patch.object(packager, '__file__', str(root / 'scripts' / 'build_zipapp.py')), patch('sys.stdout', io.StringIO()):
                archive = packager.build()
            with zipfile.ZipFile(archive) as bundle:
                names = bundle.namelist()
                self.assertIn('__main__.py', names)
                self.assertIn('tgden_tools/core.py', names)
                self.assertIn('LICENSE', names)
                self.assertTrue(all(name == '__main__.py' or name == 'LICENSE' or name.startswith('tgden_tools/') for name in names))
                self.assertFalse(any('__pycache__' in name or name.endswith(('.pyc', '.pyo')) for name in names))
            smoke = subprocess.run([sys.executable, str(archive), '--help'], cwd=root, capture_output=True, text=True, timeout=10)
            self.assertEqual(smoke.returncode, 0, smoke.stderr)
            self.assertIn('channel-posts', smoke.stdout)
            self.assertIn('buyer-preview', smoke.stdout)


if __name__ == '__main__':
    unittest.main()
