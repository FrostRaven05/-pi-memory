"""在不存在的新目录创建干净副本，不删除现有作业和证据。"""
import argparse
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(); p.add_argument('--output',required=True,type=Path); a=p.parse_args()
target=a.output.resolve()
if target.exists() or target.is_relative_to(ROOT):
    raise SystemExit('Choose a non-existing directory outside this submission')
shutil.copytree(ROOT,target,ignore=shutil.ignore_patterns('evidence','screenshots','storage','.memory','artifacts','__pycache__','.pytest_cache','.venv'))
tests=target/'login_demo/tests'
migrated=tests/'auth/test_session.py'
if migrated.exists(): migrated.unlink()  # 只清理刚创建副本内的迁移入口
shutil.copy2(target/'fixtures/test_session.py',tests/'test_session.py')
for file in (target/'login_demo/docs').glob('*.md'):
    file.write_text(file.read_text(encoding='utf-8').replace('tests/auth/test_session.py','tests/test_session.py'),encoding='utf-8')
shutil.copytree(target/'fixtures/login_docs',target/'data/login_docs',dirs_exist_ok=True)
print(target)
