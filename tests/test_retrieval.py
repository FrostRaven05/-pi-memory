import pytest
from llama_index.core.schema import TextNode, NodeWithScore
from rag.pipeline import rrf, nodes_from_docs, tokenize

def item(id): return NodeWithScore(node=TextNode(id_=id,text=id),score=999)

def test_rrf_uses_rank_not_raw_score_and_deduplicates():
    result = rrf([[item('a'),item('b')],[item('b'),item('c')]])
    assert result[0].node.node_id == 'b'
    assert result[0].score == pytest.approx(1/62 + 1/61)
    assert len({x.node.node_id for x in result}) == 3

def test_rule_update_retires_old_source_nodes(tmp_path):
    source = tmp_path/'rules.md'
    source.write_text('# 会话\n## 有效期\n登录有效期 30 分钟。',encoding='utf-8')
    old,_ = nodes_from_docs(tmp_path,'old')
    source.write_text('# 会话\n## 有效期\n登录有效期 20 分钟。',encoding='utf-8')
    new,_ = nodes_from_docs(tmp_path,'new')
    assert set(x.node_id for x in old).isdisjoint(x.node_id for x in new)
    assert '20 分钟' in new[0].text
    assert new[0].metadata['file_path'] == 'rules.md'

def test_chinese_tokenization_is_not_one_sentence():
    parts = tokenize('登录会话的有效期是多少分钟？')
    assert len(parts)>3
    assert '登录' in parts and '有效期' in parts
