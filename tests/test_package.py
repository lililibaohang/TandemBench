import contextlib
import hashlib
import http.server
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tandembench.runner import load_inputs,parse_response,read_jsonl
from tandembench.scoring import score


class FakeAPI(http.server.BaseHTTPRequestHandler):
    requests=[]
    def log_message(self,*args):pass
    def do_POST(self):
        body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        self.requests.append(body)
        if body['model']=='unauthorized':
            self.send_response(401);self.end_headers();return
        if body['model']=='retry' and len(self.requests)==1:
            self.send_response(429);self.end_headers();return
        n=len(self.requests)%4
        content=['A',r'\boxed{B}','C','No single final answer'][n]
        payload={'choices':[{'message':{'content':content},'finish_reason':'length' if n==2 else 'stop'}],
                 'usage':{'prompt_tokens':10,'completion_tokens':3}}
        self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers()
        self.wfile.write(json.dumps(payload).encode())


class PackageTests(unittest.TestCase):
    def test_data_and_gold_integrity(self):
        items,_=load_inputs(['decision','verification'],0)
        self.assertEqual(len(items),4800)
        for part in ['decision','verification']:
            answers=read_jsonl(ROOT/f'evaluation/{part}/answers.jsonl')
            pred=[]
            for g in answers:
                choice=g['correct_letter'] if part=='decision' else (g['meta_letter'] if g['condition']=='removed' else next(x for x in 'ABCD' if x!=g['meta_letter']))
                pred.append({'id':g['id'],'sample':0,'choice':choice})
            self.assertEqual(score(answers,pred,1)['DA' if part=='decision' else 'VA'],1)

    def test_parser_never_rescues_truncation_or_reasoning(self):
        response=lambda text,finish='stop':{'choices':[{'message':{'content':text},'finish_reason':finish}]}
        self.assertEqual(parse_response(response(r'\boxed{A}'))[0],'A')
        self.assertEqual(parse_response(response('Reasoning discusses B.\nFinal answer: C'))[0],'C')
        self.assertIsNone(parse_response(response('A','length'))[0])
        self.assertIsNone(parse_response(response('<think>A'))[0])
        self.assertIsNone(parse_response(response('A or B'))[0])

    def test_api_resume_retry_and_credentials(self):
        FakeAPI.requests=[]
        server=http.server.ThreadingHTTPServer(('127.0.0.1',0),FakeAPI)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            with tempfile.TemporaryDirectory() as td:
                out=Path(td)/'run'
                env=dict(os.environ,TANDEMBENCH_API_KEY='local-test-credential-do-not-persist')
                cmd=[sys.executable,'-B',str(ROOT/'run.py'),'--base-url',f'http://127.0.0.1:{server.server_port}/v1',
                     '--model','retry','--output',str(out),'--limit','4','--workers','1','--retries','1']
                first=subprocess.run(cmd,env=env,capture_output=True,text=True)
                self.assertEqual(first.returncode,0,first.stderr)
                self.assertEqual(len(FakeAPI.requests),9)
                metrics=json.loads((out/'metrics.json').read_text())
                self.assertEqual(metrics['scope'],'smoke_subset')
                self.assertEqual(metrics['completed_responses'],8)
                self.assertGreater(sum(metrics['invalid'].values()),0)
                for request in FakeAPI.requests:
                    self.assertEqual(set(request),{'model','messages','max_tokens','temperature','stream','n'})
                    self.assertEqual(len(request['messages']),1)
                    self.assertEqual(request['messages'][0]['role'],'user')
                before=(out/'attempts.jsonl').read_bytes()
                resumed=subprocess.run(cmd+['--resume'],env=env,capture_output=True,text=True)
                self.assertEqual(resumed.returncode,0,resumed.stderr)
                self.assertEqual(len(FakeAPI.requests),9)
                self.assertEqual((out/'attempts.jsonl').read_bytes(),before)
                wrong=subprocess.run(cmd+['--resume','--samples','2'],env=env,capture_output=True,text=True)
                self.assertNotEqual(wrong.returncode,0)
                self.assertEqual((out/'attempts.jsonl').read_bytes(),before)
                for file in out.glob('*'):
                    if file.is_file():self.assertNotIn(env['TANDEMBENCH_API_KEY'],file.read_text())
                auth=cmd.copy();auth[auth.index('retry')]='unauthorized';auth[auth.index(str(out))]=str(Path(td)/'auth')
                failed=subprocess.run(auth,env=env,capture_output=True,text=True)
                self.assertEqual(failed.returncode,2)
                incomplete=json.loads((Path(td)/'auth/metrics.json').read_text())
                self.assertEqual(incomplete['status'],'incomplete')
                self.assertNotIn('DA',incomplete['metrics']['decision'])
        finally:
            server.shutdown();server.server_close();thread.join()


if __name__=='__main__':unittest.main()
