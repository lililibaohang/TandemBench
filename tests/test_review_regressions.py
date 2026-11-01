import concurrent.futures
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tandembench import runner
from tandembench.scoring import score
from tandembench.api import redact, endpoint


def response(*args):
    return {'kind':'response','response':{'choices':[{'message':{'content':'A'},'finish_reason':'stop'}]}}


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.items,_=runner.load_inputs(['decision'],4)
        self.config={'parts':['decision'],'samples':1,'limit':4,'workers':2,'retries':0}

    def test_corrupt_log_preserves_existing_derived_results(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'run'
            with patch.object(runner,'request_once',side_effect=response):
                runner.evaluate(self.config,self.items,out,'dummy-key',False)
            names=['metrics.json','predictions.jsonl','run_manifest.json','REPORT.md']
            before={n:(out/n).read_bytes() for n in names}
            with (out/'attempts.jsonl').open('a') as f:f.write('{broken json')
            with self.assertRaises(ValueError):runner.evaluate(self.config,self.items,out,'dummy-key',True)
            self.assertEqual(before,{n:(out/n).read_bytes() for n in names})
            self.assertFalse((out/'.running.lock').exists())

    def test_interrupt_drains_inflight_responses_and_marks_run(self):
        def interrupt(_):
            raise KeyboardInterrupt
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'run'
            with patch.object(runner,'request_once',side_effect=response) as client:
                with patch.object(concurrent.futures,'as_completed',side_effect=interrupt):
                    with self.assertRaises(KeyboardInterrupt):runner.evaluate(self.config,self.items,out,'dummy-key',False)
                saved=runner.read_jsonl(out/'attempts.jsonl')
                self.assertEqual(len(saved),2)
                self.assertEqual(json.loads((out/'run_manifest.json').read_text())['status'],'interrupted')
                runner.evaluate(self.config,self.items,out,'dummy-key',True)
                self.assertEqual(client.call_count,4)
                self.assertEqual(len(runner.read_jsonl(out/'attempts.jsonl')),4)

    def test_corrupt_run_manifest_does_not_change_metrics(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'run'
            with patch.object(runner,'request_once',side_effect=response):
                runner.evaluate(self.config,self.items,out,'dummy-key',False)
            before=(out/'metrics.json').read_bytes()
            (out/'run_manifest.json').write_text('{broken')
            with self.assertRaises(ValueError):runner.evaluate(self.config,self.items,out,'dummy-key',True)
            self.assertEqual((out/'metrics.json').read_bytes(),before)

    def test_invalid_scoring_metadata_rejected(self):
        with self.assertRaises(ValueError):score([],[],1)
        with self.assertRaises(ValueError):score([{'id':'a','condition':'removed','meta_letter':None}],[{'id':'a','sample':0,'choice':None}],1)

    def test_escaped_credentials_redacted_after_decoding(self):
        secret='token-example'
        wire='{"nested":["\\u0074oken-example"],"token-example":"echo"}'
        cleaned=redact(json.loads(wire),secret)
        self.assertNotIn(secret,json.dumps(cleaned))
        for url in ['https://user:pass@example.com/v1','https://example.com/v1?key=x']:
            with self.assertRaises(ValueError):endpoint(url)

    def test_scoring_invalid_and_nonoptimal_concrete_choices(self):
        answers=[{'id':'m','condition':'removed','meta_letter':'D'},
                 {'id':'r','condition':'retained','meta_letter':'C'}]
        pred=[{'id':'m','sample':0,'choice':'D'},{'id':'r','sample':0,'choice':'B'}]
        self.assertEqual(score(answers,pred,1)['VA'],1)
        pred[1]['choice']=None
        self.assertEqual(score(answers,pred,1)['VA'],.5)
        with self.assertRaises(ValueError):score(answers,pred[:1],1)
        with self.assertRaises(ValueError):score(answers,[pred[0],pred[0]],1)

    def test_zero_one_and_four_sample_configuration(self):
        answer=[{'id':'q','correct_letter':'A'}]
        pred=[{'id':'q','sample':i,'choice':c} for i,c in enumerate(['A','B','B','B'])]
        self.assertEqual(score(answer,pred,4)['DA'],.25)
        with self.assertRaises(ValueError):score(answer,[],0)


if __name__=='__main__':unittest.main()
