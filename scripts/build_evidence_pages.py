"""把真实回执排成六个浏览器页面；页面截图不是伪造的终端或聊天截图。"""
from pathlib import Path
import html
import json

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'evidence/pages'; OUT.mkdir(parents=True,exist_ok=True)
def read(p): return json.loads((ROOT/p).read_text(encoding='utf-8'))
def esc(v): return html.escape(str(v))
def block(title,text): return f'<section><h2>{esc(title)}</h2><pre>{esc(text)}</pre></section>'
def page(name,title,subtitle,body):
    css='''*{box-sizing:border-box}body{margin:0;background:#f3f5f8;color:#172033;font:17px "Microsoft YaHei",sans-serif;padding:36px 48px}header{border-bottom:2px solid #1d5e75;margin-bottom:20px;padding-bottom:15px}h1{font-size:30px;margin:8px 0}h2{font-size:18px;color:#1d5e75;margin:0 0 10px}p{margin:7px 0;color:#516176}section{background:white;border:1px solid #dce3eb;border-radius:10px;padding:18px 22px;margin:12px 0}pre{font:15px/1.55 "Microsoft YaHei",monospace;white-space:pre-wrap;overflow-wrap:anywhere;margin:0}table{width:100%;border-collapse:collapse;font-size:14px}td,th{text-align:left;border-bottom:1px solid #e4e8ef;padding:8px;vertical-align:top}.pill{color:#fff;background:#1d5e75;padding:4px 12px;border-radius:15px;font-size:13px}footer{font-size:13px;color:#667285;margin-top:16px}.columns{display:grid;grid-template-columns:1fr 1fr;gap:14px}'''
    css+='th:first-child{width:52px;white-space:nowrap}'
    content=f'<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>{esc(title)}</title><style>{css}</style><header><span class="pill">第四章作业 · 实际运行记录</span><h1>{esc(title)}</h1><p>{esc(subtitle)}</p></header>{body}<footer>本页由保存的 JSON / JSONL 回执生成；完整原始记录随提交包提供。截图为运行记录页面，不是 pi 聊天界面。</footer></html>'
    (OUT/f'{name}.html').write_text(content,encoding='utf-8')

for stage,title,name in [('a','第一题：写入项目长期记忆','Q1-1'),('b','第一题：全新会话读取与核对','Q1-2'),('c','第一题：迁移测试并更新原记录','Q1-3')]:
    s=read(f'evidence/memory/{stage}/summary.json')
    record=read(f'evidence/memory/{stage}/memory-snapshot.json')['records']['session-test-entry']
    tools=' → '.join(t['name'] for t in s['tools'])
    body=block('真实调用',f'pi 独立会话：{s["session_id"]}\n进程退出码：{s["exit_code"]}\n{tools}')
    body+=block('持久化记录',f'记录：{record["id"]}   revision：{record["revision"]}\n保存路径：{ROOT / "login_demo/.memory/records.json"}\n命令：{record["verification"]["command"]}\n记录的测试退出码：{record["verification"]["exit_code"]}\n来源：'+ '\n'.join(f'{x["path"]}  sha256={x["sha256"][:16]}…' for x in record['sources']))
    if stage=='b':
        checks=next(t['result']['details']['source_checks'] for t in s['tools'] if t['name']=='memory_read')
        body+=block('来源与当前文件对比','\n'.join(f'{x["path"]}：存在={x["exists"]}，哈希一致={x["unchanged"]}' for x in checks)+'\n本轮没有 session_verify 调用；测试通过记录来自前一会话。')
    elif stage=='c':
        receipt=read('evidence/memory/c/test-receipt.json')
        body+=block('迁移后实际测试',receipt['output'])
    else: body+=block('实际测试',read('evidence/memory/a/test-receipt.json')['output'])
    # 最终回答保留原文；B 的长回答另在 summary.json 中完整提供。
    answer=s['answer'] if stage!='b' else s['answer'][:600]+'\n……完整回答见 evidence/memory/b/summary.json'
    body+=block('pi 回答（原文'+('节选' if stage=='b' else '')+'）',answer)
    page(name,title,'DeepSeek 真实模型决策 · 项目内持久存储 · 原始会话文件可追溯',body)

build=read('evidence/rag/build-before.json')
page('Q2-1','第二题：建立两路索引','同一份节点清单 → BGE 向量索引 + jieba / BM25 关键词索引',
    block('建库回执',f'Embedding：{build["embedding_model"]}（真实本地 ONNX 推理）\n维度：{build["dimension"]}\n节点数：{build["node_count"]}\n版本：{build["generation"]}\n存储位置：{build["storage"]}')+
    block('分块来源',json.dumps({k:v for k,v in build['sample'].items() if k not in ['text','score']},ensure_ascii=False,indent=2))+
    block('分块正文',build['sample']['text']))

def tables(q):
    result=''
    for mode,label in [('vector','向量检索'),('bm25','BM25'),('rrf','RRF 混合检索')]:
        rows=''.join(f'<tr><td>{i}</td><td>{x["score"]:.5f}</td><td>{esc(x["file_path"]+" / "+x["heading"])}</td><td>{esc(x["text"].replace(chr(10)," ")[:74])}</td></tr>' for i,x in enumerate(q[mode],1))
        result+=f'<section><h2>{label} · Top-5</h2><table><tr><th>排名</th><th>分数</th><th>来源</th><th>分块摘录</th></tr>{rows}</table></section>'
    return result

q=read('evidence/rag/query-before.json')
page('Q2-2','第二题：三路查询对比与回答',f'问题：{q["question"]}　|　版本：{q["generation"]}',tables(q)+block('真实模型回答',q['answer']+f'\n模型：{q["model"]}\n响应 ID：{q["response_id"]}')+block('本轮引用映射','\n'.join(f'[{i}] {x["file_path"]} / {x["heading"]}' for i,x in enumerate(q['rrf'],1))))
q=read('evidence/rag/query-after.json'); update=read('evidence/rag/update-check.json')
page('Q2-3','第二题：资料改为 20 分钟后重新查询','只更新作业资料副本；课程源码仍保持原来的 30 分钟',
    block('两路同步与旧分块退出',json.dumps(update,ensure_ascii=False,indent=2))+
    block('真实模型回答',q['answer']+f'\n模型：{q["model"]}\n响应 ID：{q["response_id"]}')+
    block('本轮引用的新资料','\n\n'.join(f'[{i}] {q["rrf"][i-1]["file_path"]} / {q["rrf"][i-1]["heading"]}\n{q["rrf"][i-1]["text"]}' for i in sorted(set(q['references'])))))
print(OUT)
