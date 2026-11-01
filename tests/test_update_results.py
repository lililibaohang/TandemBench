import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('update_results',ROOT/'tools/update_results.py')
update=importlib.util.module_from_spec(spec)
spec.loader.exec_module(update)


class ResultsTests(unittest.TestCase):
    def setUp(self):
        pointer=json.loads((ROOT/'results/current.json').read_text())
        self.data=json.loads((ROOT/pointer['summary']).read_text())

    def test_snapshot_matches_readme(self):
        update.validate(self.data)
        for filename,lang in [('README.md','en'),('README_zh-CN.md','zh')]:
            readme=(ROOT/filename).read_text(encoding='utf-8')
            rendered=readme.split(update.START)[1].split(update.END)[0].strip()
            self.assertEqual(rendered,update.table(self.data,lang).strip())

    def test_missing_verification_is_not_invented(self):
        data=copy.deepcopy(self.data)
        row=data['rows'][0]
        data['identification_complete_models']-=1
        data['identification_complete_outputs']-=row['identification_records']
        row['identification_records']=0
        row['oja']=None
        update.validate(data)
        self.assertIn('| — |',update.table(data))

    def test_duplicate_model_is_rejected(self):
        data=copy.deepcopy(self.data);data['rows'][1]['model']=data['rows'][0]['model']
        with self.assertRaises(ValueError):update.validate(data)


if __name__=='__main__':unittest.main()
