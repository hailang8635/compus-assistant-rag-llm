## 上海大学「校园百事通」(Local RAG) - 本地运行版

### 你将得到什么
- **ChatGPT 风格聊天前端**：`/`（支持 Markdown 渲染）
- **FAQ 静态页**：`/faq`
- **Embedding RAG（本地向量检索）**：
  - 启动后可对 `docs/*.md` 建立向量索引（SQLite 缓存 + 内存检索）
  - 提问时会自动检索 TopK 文档片段并附带给模型（含来源）
- **教师名录增强**：问题提到老师姓名时，命中 `docs/teachers-ms-shu.json` 并附带教师主页/介绍页链接

### 目录结构
- `docs/`：本地知识文档（已存在）
- `backend/app.py`：FastAPI 后端（`/api/chat`）
- `frontend/`：静态前端（无需编译）

### 运行环境（推荐：MacBook Air M4 / 16GB）
建议使用 **Ollama 本地大模型**（默认配置，无需外网 API）。

### 1) 安装 Ollama（本地LLM）
安装后启动 Ollama，然后拉取一个模型，例如：
- **LLM（推荐，M4/16GB 流畅）**：`qwen2.5:7b`
- **Embedding 模型（RAG 必需）**：`nomic-embed-text`

你可以在终端执行（如已安装可跳过）：

```bash
# 需要具备brew环境
brew install ollama
ollama serve
ollama pull qwen2.5:7b
ollama pull nomic-embed-text
```

### 2) 启动后端（FastAPI）
在仓库根目录：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.app:app --reload --port 8000
```

打开：
- 聊天页：`http://localhost:8000/`
- FAQ：`http://localhost:8000/faq`

### 3) 环境变量（可选）
默认使用本地 Ollama（也可以使用配置文件）：
- `LLM_PROVIDER=ollama`
- `LLM_MODEL=qwen2.5:7b`
- `EMBED_MODEL=nomic-embed-text`
- `RAG_TOP_K=5`
- `RAG_MIN_SCORE=0.38`
- `RAG_MIN_KEYWORD_HITS=1`

推荐用配置文件：复制 `config.example.env` 为 `.env`（仓库根目录），启动时会自动读取：

```bash
cp config.example.env .env
```

可选切换 DeepSeek（需要外网与 Key）：

```bash
export LLM_PROVIDER=deepseek
export DEEPSEEK_API_KEY="你的key"
export DEEPSEEK_BASE_URL="https://api.deepseek.com"
export LLM_MODEL="deepseek-chat"
```

### 4) 建立/查看向量索引（Embedding RAG）
首次运行建议手动建索引（文档大时会花几分钟）：

```bash
curl -X POST http://localhost:8000/api/rag/reindex
```

查看索引状态：

```bash
curl http://localhost:8000/api/rag/status
```

索引会缓存到：`data/rag.sqlite`（下次启动会直接加载，不用重复建）


