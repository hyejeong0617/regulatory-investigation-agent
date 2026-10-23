"""Frozen-v1 evaluation orchestration; no retrieval, prompts or answer logic."""
from __future__ import annotations
import argparse
from collections import Counter
from dataclasses import asdict
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from regulatory_agent.agent import DEFAULT_CONTEXT, Investigator, validate_claims
from regulatory_agent.budget import BudgetLedger, Pricing, nano_usd
from regulatory_agent.cli import save_result, safe_filename
from regulatory_agent.config import Config
from regulatory_agent.corpus import Corpus
from regulatory_agent.llm import OpenAIProvider
from regulatory_agent.util import now, write_json

IDS = ['Q1', 'Q2', 'Q3', 'Q4', 'Q6', 'Q7', 'Q8', 'Q9', 'Q10']
Q5 = ROOT / 'outputs/live-smoke/2026-10-22T18-26-39.920679_00-00/question-Q5-a08c925f.json'

def read(path):
    return json.loads(path.read_text(encoding='utf-8'))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def ledger_snapshot():
    with sqlite3.connect(ROOT / '.state/budget.sqlite3') as db:
        db.row_factory = sqlite3.Row
        calls = [dict(r) for r in db.execute('SELECT * FROM calls ORDER BY time')]
    accounted = sum(r['actual'] if r['actual'] is not None else r['reserved'] for r in calls)
    return {'calls': calls, 'accounted_nano_usd': accounted,
            'remaining_nano_usd': 2_000_000_000 - accounted,
            'known_usage_nano_usd': sum(r['actual'] or 0 for r in calls),
            'unknown_usage_reserved_nano_usd': sum(r['reserved'] for r in calls if r['actual'] is None)}

def config():
    data = read(HERE / 'frozen_manifest.json')['configuration']
    for key in ('source_dir', 'benchmark_file', 'output_dir', 'state_dir', 'pricing_file'):
        data[key] = Path(data[key])
    result = Config(**data)
    result.validate()
    return result

def verify():
    manifest = read(HERE / 'frozen_manifest.json')
    for item in manifest['files']:
        if sha(ROOT / item['path']) != item['sha256']:
            raise RuntimeError('Frozen file changed: ' + item['path'])
    for item in manifest['preserved_q5_files']:
        if sha(ROOT / item['path']) != item['sha256']:
            raise RuntimeError('Preserved Q5 file changed: ' + item['path'])
    return manifest

def preflight(c):
    if not os.getenv('OPENAI_API_KEY', '').strip():
        raise RuntimeError('OPENAI_API_KEY MISSING')
    pricing = Pricing(c.pricing_file, c.model)
    ledger = ledger_snapshot()
    if any(r['state'] in ('pending', 'uncertain') for r in ledger['calls']):
        raise RuntimeError('Unresolved blocking reservation; evaluation stopped without reconciliation')
    reserve = nano_usd(pricing.reserve_cost(pricing.context_window, c.max_output_tokens))
    if ledger['remaining_nano_usd'] < reserve:
        raise RuntimeError('Remaining budget cannot cover the next full request reservation')
    return {'credential': 'SET', 'next_request_reservation_nano_usd': reserve,
            'budget': ledger, 'all_nine_worst_case_guaranteed': False,
            'policy': 'Sequential requests settle usage; frozen ledger checks every request. Stop on any error. No retries or reconciliation.'}

def freeze():
    if (HERE / 'frozen_manifest.json').exists():
        raise RuntimeError('Frozen checkpoint already exists; refusing overwrite')
    env = dict(os.environ, RUN_PAID_TESTS='false', PYTHONIOENCODING='utf-8')
    env.pop('OPENAI_API_KEY', None)
    test = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'],
                          cwd=ROOT, env=env, capture_output=True, text=True, encoding='utf-8')
    (HERE / 'offline_tests.log').write_text(test.stdout + test.stderr, encoding='utf-8')
    if test.returncode:
        raise RuntimeError('Offline tests failed; no freeze or evaluation')
    corpus = Corpus(ROOT / 'data')
    q5 = read(Q5)
    accepted, rejected = validate_claims(q5['assessment']['claims'], corpus.by_id)
    questions = read(ROOT / 'data/benchmark_questions_v1.json')['questions']
    assert q5['question'] == questions['Q5'] and q5['question_id'] == 'Q5'
    assert q5['model'] == 'gpt-6-luna' and q5['reasoning_effort'] == 'medium'
    assert not q5['errors'] and q5['status'] == 'partial' and not rejected
    assert q5['corpus_fingerprint'] == corpus.fingerprint
    budget = ledger_snapshot()
    stored = {r['id']: r for r in budget['calls']}
    for event in q5['events']:
        if event['event'] == 'llm_call':
            assert stored[event['call_id']]['state'] == 'settled'
            assert abs(stored[event['call_id']]['actual'] - nano_usd(event['api_cost_usd'])) <= 1
    c = Config(source_dir=ROOT/'data', benchmark_file=ROOT/'data/benchmark_questions_v1.json',
               output_dir=HERE/'raw', state_dir=ROOT/'.state', run_paid_tests=True,
               max_seconds=600, timeout=120, pricing_file=ROOT/'config/pricing.verified.json')
    c.validate()
    check = preflight(c)
    contexts = {}
    for qid in IDS:
        context = dict(DEFAULT_CONTEXT)
        # Original question text only supplies the anaphoric topic; never answers.
        if qid == 'Q3':
            context.update(preceding_question=questions['Q2'], preceding_answer=None)
        if qid in ('Q9', 'Q10'):
            context['preceding_question_texts'] = {f'Q{i}': questions[f'Q{i}'] for i in range(1, int(qid[1:]))}
            context['preceding_answers_available'] = False
        contexts[qid] = {'question_id': qid, 'question': questions[qid], 'context': context, 'history': []}
    write_json(HERE/'inputs.json', contexts)
    write_json(HERE/'budget_before.json', budget)
    paths = sorted(set(list((ROOT/'regulatory_agent').glob('*.py')) + list((ROOT/'tests').glob('*.py'))
                       + list((ROOT/'config').glob('*.json')) + list((ROOT/'data').glob('*'))
                       + list((ROOT/'scripts').glob('*.py'))
                       + [ROOT/'TASK_BRIEF.md', ROOT/'README.md', ROOT/'CHECKPOINT.md',
                          ROOT/'pyproject.toml', ROOT/'requirements.txt', Path(__file__), HERE/'inputs.json']))
    files = [{'path': p.relative_to(ROOT).as_posix(), 'bytes': p.stat().st_size, 'sha256': sha(p)} for p in paths if p.is_file()]
    q5files = [Q5, Q5.with_suffix('.md'), Q5.with_suffix('.events.jsonl'), Q5.parent/'run_summary.json']
    manifest = {'version': 'Codex-built Regulatory Agent v1', 'frozen_at': now(),
                'configuration': {k:str(v) if isinstance(v,Path) else v for k,v in asdict(c).items()},
                'configuration_basis': 'Successful Q5 smoke: default Config except 600s question deadline and 120s request timeout; output path and accounting purpose differ.',
                'corpus_fingerprint': corpus.fingerprint, 'corpus_documents': corpus.manifest,
                'python': sys.version, 'files': files,
                'source_tree_sha256': hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest(),
                'preserved_q5_files': [{'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p)} for p in q5files],
                'q5_verification': {'status':q5['status'],'errors':q5['errors'],'claims_revalidated':len(accepted),'metrics':q5['metrics'], 'ledger_matched':True},
                'offline_test_exit_code':test.returncode, 'preflight':check,
                'question_ids':IDS, 'context_policy':'Fresh process and empty history per question. Default prescribed case. Original preceding question text for Q3/Q9/Q10 only; no preceding answers or retrieved evidence.'}
    write_json(HERE/'frozen_manifest.json', manifest)
    archive = HERE/'agent-v1-frozen.zip'
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as z:
        for item in files:
            z.write(ROOT/item['path'], item['path'])
        for p in [HERE/'frozen_manifest.json', HERE/'offline_tests.log', HERE/'budget_before.json']:
            z.write(p, p.relative_to(ROOT).as_posix())
    write_json(HERE/'checkpoint_receipt.json', {'path':str(archive),'sha256':sha(archive),'frozen_at':manifest['frozen_at']})
    print(json.dumps({'frozen':True,'credential':'SET','remaining_usd':budget['remaining_nano_usd']/1e9,'next_request_reservation_usd':check['next_request_reservation_nano_usd']/1e9,'q5_verified':True}))

def question(qid):
    if qid not in IDS:
        raise RuntimeError('Question not authorized; Q5 must not be rerun')
    verify()
    c = config()
    preflight(c)
    target = c.output_dir/qid
    target.mkdir(parents=True, exist_ok=False)
    item = read(HERE/'inputs.json')[qid]
    write_json(target/'input.json',item)
    corpus = Corpus(c.source_dir)
    provider = OpenAIProvider(c,purpose='evaluation')
    result = Investigator(corpus,c,provider).run(item['question'],qid,item['context'],history=[])
    save_result(target,result)
    verify()
    print(json.dumps({'question_id':qid,'status':result['status'],'errors':result['errors'],'metrics':result['metrics']}),flush=True)
    return 2 if result['errors'] else 0

def run():
    verify()
    preflight(config())
    lock = HERE/'execution_started.json'
    with lock.open('x',encoding='utf-8') as f:
        json.dump({'started_at':now(),'question_ids':IDS},f)
    progress = {'started_at':now(),'attempted':[],'remaining':IDS.copy(),'stop_reason':None}
    for qid in IDS:
        try:
            verify()
            preflight(config())
        except Exception as e:
            progress['stop_reason'] = str(e)
            break
        proc = subprocess.run([sys.executable,str(Path(__file__)),'question','--id',qid],cwd=ROOT,
                              capture_output=True,text=True,encoding='utf-8',env=dict(os.environ,PYTHONIOENCODING='utf-8'))
        (HERE/(qid+'_execution.log')).write_text(proc.stdout+proc.stderr,encoding='utf-8')
        progress['attempted'].append(qid)
        progress['remaining'].remove(qid)
        write_json(HERE/'progress.json',progress)
        print(proc.stdout,flush=True)
        if proc.returncode:
            progress['stop_reason'] = f'{qid} failed (exit {proc.returncode}); preserved without retry'
            break
    progress['finished_at']=now()
    write_json(HERE/'progress.json',progress)
    print(json.dumps(progress),flush=True)

def report():
    manifest = verify()
    progress = read(HERE/'progress.json')
    rows = []
    for n in range(1,11):
        qid=f'Q{n}'
        p=Q5 if qid=='Q5' else HERE/'raw'/qid/(safe_filename(qid)+'.json')
        row={'question_id':qid,'origin':'previous development smoke' if qid=='Q5' else 'post-freeze evaluation','status':'not_run','json':str(p) if p.exists() else None}
        if p.exists():
            r=read(p)
            counts=Counter(e['action']['tool'] for e in r['events'] if e['event']=='tool_call')
            row.update(status=r['status'],errors=r['errors'],metrics=r['metrics'],markdown=str(p.with_suffix('.md')),
                       events=str(p.with_suffix('.events.jsonl')),accepted_claims=len(r['assessment']['claims']),rejected_claims=len(r['rejected_claims']),
                       unresolved_issues=r['assessment']['unanswered_issues'],limitations=r['limitations'],
                       observed_tools=dict(counts),investigation_rounds=sum(e['event']=='investigation_decision' for e in r['events']),
                       review_rounds=sum(e['event']=='evidence_review' for e in r['events']))
        rows.append(row)
    budget=ledger_snapshot()
    prior=read(HERE/'budget_before.json')
    totals={k:sum(row.get('metrics',{}).get(k) or 0 for row in rows) for k in ('llm_calls','tool_calls','input_tokens','output_tokens','reasoning_tokens','wall_seconds','api_cost_usd')}
    summary={'version':manifest['version'],'frozen_at':manifest['frozen_at'],'source_tree_sha256':manifest['source_tree_sha256'],
             'frozen_hashes_verified_after_execution':True,'generated_at':now(),'questions':rows,'totals':totals,'progress':progress,
             'budget_before':prior,'budget_after':budget,'new_evaluation_accounted_usd':(budget['accounted_nano_usd']-prior['accounted_nano_usd'])/1e9,
             'context_policy':manifest['context_policy'],'grading_performed':False,'q5_rerun':False}
    write_json(HERE/'evaluation_summary.json',summary)
    write_json(HERE/'budget_after.json',budget)
    lines=['# Regulatory Agent v1 evaluation report','',f"Frozen: {manifest['frozen_at']}",f"Source manifest SHA-256: `{manifest['source_tree_sha256']}`",
           '', 'Frozen source hashes were rechecked before every question and after execution. Full hashes/configuration/corpus fingerprint: frozen_manifest.json. Archive: agent-v1-frozen.zip.',
           '', '39 offline tests passed before freezing. Model: gpt-6-luna; reasoning: medium. Limits: 12 model calls, 32 tools, 4 investigation rounds, 6,000 output tokens, 600s/question, 120s/request.',
           '', 'Q5 is the preserved pre-freeze development smoke. Other executed questions are post-freeze, independent processes with empty history. No Gold Standard grading or optimization was performed.',
           '', manifest['context_policy'], '', '| Question | Origin | Status | LLM | Tools | Input | Output | Reasoning | Seconds | Estimated USD |', '|---|---|---|---:|---:|---:|---:|---:|---:|---:|']
    for row in rows:
        m=row.get('metrics',{})
        lines.append('| '+ ' | '.join(str(v) for v in [row['question_id'],row['origin'],row['status'],*[m.get(k,'—') for k in ('llm_calls','tool_calls','input_tokens','output_tokens','reasoning_tokens','wall_seconds','api_cost_usd')]])+' |')
    lines += ['', '## Budget', '', f"New evaluation accounted USD: {summary['new_evaluation_accounted_usd']:.9f}",
              f"Cumulative known-usage estimate USD: {budget['known_usage_nano_usd']/1e9:.9f}",
              f"Retained unknown-usage reservations USD: {budget['unknown_usage_reserved_nano_usd']/1e9:.9f}",
              f"Cumulative charged-or-reserved USD: {budget['accounted_nano_usd']/1e9:.9f} / 2.00",
              f"Remaining budget lower bound USD: {budget['remaining_nano_usd']/1e9:.9f}",
              '', 'The first development transport failure retains its full $0.5295 upper bound. No ledger reset, reconciliation, automatic failed-request retry or model substitution occurred during evaluation. Costs are usage-based estimates, not invoice totals.',
              '', '## Completion and limitations', '', f"Attempted: {', '.join(progress['attempted'])}",f"Remaining: {', '.join(progress['remaining']) or 'None'}",f"Stop reason: {progress['stop_reason'] or 'None'}",
              '', 'Partial status is not an execution error or an accuracy grade. Frozen snapshots, missing external acts, exact-quote checks and same-model review limit conclusions. The frozen workflow may perform its existing single structured-format repair; these events remain logged. Hidden reasoning text is not recorded.',
              '', '## Per-question evidence and workflow observations']
    for row in rows:
        lines += ['', '### '+row['question_id'], '', f"Status: {row['status']}; origin: {row['origin']}"]
        if row['json']:
            lines += [f"JSON: [{Path(row['json']).name}]({Path(row['json']).as_posix()})",f"Markdown: [{Path(row['markdown']).name}]({Path(row['markdown']).as_posix()})",f"Events: {row['events']}",
                      f"Tools: {row['observed_tools']}; investigation rounds: {row['investigation_rounds']}; review rounds: {row['review_rounds']}; accepted claims: {row['accepted_claims']}; rejected claim records: {row['rejected_claims']}",
                      f"Errors: {json.dumps(row['errors'],ensure_ascii=False)}", 'Unresolved issues:']
            lines += ['- '+s for s in row['unresolved_issues']]
    (HERE/'EVALUATION_REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'report':str(HERE/'EVALUATION_REPORT.md'),'statuses':{r['question_id']:r['status'] for r in rows},'budget_accounted_usd':budget['accounted_nano_usd']/1e9,'remaining_usd':budget['remaining_nano_usd']/1e9}))

if __name__=='__main__':
    os.chdir(ROOT)
    if hasattr(sys.stdout,'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser()
    parser.add_argument('mode',choices=['freeze','run','question','report'])
    parser.add_argument('--id')
    args=parser.parse_args()
    if args.mode=='question':
        raise SystemExit(question(args.id))
    globals()[args.mode]()
