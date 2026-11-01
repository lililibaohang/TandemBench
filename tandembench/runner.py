"""Versioned API evaluation with append-only attempts and resumable runs."""
import argparse
import concurrent.futures
import getpass
import hashlib
import json
import math
import os
import platform
import sys
import time
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path

from .api import endpoint, request_once
from .answer_parser_v5 import parse_raw, PARSER_VERSION
from .scoring import score

ROOT=Path(__file__).resolve().parents[1]
OPTIONS={'top_p','seed','reasoning_effort','chat_template_kwargs','enable_thinking','max_completion_tokens'}


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def read_jsonl(p):
    with p.open(encoding='utf-8') as f:
        return [json.loads(x) for x in f if x.strip()]


def save(p,obj):
    temp=p.with_suffix(p.suffix+'.tmp')
    temp.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    temp.replace(p)


def parse_response(data):
    response=data['choices'][0]
    content=response['message'].get('content')
    if not isinstance(content,str):
        return None, 'missing_text_content'
    finish=response.get('finish_reason')
    if finish in ('length','max_tokens'):
        return None,'truncated'
    if finish not in (None,'stop','eos','end_turn'):
        return None,'non_final_response'
    letter,_,error=parse_raw({'finish_reason':finish,'raw_completion':content,
        'output_token_ids':[],'eos_token_text':'','eos_token_id':None,'mode':'nonthinking'})
    return letter,error


def load_inputs(parts,limit):
    manifest=json.loads((ROOT/'data/manifest.json').read_text())
    required={f'{folder}/{part}/{name}.jsonl' for folder,name in [('data','inputs'),('evaluation','answers')]
              for part in ('decision','verification')}
    if set(manifest['files'])!=required:
        raise ValueError('Dataset manifest must list exactly the four expected files')
    for name,digest in manifest['files'].items():
        if sha(ROOT/name)!=digest:
            raise ValueError('Dataset integrity check failed: '+name)
    items=[]
    for part in parts:
        rows=read_jsonl(ROOT/f'data/{part}/inputs.jsonl')
        expected=1600 if part=='decision' else 3200
        if len(rows)!=expected or len({r['id'] for r in rows})!=expected:
            raise ValueError('Dataset presentation count or uniqueness mismatch')
        if limit:
            rows=rows[:limit]
        for row in rows:
            if set(row)!={'id','prompt'}:
                raise ValueError('Unexpected model-input fields')
            items.append(dict(row,part=part))
    if len({x['id'] for x in items})!=len(items):
        raise ValueError('Duplicate dataset IDs')
    return items,manifest


def collect_metrics(out,config,items,completed):
    results={'status':'complete' if len(completed)==len(items)*config['samples'] else 'incomplete',
             'scope':'smoke_subset' if config['limit'] else 'full_selected_parts',
             'planned_requests':len(items)*config['samples'],'completed_responses':len(completed),
             'metrics':{},'invalid':dict(Counter(x['parse_error'] for x in completed.values() if x['parse_error']))}
    for part in config['parts']:
        selected={x['id'] for x in items if x['part']==part}
        preds=[{'id':i,'sample':s,'choice':x['choice']} for (i,s),x in completed.items() if i in selected]
        if len(preds)!=len(selected)*config['samples']:
            results['metrics'][part]={'status':'incomplete','completed':len(preds),'expected':len(selected)*config['samples']}
            continue
        # Evaluation labels are loaded only for local scoring, never in the request worker.
        answers=[x for x in read_jsonl(ROOT/f'evaluation/{part}/answers.jsonl') if x['id'] in selected]
        results['metrics'][part]=score(answers,preds,config['samples'])
    save(out/'metrics.json',results)
    rows=[{'id':i,'sample':s,**x} for (i,s),x in sorted(completed.items())]
    temp=out/'predictions.jsonl.tmp'
    temp.write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in rows),encoding='utf-8')
    temp.replace(out/'predictions.jsonl')
    md=['# TandemBench API evaluation','',f"Status: {results['status']}; scope: {results['scope']}",
        f"Responses: {len(completed)} / {results['planned_requests']}",'','| Metric | Percent |','|---|---:|']
    for part,value in results['metrics'].items():
        for name in ('DA','VA'):
            if name in value:md.append(f"| {name} | {100*value[name]:.2f} |")
    md+=['','No score is issued for an incomplete part. Invalid/truncated model answers count as wrong; transport failures are separately recorded. Subset scores are smoke tests, not benchmark results.','']
    (out/'REPORT.md').write_text('\n'.join(md))
    return results


def evaluate(config,items,out,key,resume):
    if out.exists() and not resume:
        raise ValueError('Output directory exists; use --resume or a new --output')
    if resume and not (out/'config.json').exists():
        raise ValueError('No resumable configuration at --output')
    out.mkdir(parents=True,exist_ok=True)
    lock=out/'.running.lock'
    fd=os.open(lock,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    os.write(fd,str(os.getpid()).encode());os.close(fd)
    completed={}; attempts=Counter()
    recovery_validated=False
    exit_status=None
    try:
        if resume:
            if json.loads((out/'config.json').read_text())!=config:
                raise ValueError('Resume configuration/code/data differs; use the original settings or a new output')
            manifest=json.loads((out/'run_manifest.json').read_text())
            if not isinstance(manifest,dict) or 'started_at' not in manifest or 'status' not in manifest:
                raise ValueError('Invalid run manifest; restore it before resuming')
        else:
            save(out/'config.json',config)
            save(out/'run_manifest.json',{'started_at':datetime.now(timezone.utc).isoformat(),
                'python':platform.python_version(),'parser':PARSER_VERSION,'status':'running',
                'note':'Independent API run, not automatically adopted into the paper leaderboard'})
            (out/'EXPERIMENT_CARD.md').write_text('# API evaluation\n\nProtocol and model are fixed in config.json. Raw attempts are append-only in attempts.jsonl. The input contains the unchanged benchmark prompt, not evaluation labels. Metrics use all requested positions and samples; no voting or selection among successful retries.\n')
        logfile=out/'attempts.jsonl'
        if logfile.exists():
            for row in read_jsonl(logfile):
                if (not isinstance(row,dict) or row.get('kind') not in ('response','error')
                        or type(row.get('sample')) is not int or not isinstance(row.get('id'),str)):
                    raise ValueError('Invalid attempt log record')
                job=(row['id'],row['sample']);attempts[job]+=1
                if row['kind']=='response':
                    if job in completed:raise ValueError('Duplicate completed response in attempt log')
                    letter,error=parse_response(row['response'])
                    completed[job]={'choice':letter,'parse_error':error,'part':row['part']}
        valid={(x['id'],s) for x in items for s in range(config['samples'])}
        if not set(attempts)<=valid:raise ValueError('Unknown job in saved log')
        recovery_validated=True
        jobs=[(x,s) for x in items for s in range(config['samples']) if (x['id'],s) not in completed]
        # Only one bounded wave is in flight; authentication errors stop later waves.
        with logfile.open('a',encoding='utf-8') as log, concurrent.futures.ThreadPoolExecutor(max_workers=config['workers']) as pool:
            def record(item,sample,result):
                job=(item['id'],sample);attempts[job]+=1
                row={'id':item['id'],'part':item['part'],'sample':sample,'attempt':attempts[job],
                     'timestamp':datetime.now(timezone.utc).isoformat(),**result}
                log.write(json.dumps(row,ensure_ascii=False)+'\n');log.flush();os.fsync(log.fileno())
                if result['kind']=='response':
                    letter,error=parse_response(result['response'])
                    completed[job]={'choice':letter,'parse_error':error,'part':item['part']}
            for start in range(0,len(jobs),config['workers']):
                pending=jobs[start:start+config['workers']]
                fatal_status=None
                for retry in range(config['retries']+1):
                    futures={pool.submit(request_once,config,item['prompt'],key):(item,s) for item,s in pending}
                    pending=[]
                    recorded=set()
                    def result_of(future):
                        try:
                            return future.result()
                        except Exception as exc:
                            return {'kind':'error','error':'worker_exception',
                                    'exception_type':type(exc).__name__,'retryable':False}
                    try:
                        for future in concurrent.futures.as_completed(futures):
                            item,s=futures[future];result=result_of(future);record(item,s,result)
                            recorded.add(future)
                            if result.get('http_status') in (400,401,403,404,405,413,422):
                                fatal_status=result['http_status']
                            if result.get('retryable') and retry<config['retries']:pending.append((item,s))
                    except KeyboardInterrupt:
                        print('Stopping after the in-flight batch is saved; please wait for request timeouts.',file=sys.stderr)
                        for future,(item,s) in futures.items():
                            if future not in recorded and (item['id'],s) not in completed:
                                record(item,s,result_of(future))
                        raise
                    if not pending or fatal_status:break
                    time.sleep(min(2**retry,8))
                print(f"Responses {len(completed)}/{len(valid)}",flush=True)
                if fatal_status:
                    print(f'HTTP {fatal_status}; stopping. Check endpoint, credentials, model and request options.',file=sys.stderr)
                    break
    except BaseException as exc:
        exit_status='interrupted' if isinstance(exc,KeyboardInterrupt) else 'failed'
        raise
    finally:
        try:
            # Failed recovery must never overwrite existing derived results.
            if recovery_validated:
                result=collect_metrics(out,config,items,completed)
                manifest=json.loads((out/'run_manifest.json').read_text())
                manifest.update(status=exit_status or result['status'],
                    updated_at=datetime.now(timezone.utc).isoformat(),
                    attempt_log_sha256=sha(out/'attempts.jsonl') if (out/'attempts.jsonl').exists() else None,
                    metrics_sha256=sha(out/'metrics.json'))
                save(out/'run_manifest.json',manifest)
        finally:
            lock.unlink(missing_ok=True)
    result=json.loads((out/'metrics.json').read_text())
    return 0 if result['status']=='complete' else 2


def main():
    p=argparse.ArgumentParser(description='Run TandemBench against an OpenAI-compatible Chat Completions API.')
    p.add_argument('--base-url');p.add_argument('--model');p.add_argument('--api-key-env',default='TANDEMBENCH_API_KEY')
    p.add_argument('--output',type=Path,default=Path('runs')/datetime.now().strftime('%Y%m%d-%H%M%S'))
    p.add_argument('--part',choices=['all','decision','verification'],default='all')
    p.add_argument('--samples',type=int,default=1);p.add_argument('--workers',type=int,default=4)
    p.add_argument('--max-tokens',type=int,default=16384);p.add_argument('--temperature',type=float,default=0)
    p.add_argument('--timeout',type=float,default=180);p.add_argument('--retries',type=int,default=2)
    p.add_argument('--limit',type=int,default=0,help='Per-part limit for smoke tests; 0 means all')
    p.add_argument('--request-options',type=Path,help='Optional JSON containing supported provider-specific generation options')
    p.add_argument('--resume',action='store_true');p.add_argument('--dry-run',action='store_true')
    a=p.parse_args()
    if not math.isfinite(a.timeout) or min(a.samples,a.workers,a.max_tokens,a.timeout)<=0 or a.retries<0 or a.limit<0:
        p.error('Positive samples/workers/max-tokens/timeout and nonnegative retries/limit required')
    if not 0<=a.temperature<=2:p.error('temperature must be in [0,2]')
    options=json.loads(a.request_options.read_text()) if a.request_options else {}
    if not isinstance(options,dict) or set(options)-OPTIONS:p.error('Unsupported request-options keys')
    for name in ('seed','max_completion_tokens'):
        if name in options and (type(options[name]) is not int or (name=='max_completion_tokens' and options[name]<=0)):
            p.error(name+' must be an integer (token budget must be positive)')
    if 'top_p' in options and (type(options['top_p']) not in (int,float) or not 0<options['top_p']<=1):
        p.error('top_p must be in (0,1]')
    if 'enable_thinking' in options and type(options['enable_thinking']) is not bool:
        p.error('enable_thinking must be boolean')
    if 'chat_template_kwargs' in options and not isinstance(options['chat_template_kwargs'],dict):
        p.error('chat_template_kwargs must be an object')
    if 'reasoning_effort' in options and (not isinstance(options['reasoning_effort'],str) or not options['reasoning_effort']):
        p.error('reasoning_effort must be a nonempty string')
    parts=['decision','verification'] if a.part=='all' else [a.part]
    items,manifest=load_inputs(parts,a.limit)
    if a.dry_run:
        print(json.dumps({'parts':parts,'presentations':len(items),'planned_requests':len(items)*a.samples,
              'scope':'smoke_subset' if a.limit else 'full_selected_parts','data_hashes_verified':True},indent=2));return 0
    base=a.base_url or input('API base URL (including /v1 if required): ').strip()
    model=a.model or input('Model name: ').strip()
    if not model:raise ValueError('Model name is required')
    key=os.environ.get(a.api_key_env) or getpass.getpass('API key (hidden; not saved): ')
    if not key:raise ValueError('API key is required (local no-auth servers can use a dummy value)')
    config={'protocol':'chat-completions-four-position-v1','endpoint':endpoint(base),'model':model,
        'parts':parts,'samples':a.samples,'workers':a.workers,'max_tokens':a.max_tokens,
        'temperature':a.temperature,'timeout':a.timeout,'retries':a.retries,'limit':a.limit,
        'request_options':options,'data_manifest_sha256':sha(ROOT/'data/manifest.json'),
        'code_sha256':{x.name:sha(x) for x in sorted((ROOT/'tandembench').glob('*.py'))}}
    print(f"Planned requests: {len(items)*a.samples}; output: {a.output}")
    return evaluate(config,items,a.output,key,a.resume)
