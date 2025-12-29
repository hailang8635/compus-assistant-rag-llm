# 上海大学校园百事通系统
_Exported on 2025/12/27 at GMT+8 9:20:15 from Cursor (2.2.43)_

---

**第一次 User**

做一个上海大学的“校园百事通”系统，前端页面模仿chaggpt的交互，后端使用python或者springboot；
本地知识文档在docs目录下；
需要使用本地RAG技术

本机配置为mac air M4芯片，16GB内存；

---

**<-------- Cursor**

目标是搭一个**本地RAG的“上海大学校园百事通”**：前端用 ChatGPT 风格聊天界面，后端用 Python（FastAPI）接入本地 Ollama 做**本地大模型 + 本地向量检索**，知识源只来自 `docs/`。接下来我会先看 `docs/` 里有哪些文件类型与内容，再把项目骨架（backend/frontend/README/一键索引脚本）落地。

Got it：你要的是一个“轻量本地RAG”的第一步——**先在本地 `docs/2025_student_guidance.md` 里做段落匹配**，命中就把“前一段+命中段+后一段”作为上下文一起发给模型。接下来我先确认当前仓库里后端代码是否已经落地（别只是写在 `docs/cursor_.md` 里），然后把这个能力真正实现进后端 `ChatService`。

我先把项目真正“跑起来”的骨架落地：FastAPI 提供 `/api/chat`，并直接托管前端静态页（像 ChatGPT 的聊天 UI）。骨架通了之后再把“学生手册段落匹配+相邻三段拼接”插入到聊天链路里。

```plaintext
fastapi==0.115.6
uvicorn[standard]==0.34.0
pydantic==2.10.4
python-dotenv==1.0.1
httpx==0.28.1

```

```python

def build_system_prompt() -> str:
    return (
        "你是“上海大学校园百事通”的智能助手。\n"
        "你会收到一些【本地资料片段】作为上下文，请优先基于这些资料回答，并给出清晰可执行的步骤。\n"
        "若资料不足，请明确说明不确定，并给出建议的官方咨询路径（学院教务/研究生院/信息办/辅导员等）。\n"
        "输出支持 Markdown。\n"
    )


async def call_ollama(messages: list[dict], model: str) -> str:
    """
    Call local Ollama: https://ollama.com
    """
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    timeout = float(os.getenv("OLLAMA_TIMEOUT", "60"))
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            f"{base_url}/api/chat",
            json={"model": model, "messages": messages, "stream": False},
        )
        resp.raise_for_status()
        data = resp.json()
        return (data.get("message") or {}).get("content", "").strip()


async def call_deepseek(messages: list[dict], model: str) -> str:
    """
    Call DeepSeek (OpenAI-compatible chat/completions).
    """
    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    


```

Nice：后端主链路已经落地了——现在 `/api/chat` 会先做 **guidance 三段命中**，再做 **老师名命中**，把这些本地片段拼进同一次模型调用里。接下来我补齐前端 ChatGPT 风格静态页（含 Markdown 渲染），并写 README 让你在 M4 上用 Ollama 一键跑通。

```html
HTML CODE
```

你可以在终端执行（如已安装可跳过）：

```bash
ollama pull qwen2.5:7b
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
默认使用本地 Ollama：
- `LLM_PROVIDER=ollama`
- `LLM_MODEL=qwen2.5:7b`

可选切换 DeepSeek（需要外网与 Key）：


### 4) 本地RAG（本次实现的匹配策略）
- **Guidance 三段匹配**：把 `docs/2025_student_guidance.md` 按空行切段，基于关键词重叠评分，命中后取相邻三段作为上下文。


```
def build_system_prompt() -> str:
    return (
        "你是“上海大学校园百事通”的智能助手。\n"
        "你会收到一些【本地资料片段】作为上下文，请优先基于这些资料回答，并给出清晰可执行的步骤。\n"
        "若资料不足，请明确说明不确定，并给出建议的官方咨询路径（学院教务/研究生院/信息办/辅导员等）。\n"
        "输出支持 Markdown。\n"
    )

```

我刚试着做一次 Python 编译自检，沙盒环境不允许 Python 往系统缓存目录写入 `pyc`，所以失败了；我改成把 pyc 缓存强制写到仓库目录后再跑一次，这样就能验证代码是否有语法/导入问题。

### 已实现：提问先匹配《`docs/2025_student_guidance.md`》，命中就附带相邻三段给模型
后端 `POST /api/chat` 在收到问题后会：
- **先做本地匹配**：把 `docs/2025_student_guidance.md` 按空行切段，做关键词重叠评分
- **命中则附带上下文**：把“上一段 + 命中段 + 下一段”三段内容拼进同一次模型调用（作为 `【本地资料片段】`）
- **老师名增强**（你之前的需求也一起落地了）：若问题包含 `docs/teachers-ms-shu.json` 里的老师姓名，会把命中的老师链接也附带进去

### 关键文件
- `backend/rag/guidance_match.py`：段落匹配 + 相邻三段拼接
- `backend/app.py`：把命中三段（以及老师名命中）拼到 --------> User message 后再调用模型
- `frontend/index.html` + `frontend/assets/app.js`：ChatGPT 风格 UI，AI 回复 **Markdown 正确渲染**

### 本地启动（Mac M4）
按 `README.md`：
- 启动：`uvicorn backend.app:app --reload --port 8000`
- 打开：`http://localhost:8000/`（聊天）与 `http://localhost:8000/faq`（FAQ）

如果你希望“匹配策略”从关键词重叠升级为更像向量检索（真正的 embedding RAG），我可以下一步把 `docs/` 全量索引成向量库，再做 TopK 检索与引用来源输出。

---

**第2次 --------> User**

使用 embedding RAG + mac m4芯片可流畅运行的llm来跑

---

**<-------- Cursor**

目标是把现在的“关键词段落匹配”升级为**真正的 embedding RAG**：启动时把 `docs/` 文档切块→用本地 Ollama 的 embedding 模型生成向量→本地持久化（SQLite）并加载到内存；提问时先做向量检索 TopK，再把命中文本片段（带来源）一起送给本地 LLM（同样走 Ollama，M4 流畅）。我接下来会新增索引模块、加一个 `/api/rag/reindex` 手动重建接口，并更新 README 推荐的 M4 模型组合。

```python
def _default_embed_model() -> str:
    # Light + common on Apple Silicon
    return os.getenv("EMBED_MODEL", "nomic-embed-text").strip() or "nomic-embed-text"

```

Aha：embedding RAG 已经接进 `/api/chat` 了，并把 README 更新成“推荐：qwen2.5:7b + nomic-embed-text”以及如何 `POST /api/rag/reindex` 建索引。

### 已改成 **Embedding RAG + Mac M4 流畅本地 LLM**
现在系统默认走 **本地 Ollama**：
- **LLM（回答模型）**：默认 `qwen2.5:7b`（M4/16GB 很稳）
- **Embedding（向量模型）**：默认 `nomic-embed-text`
- **RAG**：对 `docs/*.md` 建向量索引（`data/rag.sqlite` 缓存 + 内存 cosine 检索 TopK），命中片段会连同来源一起送入同一次模型调用。

### 你需要做的事（本机运行）
1) 拉模型：
```bash
ollama pull qwen2.5:7b
ollama pull nomic-embed-text
```

2) 启动后端：
```bash
uvicorn backend.app:app --reload --port 8000
```

3) 首次建索引（很关键）：
```bash
curl -X POST http://localhost:8000/api/rag/reindex
```

4) 打开：
- 聊天：`http://localhost:8000/`
- FAQ：`http://localhost:8000/faq`

### 新增接口
- **索引状态**：`GET /api/rag/status`
- **重建索引**：`POST /api/rag/reindex`

如果你希望“索引范围”包含 `docs/*.json`（比如把教师名录也向量化用于模糊匹配），我也可以继续扩展切块与索引器。

```shellscript
ollama pull qwen2.5:7b
ollama pull nomic-embed-text
```

```shellscript
uvicorn backend.app:app --reload --port 8000
```

```shellscript
curl -X POST http://localhost:8000/api/rag/reindex
```

---

**第3次--------> User**

1，日志输出本地资料的匹配情况；
2，日志输出调用大模型的输入输出报文
3，增加使用配置文件的方式设置大模型的url、模型、api_key


---

**<-------- Cursor**

计划：先把后端的配置统一收敛到一个 `.env` 配置文件（URL/模型/API Key 都从这里读），并加入标准日志（命中哪些本地资料、TopK 分数、以及调用大模型的入参/出参）。然后我会跑一次编译自检，确保你一启动就能看到清晰的日志输出。

计划：我会先把 `.env` 配置文件接入（启动时自动读取，统一管理 LLM 的 URL/模型/API Key），然后把日志补齐：每次提问都打印 RAG TopK 命中情况、以及大模型调用的入参/出参（默认截断，避免日志爆炸，可通过开关输出全量）。


Nice：日志链路已经补齐了——现在每次提问都会打印 **RAG TopK 命中/分数**、**教师名命中**、以及 **大模型请求/响应报文**（默认截断，避免过大）。接下来我补一个可复制的配置文件模板（用 `config.example.env`，不受忽略规则影响），你复制成 `.env` 就能生效。

### 已新增 3 个能力
- **1）日志输出本地资料匹配情况**
  - 每次 `/api/chat` 会打印：
    - **RAG 命中**：TopK 的 `source/chunk_index/score`
    - **教师命中**：命中的 `{name,url}` 列表
    - 若无命中也会打印 `none`

- **2）日志输出调用大模型的输入/输出报文**
  - 在 `call_ollama()` / `call_deepseek()` 里会打印：
    - **请求 payload**（model + messages + 其他参数）
    - **响应文本**
  - 默认会按 `LOG_LLM_MAX_CHARS` 截断，避免日志过大

- **3）用配置文件设置大模型 url / 模型 / api_key**
  - 后端启动时会自动读取仓库根目录的 `.env`
  - 我提供了模板：`config.example.env`（复制成 `.env` 即可生效）

### 你怎么用
1) 复制配置模板：
```bash
cp config.example.env .env
```

2) 在 `.env` 里按需改：
- **Ollama**：`OLLAMA_BASE_URL`、`LLM_MODEL`
- **DeepSeek**：`DEEPSEEK_BASE_URL`、`DEEPSEEK_API_KEY`、`LLM_PROVIDER=deepseek`

### 可调日志开关（都在 `.env`）
- **LOG_LEVEL**：`INFO/DEBUG`
- **LOG_LLM_IO**：是否打印大模型入参/出参
- **LOG_LLM_MAX_CHARS**：报文截断长度
- **LOG_MSG_MAX_CHARS**：用户问题截断长度

```shellscript
cp config.example.env .env
```

---

**第4次--------> User**

RAG hits没有精确命中，不要匹配不相关的内容

---

**<-------- Cursor**

计划：我会把 RAG 检索改成“**先召回再过滤**”：先取一批候选（TopN），再按 **相似度阈值** + **关键词重叠** 过滤；如果过滤后为空，就直接认为“未命中”，不再把不相关片段塞给大模型。同时把过滤原因打到日志里，方便你调参。

```python

def _default_embed_model() -> str:
    # Light + common on Apple Silicon
    return os.getenv("EMBED_MODEL", "nomic-embed-text").strip() or "nomic-embed-text"

```

### 已修复：RAG 不再“硬塞”不相关内容
我把检索改成 **召回→过滤→命中才使用**：

- **过滤条件 1：相似度阈值**（`RAG_MIN_SCORE`，默认 `0.38`）
- **过滤条件 2：关键词重叠**（`RAG_MIN_KEYWORD_HITS`，默认 `1`，要求 chunk 至少包含问题中的 1 个关键词片段）
- **过滤后为空**：直接视为 **“未命中”**，不会把无关片段附带给大模型

### 日志也更清晰了
- 命中时：会输出每条命中 `source/chunk_index/score/keyword_hits`
- 未命中时：会输出 `RAG hits: none (filtered)...` 并带上当前阈值参数

### 你可以这样调参（`.env`）
- 更严格（更少误命中）：
  - `RAG_MIN_SCORE=0.45`
  - `RAG_MIN_KEYWORD_HITS=2`
- 更宽松（更容易命中）：
  - `RAG_MIN_SCORE=0.30`
  - `RAG_MIN_KEYWORD_HITS=1`

相关配置已写进 `config.example.env` 和 `README.md`。

