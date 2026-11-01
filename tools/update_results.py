"""Adopt an audited project result table and render the README leaderboard."""
import argparse
import hashlib
import json
from collections import Counter
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
START='<!-- RESULTS_START -->'
END='<!-- RESULTS_END -->'
FIELDS=('model','display_name','model_group','global_acc_rank','table_params_display',
        'mean_output_tokens','main_accuracy','oja','main_records','identification_records','source_result')


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def save(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    tmp.replace(path)


def validate(data):
    rows=data['rows']
    if len(rows)!=data['main_models'] or len({r['model'] for r in rows})!=len(rows):
        raise ValueError('Model count or identity mismatch')
    if sorted(r['global_acc_rank'] for r in rows)!=list(range(1,len(rows)+1)):
        raise ValueError('Invalid global ranks')
    if Counter(r['model_group'] for r in rows)!=data['model_groups']:
        raise ValueError('Model group counts mismatch')
    ranked=sorted(rows,key=lambda r:r['global_acc_rank'])
    if any(a['main_accuracy']<b['main_accuracy'] for a,b in zip(ranked,ranked[1:])):
        raise ValueError('Ranks are inconsistent with decision accuracy')
    if sum(r['main_records'] for r in rows)!=data['main_outputs']:
        raise ValueError('Decision output count mismatch')
    if sum(r.get('identification_records') or 0 for r in rows)!=data['identification_complete_outputs']:
        raise ValueError('Verification output count mismatch')
    if sum(r.get('oja') is not None for r in rows)!=data['identification_complete_models']:
        raise ValueError('Verification model count mismatch')
    for r in rows:
        for metric in ('main_accuracy','oja'):
            value=r.get(metric)
            if value is None and metric=='oja':continue
            if isinstance(value,bool) or not isinstance(value,(int,float)) or not 0<=value<=1:
                raise ValueError('Invalid score in '+r['model'])
        if r['model_group'] not in ('native_decision','open_general'):
            raise ValueError('Unknown model group')
        if r['model_group']=='open_general' and (not isinstance(r.get('mean_output_tokens'),(int,float)) or r['mean_output_tokens']<0):
            raise ValueError('Missing or invalid average output length: '+r['model'])


def table(data):
    pct=lambda x: '—' if x is None else str((Decimal(str(x))*100).quantize(Decimal('.01'),rounding=ROUND_HALF_UP))
    lines=[f"**评测结果截至：{data['evaluation_date']}**",'']
    for group,title in [('native_decision','决策模型'),('open_general','通用模型')]:
        column='Params. (B)' if group=='native_decision' else 'Avg. output tokens'
        lines += [f'### {title}','','| Rank | Model | '+column+' | DA ↑ | VA ↑ |','|---:|---|---:|---:|---:|']
        for r in sorted((x for x in data['rows'] if x['model_group']==group),key=lambda x:x['global_acc_rank']):
            model=str(r['display_name']).replace('|','\\|')
            detail=(str(r.get('table_params_display') or '—').replace('|','\\|') if group=='native_decision'
                    else format(int(Decimal(str(r['mean_output_tokens'])).quantize(Decimal('1'),rounding=ROUND_HALF_UP)),','))
            lines.append(f"| {r['global_acc_rank']} | {model} | {detail} | {pct(r['main_accuracy'])} | {pct(r.get('oja'))} |")
        lines.append('')
    return '\n'.join(lines)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True,help='Reviewed main-table-results.json')
    p.add_argument('--workspace',type=Path,required=True,help='Workspace root for source-hash verification')
    p.add_argument('--date',required=True,help='Last evaluation date: YYYY-MM-DD')
    p.add_argument('--snapshot-id',required=True,help='New immutable snapshot ID')
    a=p.parse_args();date.fromisoformat(a.date)
    if not a.snapshot_id or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for c in a.snapshot_id):
        p.error('snapshot-id must contain only letters, numbers, - or _')
    root=a.workspace.resolve();raw=a.source.read_bytes();data=json.loads(raw);validate(data)
    sources=data['sources']+[data['output_length_source']]
    for entry in sources:
        path=(root/entry['path']).resolve()
        if not path.is_relative_to(root) or not path.is_file() or sha(path)!=entry['sha256']:
            raise ValueError('Source hash mismatch: '+entry['path'])
    if a.source.read_bytes()!=raw:raise ValueError('Source table changed during validation')
    readme=ROOT/'README.md';text=readme.read_text(encoding='utf-8')
    if text.count(START)!=1 or text.count(END)!=1:raise ValueError('README must have one results marker pair')
    target=ROOT/'results/snapshots'/a.snapshot_id
    if target.exists():raise ValueError('Snapshot already exists; choose a new ID')
    snapshot={k:data[k] for k in ('source_result_id','main_models','main_outputs','identification_complete_models','identification_complete_outputs','model_groups')}
    snapshot.update(snapshot_id=a.snapshot_id,evaluation_date=a.date,
        source_table_sha256=hashlib.sha256(raw).hexdigest(),rows=[{k:r.get(k) for k in FIELDS} for r in data['rows']])
    # Validate fully before creating a new immutable snapshot.
    rendered=table(snapshot)
    target.mkdir(parents=True)
    save(target/'summary.json',snapshot)
    save(ROOT/'results/current.json',{'snapshot_id':a.snapshot_id,
        'summary':str((target/'summary.json').relative_to(ROOT)), 'sha256':sha(target/'summary.json')})
    readme.write_text(text.split(START)[0]+START+'\n'+rendered+END+text.split(END,1)[1],encoding='utf-8')
    manifest_path=ROOT/'PACKAGE_MANIFEST.json';manifest=json.loads(manifest_path.read_text())
    for file in [readme,ROOT/'results/current.json',target/'summary.json',Path(__file__)]:
        manifest['files'][str(file.relative_to(ROOT))]=sha(file)
    manifest['files']=dict(sorted(manifest['files'].items()));save(manifest_path,manifest)
    print(f"Adopted {len(snapshot['rows'])} models in {a.snapshot_id}; README updated.")


if __name__=='__main__':main()
