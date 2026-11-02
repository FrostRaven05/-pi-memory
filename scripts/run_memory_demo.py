"""每个阶段启动独立 pi 进程，不续接聊天；保留原始 JSONL 与工具回执。"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PROMPTS = {
    'a': '读取当前项目 tests/test_session.py 和 docs/testing-guide.md，调用 session_verify 运行测试。把实际测试路径、运行命令和测试结果保存到项目长期记忆，ID 使用 session-test-entry，sources 包含测试文件、测试说明和 artifacts/session-tests.json。请实际调用 memory_write，返回保存路径和来源。不要修改源码或文档。',
    'b': '从当前项目长期记忆中查找会话测试入口，再读取准确记忆记录，核对当前测试文件和说明是否存在且一致。展示来源、命令和文件核对结果。不要创建或更新记录，不要运行测试；先检索再读当前文件。',
    'c': '先读取当前项目长期记忆中的会话测试入口。然后调用 session_migrate 将测试迁移到 tests/auth/test_session.py 并同步说明，调用 session_verify 运行新测试命令。根据真实结果用 memory_update 更新原记录 session-test-entry，sources 使用迁移后的文件、docs/testing-guide.md 和 artifacts/session-tests.json。最后 memory_read 核对新版本。不要修改业务源码或测试断言。',
    'delete': '验证删除功能：读取 docs/testing-guide.md，以它为来源，用 memory_write 新建临时记录 delete-probe，随后 memory_delete 删除这条临时活动记录，再 memory_search 搜索 delete-probe，确认返回零条。不要删除或修改 session-test-entry。',
}

def main():
    p = argparse.ArgumentParser(); p.add_argument('stage', choices=PROMPTS); a = p.parse_args()
    output = ROOT / 'evidence/memory' / a.stage
    if output.exists(): raise SystemExit(f'Evidence already exists: {output}; use a clean project copy to replay')
    output.mkdir(parents=True)
    pi_cmd = shutil.which('pi.cmd') or shutil.which('pi')
    if not pi_cmd: raise SystemExit('pi not installed')
    cli = Path(pi_cmd).parent / 'node_modules/@earendil-works/pi-coding-agent/dist/cli.js'
    if not cli.exists():
        cli = Path(os.environ.get('HOMEWORK_PI_CLI',''))
    if not cli.is_file(): raise SystemExit('Set HOMEWORK_PI_CLI to installed pi dist/cli.js')
    env = os.environ.copy()
    env['HOMEWORK_PYTHON'] = sys.executable
    env['PYTHONIOENCODING'] = 'utf-8'
    env['PI_CODING_AGENT_DIR'] = str(ROOT.parent / '.pi-runtime')
    argv = ['node',str(cli),'-p','--mode','json','--provider','homework',
        '--model',env.get('HOMEWORK_CHAT_MODEL','deepseek-flash'),'--thinking','off',
        '--session',str(output/'session.jsonl'),'--no-skills','--no-prompt-templates',
        '--tools','read,memory_write,memory_search,memory_read,memory_update,memory_delete,session_verify,session_migrate',PROMPTS[a.stage]]
    (output/'prompt.txt').write_text(PROMPTS[a.stage],encoding='utf-8')
    with (output/'events.jsonl').open('w',encoding='utf-8') as out, (output/'stderr.txt').open('w',encoding='utf-8') as err:
        done = subprocess.run(argv,cwd=ROOT/'login_demo',env=env,stdout=out,stderr=err,timeout=300)
    events = [json.loads(line) for line in (output/'events.jsonl').read_text(encoding='utf-8').splitlines() if line.startswith('{')]
    calls = [e for e in events if e.get('type')=='tool_execution_end']
    answers = [e['message'] for e in events if e.get('type')=='message_end' and e.get('message',{}).get('role')=='assistant']
    final = '\n'.join(x['text'] for x in (answers[-1].get('content',[]) if answers else []) if x.get('type')=='text')
    summary = {'stage':a.stage,'exit_code':done.returncode,
        'session_id':next((e.get('id') for e in events if e.get('type')=='session'),None),
        'tools':[{'name':e['toolName'],'is_error':e.get('isError'), 'result':e.get('result')} for e in calls], 'answer':final}
    (output/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    expected = {'a':{'session_verify','memory_write'},'b':{'memory_search','memory_read','read'},'c':{'session_migrate','session_verify','memory_update','memory_read'},'delete':{'memory_write','memory_delete','memory_search'}}[a.stage]
    successful = {e['toolName'] for e in calls if not e.get('isError')}
    if done.returncode or not expected <= successful or not final: raise SystemExit('Stage incomplete: inspect events and stderr')
    memory = ROOT/'login_demo/.memory/records.json'
    if memory.exists(): shutil.copy2(memory,output/'memory-snapshot.json')
    receipt = ROOT/'login_demo/artifacts/session-tests.json'
    if receipt.exists(): shutil.copy2(receipt,output/'test-receipt.json')

if __name__ == '__main__': main()
