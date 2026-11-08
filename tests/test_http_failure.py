"""Exercise the collector CLI with a real local HTTP 429 response."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class HTTPFailureTests(unittest.TestCase):
    def test_http429_cli_exit_and_report(self):
        probe = Path(__file__).with_name('probe_http429.py').resolve()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'leads.json'
            report = Path(directory) / 'report.json'
            result = subprocess.run(
                [sys.executable, str(probe), '--output', str(output), '--report', str(report)],
                capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            data = json.loads(report.read_text())
            self.assertEqual(data['status'], 'failed')
            self.assertEqual(data['added'], 0)
            self.assertEqual(data['sources'][0]['status'], 'failed')
            self.assertIn('429', data['sources'][0]['error'])
            self.assertFalse(output.exists())
