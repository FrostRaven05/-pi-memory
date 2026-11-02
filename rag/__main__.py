import argparse
import json
from pathlib import Path
from .pipeline import ROOT, QUESTION, build, query, update_to_20, check_update, write_json

p = argparse.ArgumentParser()
p.add_argument('action', choices=['build','query','update','check-update'])
p.add_argument('--data', type=Path, default=ROOT/'data/login_docs')
p.add_argument('--storage', type=Path, default=ROOT/'storage')
p.add_argument('--question', default=QUESTION)
p.add_argument('--no-llm', action='store_true')
p.add_argument('--previous')
p.add_argument('--output', type=Path)
a = p.parse_args()
if a.action == 'build': result = build(a.data, a.storage)
elif a.action == 'query': result = query(a.storage, a.question, not a.no_llm)
elif a.action == 'update': result = {'changed':update_to_20(a.data), **build(a.data,a.storage)}
else:
    if not a.previous: p.error('--previous required')
    result = check_update(a.storage,a.previous)
if a.output: write_json(a.output,result)
print(json.dumps(result,ensure_ascii=False,indent=2))
