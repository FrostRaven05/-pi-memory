"""核对真实执行证据，失败时直接退出；不调用模型、不改作业资料。"""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def read(p): return json.loads((ROOT/p).read_text(encoding='utf-8'))
def check(value,message):
    if not value: raise AssertionError(message)

sessions=[read(f'evidence/memory/{s}/summary.json') for s in ['a','b','c','delete']]
check(len({s['session_id'] for s in sessions})==4,'Sessions must be independent')
for s in sessions:
    check(s['exit_code']==0 and s['answer'],f'Incomplete session {s["stage"]}')
    check(not any(t['is_error'] for t in s['tools']),f'Tool failure in {s["stage"]}')
before=read('evidence/memory/a/memory-snapshot.json')['records']['session-test-entry']
after=read('evidence/memory/c/memory-snapshot.json')['records']['session-test-entry']
check(before['revision']==1 and after['revision']==2,'Expected update of same record')
check(after['verification']['exit_code']==0,'Updated tests failed')
check('tests/auth/test_session.py' in after['verification']['command'],'Wrong updated command')
check(not (ROOT/'login_demo/tests/test_session.py').exists(),'Old test path remains')
check(hashlib.sha256((ROOT/'fixtures/test_session.py').read_bytes()).hexdigest()==hashlib.sha256((ROOT/'login_demo/tests/auth/test_session.py').read_bytes()).hexdigest(),'Migration modified tests')
deleted=read('evidence/memory/delete/memory-snapshot.json')['records']
check('delete-probe' not in deleted and 'session-test-entry' in deleted,'Wrong deletion')
q1=read('evidence/rag/query-before.json'); q2=read('evidence/rag/query-after.json')
for q,minutes in [(q1,30),(q2,20)]:
    check(all(len(q[m])==5 for m in ['vector','bm25','rrf']),'Expected Top-5')
    check(str(minutes) in q['answer'],'Wrong answer duration')
    check(q['response_id'] and q['usage'],'Missing real model receipt')
    citations=[q['rrf'][i-1] for i in q['references']]
    check(any(f'{minutes} 分钟' in x['text'] for x in citations),'Citation does not support duration')
update=read('evidence/rag/update-check.json')
check(update['old_nodes_remaining']==0 and update['retired_node_count']>0,'Old nodes remain')
check(q1['generation']!=q2['generation'],'No generation update')
active=read('storage/current.json')['generation']
check(active==q2['generation'],'Query is not for active index')
manifest=read(f'storage/{active}/manifest.json')
for file,expected in manifest['files'].items():
    check(hashlib.sha256((ROOT/'storage'/active/file).read_bytes()).hexdigest()==expected,f'Corrupt index: {file}')
for file,expected in manifest['sources'].items():
    check(hashlib.sha256((ROOT/'data/login_docs'/file).read_bytes()).hexdigest()==expected,f'Stale source: {file}')
for source in read('evidence/source-reuse.json'):
    check(hashlib.sha256((ROOT/source['submission']).read_bytes()).hexdigest()==source['sha256'],'Reused source changed')
print('PASS: independent pi sessions, persistent CRUD, unchanged migrated tests, three retrieval routes, real model answers and updated citations.')
