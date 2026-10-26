"""Export transaction, CLI errors and GitHub input boundary checks."""
import csv
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tgden_tools import SourceError
from tgden_tools.__main__ import main
from tgden_tools.export import csv_cell, write_results

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('run_github_tool', ROOT / 'scripts' / 'run_github_tool.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def result(title='Normal'):
    return {'tool': 'groups', 'items': [{'username': 'public_chat', 'title': title}], 'count': 1,
            'source': 'TGDen public catalog keyword search', 'checked_at': '2026-10-26T00:00:00+00:00',
            'scope': 'Catalog metadata', 'limits': {'max_items': 50}}


class ExportTests(unittest.TestCase):
    def test_csv_formula_safety_and_json_preserves_original_values(self):
        values = ['=HYPERLINK("https://evil")', '+SUM(1,2)', '-1+2', '@SUM(1,2)', '\tformula', '\nformula', '\rformula', '  =formula']
        for value in values:
            self.assertEqual(csv_cell(value), "'" + value)
        self.assertEqual(csv_cell('Normal value'), 'Normal value')
        self.assertEqual(csv_cell(None), '')
        with tempfile.TemporaryDirectory() as directory:
            payload = result(values[0])
            write_results(payload, Path(directory) / 'output')
            output = Path(directory) / 'output'
            self.assertEqual(json.loads((output / 'result.json').read_text())['items'][0]['title'], values[0])
            with (output / 'result.csv').open(newline='') as stream:
                self.assertEqual(list(csv.DictReader(stream))[0]['title'], "'" + values[0])
            metadata = json.loads((output / 'metadata.json').read_text())
            self.assertNotIn('items', metadata)
            self.assertEqual(metadata['count'], 1)
            self.assertEqual(set(metadata['files']), {'result.json', 'result.csv', 'metadata.json'})

    def test_export_error_rolls_back_replaced_files(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'output'
            write_results(result('Original'), output)
            originals = {file.name: file.read_bytes() for file in output.iterdir()}
            real_replace = os.replace
            count = 0
            def fail_once(src, dst):
                nonlocal count
                count += 1
                if count == 2:
                    raise OSError('Simulated disk replacement failure')
                return real_replace(src, dst)
            with patch('tgden_tools.export.os.replace', side_effect=fail_once), self.assertRaises(OSError):
                write_results(result('New'), output)
            self.assertEqual({file.name: file.read_bytes() for file in output.iterdir()}, originals)
            self.assertEqual([file.name for file in Path(directory).iterdir()], ['output'])

    def test_new_output_is_not_created_on_staging_error(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'output'
            payload = result()
            payload['items'][0]['bad_float'] = float('nan')
            with self.assertRaises(ValueError):
                write_results(payload, output)
            self.assertFalse(output.exists())

    def test_refuses_result_symlinks(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'output'
            output.mkdir()
            original = Path(directory) / 'unrelated'
            original.write_text('Keep')
            (output / 'result.json').symlink_to(original)
            with self.assertRaises(ValueError):
                write_results(result(), output)
            self.assertEqual(original.read_text(), 'Keep')

    def test_empty_result_csv_still_has_columns(self):
        payload = result()
        payload['items'] = []
        payload['count'] = 0
        with tempfile.TemporaryDirectory() as directory:
            write_results(payload, Path(directory) / 'output')
            self.assertIn('username', (Path(directory) / 'output' / 'result.csv').read_text())

    def test_cli_source_failure_has_nonzero_status_and_preserves_existing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'output'
            write_results(result('Original'), output)
            originals = {file.name: file.read_bytes() for file in output.iterdir()}
            stderr = io.StringIO()
            with patch('tgden_tools.__main__.run_tool', side_effect=SourceError('Source unavailable')), patch('sys.stderr', stderr):
                self.assertEqual(main(['groups', '--query', 'python', '--output', str(output)]), 1)
            self.assertIn('Source unavailable', stderr.getvalue())
            self.assertEqual({file.name: file.read_bytes() for file in output.iterdir()}, originals)

    def test_cli_success_writes_all_files(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'output'
            with patch('tgden_tools.__main__.run_tool', return_value=result()), patch('sys.stdout', io.StringIO()):
                self.assertEqual(main(['groups', '--query', 'python', '--output', str(output)]), 0)
            self.assertEqual(set(file.name for file in output.iterdir()), {'result.json', 'result.csv', 'metadata.json'})


class GitHubBoundaryTests(unittest.TestCase):
    def test_fixed_env_inputs_are_data_and_output_location_is_fixed(self):
        attack = '$(touch /tmp/should-never-run); `id` <script>x</script>'
        env = {'TG_TOOL': 'groups', 'TG_QUERY': attack, 'TG_USERNAME': '', 'TG_COUNTRY': '',
               'TG_CATEGORY': '', 'TG_LIMIT': '2', 'TG_DAYS': '7', 'TG_OUTPUT': '/arbitrary'}
        with patch.object(runner, 'run_tool', return_value=result()) as run, patch.object(runner, 'write_results') as write, patch('sys.stdout', io.StringIO()):
            self.assertEqual(runner.main(env), 0)
        self.assertEqual(run.call_args.kwargs['query'], attack)
        self.assertEqual(write.call_args.args[1], ROOT / 'output')
        self.assertNotIn('output', run.call_args.kwargs)

    def test_invalid_numeric_env_never_fetches_or_writes(self):
        with patch.object(runner, 'run_tool') as run, patch.object(runner, 'write_results') as write, patch('sys.stderr', io.StringIO()):
            self.assertEqual(runner.main({'TG_LIMIT': '1; echo nope'}), 1)
        run.assert_not_called()
        write.assert_not_called()

    def test_source_failure_writes_no_artifact_or_success_summary(self):
        with tempfile.TemporaryDirectory() as directory:
            summary_path = Path(directory) / 'summary'
            with patch.object(runner, 'run_tool', side_effect=SourceError('429')), patch.object(runner, 'write_results') as write, patch('sys.stderr', io.StringIO()):
                self.assertEqual(runner.main({'GITHUB_STEP_SUMMARY': str(summary_path)}), 1)
            write.assert_not_called()
            self.assertFalse(summary_path.exists())

    def test_summary_escapes_html_and_does_not_interpolate_query_or_titles(self):
        payload = result('<script>untrusted title</script>')
        payload['source'] = 'Catalog <script>untrusted source</script>'
        payload['source_url'] = 'https://tgden.com/api/v1/search?q=%29%0Ax&type=chat'
        payload['items'][0]['catalog_url'] = 'https://tgden.com/en/chat/public_chat?utm_source=github'
        summary = runner.summary(payload)
        self.assertNotIn('<script>', summary)
        self.assertNotIn('untrusted title', summary)
        self.assertIn('&lt;script&gt;', summary)
        self.assertIn('[Result 1](https://tgden.com/en/chat/public_chat?', summary)
        self.assertIn('GitHub sign-in required', summary)

    def test_workflow_has_read_only_permissions_pins_and_no_shell_input_interpolation(self):
        body = (ROOT / '.github/workflows/run-tool.yml').read_text()
        self.assertIn('contents: read', body)
        self.assertNotIn('contents: write', body)
        self.assertIn('timeout-minutes: 5', body)
        self.assertIn('retention-days: 1', body)
        self.assertIn('if: success()', body)
        self.assertIn('persist-credentials: false', body)
        self.assertIn('actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1', body)
        self.assertIn('actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9', body)
        self.assertIn('run: python3 scripts/run_github_tool.py', body)
        for line in body.splitlines():
            if '${{ inputs.' in line:
                self.assertRegex(line, r'^          TG_[A-Z]+: ')
        for token in ('schedule:', 'secrets.', 'pip install', 'npm install', 'pull_request_target:'):
            self.assertNotIn(token, body)
        for name in ('groups', 'channels', 'bots', 'lookup', 'classifieds', 'buyer-preview', 'post-search', 'channel-posts'):
            self.assertIn('- ' + name, body)


if __name__ == '__main__':
    unittest.main()
