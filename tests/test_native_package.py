import http.server
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class NativeAPI(http.server.BaseHTTPRequestHandler):
    requests = []

    def log_message(self, *_args):
        pass

    def do_POST(self):
        self.requests.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
        payload = {'answers': {'decision': {
            'type': 'choice',
            'choice': 'A',
            'probabilities': {'A': 0.7, 'B': 0.1, 'C': 0.1, 'D': 0.1},
        }}}
        raw = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(raw)


class NativePackageTests(unittest.TestCase):
    def test_native_runner_request_contract_and_metrics(self):
        NativeAPI.requests = []
        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), NativeAPI)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as td:
                out = Path(td) / 'run'
                env = dict(os.environ, TANDEMBENCH_API_KEY='local-native-test-credential')
                cmd = [sys.executable, '-B', str(ROOT / 'run_native.py'),
                       '--base-url', f'http://127.0.0.1:{server.server_port}/v1',
                       '--model', 'native-test', '--output', str(out), '--part', 'decision',
                       '--limit', '4', '--workers', '1']
                result = subprocess.run(cmd, env=env, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(len(NativeAPI.requests), 4)
                first = NativeAPI.requests[0]
                self.assertEqual(set(first), {'state', 'questions'})
                question = first['questions']['decision']
                self.assertEqual(question['type'], 'choice')
                self.assertEqual(set(question['criteria']), set('ABCD'))
                self.assertEqual(json.loads((out / 'metrics.json').read_text())['status'], 'complete')
                predictions = [json.loads(x) for x in (out / 'predictions.jsonl').read_text().splitlines()]
                self.assertEqual(len(predictions), 4)
                self.assertEqual(predictions[0]['probabilities']['A'], 0.7)
                for path in out.glob('*'):
                    if path.is_file():
                        self.assertNotIn(env['TANDEMBENCH_API_KEY'], path.read_text())
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_native_dry_run(self):
        result = subprocess.run([sys.executable, '-B', str(ROOT / 'run_native.py'),
                                 '--dry-run', '--part', 'verification', '--limit', '4'],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['planned_requests'], 4)


if __name__ == '__main__':
    unittest.main()
