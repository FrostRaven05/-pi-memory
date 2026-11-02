# 第四章作业

这份作业沿用了课件里的 Python 登录会话示例，完成了两件事：让 pi 在新会话中找回项目记忆，以及用向量和关键词混合检索回答登录规则。两道题的原始运行记录、索引和截图都放在这个目录里。

建议先看 `提交说明.md`，再看 `screenshots`。需要核对细节时，可以打开 `evidence` 下的 JSON 和 pi 会话文件。

## 文件怎么找

- `login_demo/app`：课件中的三个 Python 源文件，未修改。
- `login_demo/tests/auth/test_session.py`：本次补的测试，已经完成迁移。
- `login_demo/.pi/extensions`：pi 的记忆工具和模型配置。
- `login_demo/memory/store.mjs`：记忆的保存、查询、更新、删除。
- `rag`：分块、BGE 向量、中文 BM25、RRF、索引保存和回答生成。
- `data/login_docs`：第二题使用的资料副本，现为 20 分钟版本。
- `fixtures`：迁移前的测试与 30 分钟资料，供重新演示使用。
- `storage`：更新前后两代索引；`current.json` 指向当前版本。
- `evidence`：实际运行记录。`source-reuse.json` 可核对课件源码与提交源码的哈希。

## 环境

本次使用 Windows、Python 3.12、Node.js 22.13.0、pi 0.74.2。Python 的实际依赖版本见 `requirements-lock.txt`。

在本目录安装 Python 依赖：

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements-lock.txt
```

如果 pip 下载很慢，可以加 `--no-cache-dir`，或使用自己信任的镜像。需要安装 pi 时：

```powershell
npm install -g @earendil-works/pi-coding-agent@0.74.2
```

真实回答和 pi 演示读取环境变量 `DEEPSEEK_API_KEY`。密钥不包含在提交包中。本次回答模型是 `deepseek-flash`，也可以通过 `HOMEWORK_CHAT_MODEL` 和 `HOMEWORK_CHAT_BASE_URL` 配置兼容端点。

Embedding 使用 `BAAI/bge-small-zh-v1.5`，由 fastembed 在本地运行。首次使用需要下载权重，之后复用缓存。权重没有放进提交包；`HOMEWORK_MODEL_CACHE` 可指定缓存目录。

## 先查看已经完成的结果

不需要 API 密钥，可以核对已保存的证据：

```powershell
.venv/Scripts/python.exe scripts/verify_submission.py
node --test tests/memory.test.mjs
.venv/Scripts/python.exe -m pytest tests/test_retrieval.py -q
```

登录项目的测试从项目根目录运行：

```powershell
cd login_demo
../.venv/Scripts/python.exe -m pytest tests/auth/test_session.py -q
cd ..
```

现有索引也可以直接查询。下列命令会加载已经保存的索引，不会重新为文档生成向量；查询向量仍需本地 BGE 模型：

```powershell
.venv/Scripts/python.exe -m rag query --no-llm
# 去掉 --no-llm 后会调用真实回答模型
```

## 从头演示两道题

提交目录保留的是“测试已迁移、资料已更新”的最终状态。不要在这里反复覆盖原始证据。先创建一个干净副本，输出目录必须尚不存在：

```powershell
.venv/Scripts/python.exe scripts/prepare_demo.py --output ../homework-replay
```

这个脚本恢复迁移前的测试和 30 分钟资料，不复制旧会话、记忆、截图和索引，也不会删除原提交目录。然后进入新目录，安装依赖并配置密钥。

第一题按顺序运行，每条命令都会启动独立的 pi 进程和新会话：

```powershell
python scripts/run_memory_demo.py a
python scripts/run_memory_demo.py b
python scripts/run_memory_demo.py c
python scripts/run_memory_demo.py delete
```

`a` 读取来源、跑测试并写入；`b` 只读取记忆并核对文件；`c` 迁移测试、复跑并更新原记录；`delete` 新建并删除临时记录。某一阶段已经有证据目录时，脚本会拒绝覆盖。

也可以手动进入 `login_demo` 后运行 `pi --provider homework --model deepseek-flash`，在会话中按题面提出任务。运行前把 `HOMEWORK_PYTHON` 设为安装了 pytest 的 Python 解释器完整路径。扩展放在项目的 `.pi/extensions`，pi 会自动发现。

记忆保存在 `login_demo/.memory/records.json`。项目 ID 绑定规范化根路径，复制到别处后不会默默把旧库认成新项目；因此跨目录复现请使用上述干净副本。删除操作移除活动记录，变更历史仍保留，这里不把它称为彻底擦除。

第二题也在干净副本根目录运行：

```powershell
python -m rag build --output evidence/rag/build-before.json
python -m rag query --output evidence/rag/query-before.json
$previous = (Get-Content storage/current.json -Raw | ConvertFrom-Json).generation
python -m rag update --output evidence/rag/build-after.json
python -m rag query --output evidence/rag/query-after.json
python -m rag check-update --previous $previous --output evidence/rag/update-check.json
python scripts/verify_submission.py
```

`update` 只接受仍为 30 分钟的资料副本，改成 20 分钟后重建两路索引。旧版本留下来用于对比，但不参与默认查询。两路写完并校验后才切换版本，不能只更新向量一路。

## 截图与完整记录

六张截图来自实际回执生成的浏览器页面，不是假装的终端或聊天截图。页面位于 `evidence/pages`，完整 pi 事件在 `evidence/memory/*/events.jsonl`，完整检索结果与模型输入在 `evidence/rag`。截图里为了易读只显示分块摘录，JSON 中保留全文。

要用自己的运行结果重新生成页面：

```powershell
python scripts/build_evidence_pages.py
python scripts/capture_pages.py
```

截图脚本在 Windows 默认使用 Edge 无界面模式；也可通过 `HOMEWORK_BROWSER` 指定兼容 Chromium 浏览器路径。模型配置中的费用字段未维护价格，不用于统计实际费用；调用是否发生以保存的模型响应 ID、用量和工具事件为依据。
