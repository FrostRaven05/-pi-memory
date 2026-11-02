"""LlamaIndex + BGE + 中文 BM25；两路索引以同一 generation 发布。"""
from __future__ import annotations
import hashlib
import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

import jieba
from fastembed import TextEmbedding
from llama_index.core import VectorStoreIndex, StorageContext, load_index_from_storage
from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.core.schema import TextNode, NodeWithScore
from rank_bm25 import BM25Okapi

ROOT = Path(__file__).resolve().parents[1]
MODEL = 'BAAI/bge-small-zh-v1.5'
QUESTION = '登录会话的有效期是多少分钟？'
_model = None
jieba.setLogLevel(40)

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')

def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def tokenize(text):
    return [t for t in jieba.lcut(text.lower()) if t.strip()]

def model():
    global _model
    if _model is None:
        _model = TextEmbedding(MODEL, cache_dir=os.environ.get('HOMEWORK_MODEL_CACHE', str(ROOT.parent / '.model-cache')))
    return _model

class BGEEmbedding(BaseEmbedding):
    # 复用课件 rag/local_embed.py 的双入口方式，显式记录模型名。
    model_name: str = MODEL
    def _get_query_embedding(self, query):
        return next(model().query_embed([query])).tolist()
    def _get_text_embedding(self, text):
        return next(model().passage_embed([text])).tolist()
    def _get_text_embeddings(self, texts):
        return [v.tolist() for v in model().passage_embed(texts)]
    async def _aget_query_embedding(self, query):
        return self._get_query_embedding(query)

def nodes_from_docs(data: Path, generation: str):
    nodes, sources = [], {}
    for file in sorted(data.rglob('*.md')):
        relative = file.relative_to(data).as_posix()
        raw = file.read_bytes(); source_hash = sha(raw); sources[relative] = source_hash
        text = raw.decode('utf-8')
        text = re.sub(r'\A---\s*\n.*?\n---\s*\n', '', text, flags=re.S)
        title = ''; heading = ''; body = []
        def flush():
            content = '\n'.join(body).strip()
            if not content: return
            # 当前教学资料小节很短，完整保留标题与条件，不人为拆碎规则。
            if len(content) > 6000: raise ValueError(f'Section too large; split explicitly: {relative}/{heading}')
            identity = sha(f'{relative}\n{source_hash}\n{heading}\n{content}'.encode())
            nodes.append(TextNode(id_=identity, text=f'{title}\n{heading}\n{content}', metadata={
                'file_path': relative, 'heading': heading or title, 'source_hash': source_hash,
                'project_id': 'login_demo', 'generation': generation,
            }, excluded_embed_metadata_keys=['source_hash','generation','project_id'],
                excluded_llm_metadata_keys=['source_hash','generation','project_id']))
        for line in text.splitlines():
            if line.startswith('# '):
                flush(); body = []; title = line[2:]; heading = title
            elif line.startswith('## '):
                flush(); body = []; heading = line[3:]
            else: body.append(line)
        flush()
    if not nodes: raise ValueError('No Markdown nodes')
    if len({n.node_id for n in nodes}) != len(nodes): raise ValueError('Duplicate node IDs')
    return nodes, sources

def build(data: Path, storage: Path):
    generation = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + uuid.uuid4().hex[:8]
    target = storage / generation
    nodes, sources = nodes_from_docs(data, generation)
    embed = BGEEmbedding()
    index = VectorStoreIndex(nodes, embed_model=embed, show_progress=False)
    index.storage_context.persist(persist_dir=str(target / 'vector'))
    serialized = [n.to_dict() for n in nodes]
    write_json(target / 'nodes.json', serialized)
    corpus = [tokenize(n.text) for n in nodes]
    bm25 = BM25Okapi(corpus)
    # 保存真实索引统计量，加载时恢复，而不是只把正文留在磁盘。
    write_json(target / 'bm25.json', {'node_ids':[n.node_id for n in nodes],
        'corpus_size':bm25.corpus_size, 'avgdl':bm25.avgdl, 'doc_freqs':bm25.doc_freqs,
        'idf':bm25.idf, 'doc_len':bm25.doc_len, 'k1':bm25.k1, 'b':bm25.b,
        'epsilon':bm25.epsilon, 'average_idf':bm25.average_idf})
    manifest = {'generation':generation, 'embedding_model':MODEL, 'dimension':512,
        'node_ids':[n.node_id for n in nodes], 'node_count':len(nodes), 'sources':sources,
        'tokenizer':'jieba.lcut(lowercase)', 'built_at':datetime.now(timezone.utc).isoformat()}
    manifest['files'] = {p.relative_to(target).as_posix():sha(p.read_bytes()) for p in target.rglob('*') if p.is_file()}
    write_json(target / 'manifest.json', manifest)
    # 完整性校验通过后才切换两路共同指针。
    load_generation(storage, generation)
    pointer = storage / ('current.' + uuid.uuid4().hex + '.tmp')
    write_json(pointer, {'generation':generation})
    os.replace(pointer, storage / 'current.json')
    example = next((n for n in nodes if n.metadata['heading'] == '有效期长度'), nodes[0])
    return {'generation':generation, 'node_count':len(nodes), 'embedding_model':MODEL,
        'dimension':512, 'storage':str(target.resolve()), 'sample':serialize(NodeWithScore(node=example, score=0))}

def load_generation(storage: Path, generation=None):
    generation = generation or read_json(storage / 'current.json')['generation']
    if not re.fullmatch(r'[0-9TZ]+-[a-f0-9]{8}', generation): raise ValueError('Invalid generation')
    target = storage / generation
    manifest = read_json(target / 'manifest.json')
    if manifest['embedding_model'] != MODEL: raise ValueError('Embedding model mismatch: rebuild required')
    for name, expected in manifest['files'].items():
        file = (target / name).resolve()
        if not file.is_relative_to(target.resolve()) or sha(file.read_bytes()) != expected:
            raise ValueError(f'Index integrity check failed: {name}')
    nodes = [TextNode.from_dict(n) for n in read_json(target / 'nodes.json')]
    state = read_json(target / 'bm25.json')
    if state.pop('node_ids') != [n.node_id for n in nodes] or [n.node_id for n in nodes] != manifest['node_ids']:
        raise ValueError('Index node IDs disagree')
    bm25 = object.__new__(BM25Okapi)
    for key, value in state.items(): setattr(bm25, key, value)
    context = StorageContext.from_defaults(persist_dir=str(target / 'vector'))
    index = load_index_from_storage(context, embed_model=BGEEmbedding())
    if set(index.index_struct.nodes_dict.values()) != set(manifest['node_ids']):
        raise ValueError('Vector and BM25 membership disagree')
    return nodes, bm25, index, manifest

def rrf(lists, top_k=5, k=60):
    scores, nodes = {}, {}
    for results in lists:
        seen = set()
        for rank, item in enumerate(results, 1):
            nid = item.node.node_id
            if nid in seen: continue
            seen.add(nid); nodes[nid] = item.node
            scores[nid] = scores.get(nid, 0) + 1 / (k + rank)
    keys = sorted(scores, key=lambda n: (-scores[n], n))[:top_k]
    return [NodeWithScore(node=nodes[n], score=scores[n]) for n in keys]

def serialize(item):
    return {'node_id':item.node.node_id, 'score':float(item.score or 0),
        **item.node.metadata, 'text':item.node.text}

def query(storage: Path, question=QUESTION, generate=True):
    nodes, bm25, index, manifest = load_generation(storage)
    vector = index.as_retriever(similarity_top_k=min(10,len(nodes))).retrieve(question)
    scores = bm25.get_scores(tokenize(question))
    order = sorted(range(len(nodes)), key=lambda i: (-scores[i], nodes[i].node_id))[:10]
    keyword = [NodeWithScore(node=nodes[i], score=float(scores[i])) for i in order]
    hybrid = rrf([vector, keyword])
    result = {'question':question, 'generation':manifest['generation'],
        'vector':[serialize(x) for x in vector[:5]], 'bm25':[serialize(x) for x in keyword[:5]],
        'rrf':[serialize(x) for x in hybrid], 'candidate_k':10, 'rrf_k':60}
    if generate:
        from openai import OpenAI
        key = os.environ.get('DEEPSEEK_API_KEY')
        if not key: raise RuntimeError('DEEPSEEK_API_KEY is required; no fake answer fallback')
        chat_model = os.environ.get('HOMEWORK_CHAT_MODEL', 'deepseek-flash')
        evidence = '\n\n'.join(f'[{i}] {x["file_path"]} / {x["heading"]}\n{x["text"]}' for i,x in enumerate(result['rrf'],1))
        prompt = f'问题：{question}\n\n本轮资料：\n{evidence}\n\n只依据本轮资料回答，结论附[编号]。证据不足就说明不足。区分资料要求与源码实际行为。请用简短中文回答。'
        client = OpenAI(api_key=key, base_url=os.environ.get('HOMEWORK_CHAT_BASE_URL','https://api.deepseek.com'), timeout=60, max_retries=0)
        response = client.chat.completions.create(model=chat_model, messages=[{'role':'user','content':prompt}], temperature=0, max_tokens=500)
        answer = response.choices[0].message.content or ''
        references = [int(x) for x in re.findall(r'\[(\d+)\]', answer)]
        if not references or any(i < 1 or i > len(hybrid) for i in references): raise ValueError(f'Invalid answer citations: {answer}')
        result.update(answer=answer, references=references, model=chat_model, prompt=prompt,
            response_id=response.id, usage=response.usage.model_dump() if response.usage else {})
    return result

def update_to_20(data: Path):
    # 只改当前有效规则和 FAQ；不改课程源文件、实现、历史记录。
    changed = []
    for name in ['docs/session-rules.md','docs/faq.md']:
        p = data / name; before = p.read_text(encoding='utf-8')
        if '30 分钟' not in before: raise ValueError(f'Expected baseline 30 分钟 in {name}')
        after = before.replace('30 分钟','20 分钟')
        p.write_text(after, encoding='utf-8'); changed.append(name)
    return changed

def check_update(storage: Path, previous: str):
    _, _, _, old = load_generation(storage, previous)
    _, _, _, new = load_generation(storage)
    changed_sources = {p for p,h in old['sources'].items() if new['sources'].get(p) != h}
    old_nodes = read_json(storage / previous / 'nodes.json')
    obsolete = {n['id_'] for n in old_nodes if n['metadata']['file_path'] in changed_sources}
    remaining = obsolete.intersection(new['node_ids'])
    if not changed_sources or remaining: raise ValueError('Update did not retire old nodes')
    return {'previous':previous, 'current':new['generation'], 'changed_sources':sorted(changed_sources),
        'retired_node_count':len(obsolete), 'old_nodes_remaining':len(remaining), 'both_indexes_same_nodes':True}
