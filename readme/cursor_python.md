# 上海大学校园百事通系统
_Exported on 2025/12/27 at GMT+8 9:20:15 from Cursor (2.2.43)_

---

**User**

做一个上海大学的“校园百事通”系统，前端页面模仿chaggpt的交互，后端使用python或者springboot；
本地知识文档在docs目录下；
需要使用本地RAG技术

本机配置为mac air M4芯片，16GB内存；

---

**Cursor**

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
from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

import httpx
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.rag.guidance_match import GuidanceMatchService
from backend.rag.teacher_match import TeacherMatchService


APP_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = APP_ROOT.parent
DOCS_DIR = REPO_ROOT / "docs"
FRONTEND_DIR = REPO_ROOT / "frontend"


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, description="User message")


class ChatResponse(BaseModel):
    type: Literal["answer", "human"]
    answer: str


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
    if not api_key:
        return "系统未配置 `DEEPSEEK_API_KEY`，无法调用 DeepSeek。请先配置环境变量后重试。"
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
    timeout = float(os.getenv("DEEPSEEK_TIMEOUT", "60"))
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": model, "messages": messages, "temperature": 0.3},
        )
        resp.raise_for_status()
        data = resp.json()
        return (((data.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()


def get_llm_provider() -> str:
    return os.getenv("LLM_PROVIDER", "ollama").strip().lower()


def get_llm_model() -> str:
    # Good defaults for Apple Silicon: qwen2.5:7b / llama3.1:8b
    return os.getenv("LLM_MODEL", "qwen2.5:7b").strip()


app = FastAPI(title="SHU Campus Assistant (Local RAG)")

# Static frontend
FRONTEND_DIR.mkdir(exist_ok=True)
app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIR / "assets")), name="assets")


@app.get("/")
def index():
    index_file = FRONTEND_DIR / "index.html"
    if not index_file.exists():
        return {"error": "frontend/index.html not found"}
    return FileResponse(str(index_file))


@app.get("/faq")
def faq():
    faq_file = FRONTEND_DIR / "faq.html"
    if not faq_file.exists():
        return {"error": "frontend/faq.html not found"}
    return FileResponse(str(faq_file))


guidance_service = GuidanceMatchService(guidance_path=DOCS_DIR / "2025_student_guidance.md")
teacher_service = TeacherMatchService(teachers_json_path=DOCS_DIR / "teachers-ms-shu.json")


@app.get("/api/health")
def health():
    return {"ok": True}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    msg = (req.message or "").strip()
    if msg == "人工":
        return ChatResponse(type="human", answer="请联系学长：zhangdreamer@126.com")

    context_blocks: list[str] = []

    # Feature: guidance match -> add neighbor 3 paragraphs
    g = guidance_service.match_with_neighbors(msg)
    if g:
        context_blocks.append(
            "【本地资料片段：2025_student_guidance.md（相邻三段）】\n" + g.strip()
        )

    # Feature: teacher mention -> add teacher info
    t = teacher_service.build_teacher_context_if_mentioned(msg)
    if t:
        context_blocks.append(t.strip())

    context = "\n\n".join(context_blocks).strip()
    user_content = msg if not context else f"{context}\n\n【用户问题】\n{msg}"

    messages = [
        {"role": "system", "content": build_system_prompt()},
        {"role": "user", "content": user_content},
    ]

    provider = get_llm_provider()
    model = get_llm_model()

    try:
        if provider == "deepseek":
            answer = await call_deepseek(messages, model=model)
        else:
            answer = await call_ollama(messages, model=model)
    except Exception as e:
        return ChatResponse(type="answer", answer=f"调用模型失败：{type(e).__name__}: {e}")

    if not answer:
        answer = "（模型返回为空）"
    return ChatResponse(type="answer", answer=answer)


```

```python
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


def _split_to_paragraphs(text: str) -> list[str]:
    # Split by blank lines (one or more)
    raw = re.split(r"\n\s*\n+", text.replace("\r\n", "\n"))
    out: list[str] = []
    for p in raw:
        s = (p or "").strip()
        if not s:
            continue
        # skip pure separators
        if re.fullmatch(r"[#\-=*_ \t]+", s):
            continue
        out.append(s)
    return out


def _extract_keywords(msg: str) -> list[str]:
    # Chinese 2-4 chars + alnum words
    zh = re.findall(r"[\u4e00-\u9fff]{2,4}", msg)
    en = re.findall(r"[A-Za-z0-9]{2,}", msg.lower())

    kws: list[str] = []
    seen = set()
    for k in zh + en:
        if k in seen:
            continue
        seen.add(k)
        kws.append(k)

    stop = {"什么", "怎么", "如何", "可以", "是否", "老师", "同学", "上海", "大学", "校园"}
    kws = [k for k in kws if k not in stop]
    kws.sort(key=len, reverse=True)
    return kws[:12]


def _score_paragraph(p: str, keywords: list[str]) -> int:
    return sum(1 for k in keywords if k and (k in p))


@dataclass
class GuidanceMatchService:
    guidance_path: Path
    min_score: int = 2

    _paragraphs: list[str] | None = None
    _mtime: float | None = None

    def _reload_if_needed(self) -> None:
        if not self.guidance_path.exists():
            self._paragraphs = []
            self._mtime = None
            return
        mtime = self.guidance_path.stat().st_mtime
        if self._paragraphs is not None and self._mtime == mtime:
            return
        text = self.guidance_path.read_text(encoding="utf-8", errors="ignore")
        self._paragraphs = _split_to_paragraphs(text)
        self._mtime = mtime

    def match_with_neighbors(self, user_message: str) -> str | None:
        msg = (user_message or "").strip()
        if not msg:
            return None
        self._reload_if_needed()
        paragraphs = self._paragraphs or []
        if not paragraphs:
            return None

        keywords = _extract_keywords(msg)
        if not keywords:
            return None

        best_idx = -1
        best_score = 0
        for i, p in enumerate(paragraphs):
            score = _score_paragraph(p, keywords)
            if score > best_score:
                best_score = score
                best_idx = i

        if best_idx < 0 or best_score < self.min_score:
            return None

        start = max(0, best_idx - 1)
        end = min(len(paragraphs) - 1, best_idx + 1)
        return "\n\n".join(paragraphs[start : end + 1]).strip()


```

```python
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TeacherMatchService:
    teachers_json_path: Path
    max_hits: int = 3

    _teacher_map: dict[str, str] | None = None
    _mtime: float | None = None

    def _reload_if_needed(self) -> None:
        if not self.teachers_json_path.exists():
            self._teacher_map = {}
            self._mtime = None
            return
        mtime = self.teachers_json_path.stat().st_mtime
        if self._teacher_map is not None and self._mtime == mtime:
            return
        try:
            raw = self.teachers_json_path.read_text(encoding="utf-8", errors="ignore")
            data = json.loads(raw) if raw.strip() else {}
            if isinstance(data, dict):
                self._teacher_map = {str(k).strip(): str(v).strip() for k, v in data.items() if str(k).strip()}
            else:
                self._teacher_map = {}
            self._mtime = mtime
        except Exception:
            self._teacher_map = {}
            self._mtime = mtime

    def build_teacher_context_if_mentioned(self, user_message: str) -> str | None:
        msg = (user_message or "").strip()
        if not msg:
            return None
        self._reload_if_needed()
        teacher_map = self._teacher_map or {}
        if not teacher_map:
            return None

        hits: list[tuple[str, str]] = []
        for name, url in teacher_map.items():
            if len(name) < 2:
                continue
            if name in msg:
                hits.append((name, url))
                if len(hits) >= self.max_hits:
                    break

        if not hits:
            return None

        lines = ["【本地资料片段：teachers-ms-shu.json（教师名录命中）】"]
        for name, url in hits:
            lines.append(f"- 教师：{name}")
            if url:
                lines.append(f"  主页/介绍页：{url}")
        return "\n".join(lines).strip()


```

```python
__all__ = []


```

```python
__all__ = []


```

Nice：后端主链路已经落地了——现在 `/api/chat` 会先做 **guidance 三段命中**，再做 **老师名命中**，把这些本地片段拼进同一次模型调用里。接下来我补齐前端 ChatGPT 风格静态页（含 Markdown 渲染），并写 README 让你在 M4 上用 Ollama 一键跑通。

```html
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>上海大学 · 校园百事通</title>
  <meta name="description" content="上海大学校园百事通：本地RAG + ChatGPT风格交互"/>
  <link rel="stylesheet" href="/assets/style.css"/>
  <script src="https://cdn.jsdelivr.net/npm/marked@12.0.2/marked.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/dompurify@3.1.6/dist/purify.min.js"></script>
</head>
<body>
  <div class="app">
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-badge">SHU</div>
        <div class="brand-meta">
          <div class="brand-title">校园百事通</div>
          <div class="brand-sub">本地RAG · 办事指南 · 智能问答</div>
        </div>
      </div>

      <div class="side-actions">
        <a class="btn primary" href="/faq">FAQ（20条）</a>
        <button class="btn ghost" id="newChatBtn" type="button">新建对话</button>
      </div>

      <div class="tips">
        <div class="tips-title">使用提示</div>
        <div class="tips-body">
          - 回车发送，Shift+回车换行<br/>
          - 输入<strong>“人工”</strong>：弹出联系方式<br/>
          - 若命中 <code>docs/2025_student_guidance.md</code>，会自动附带相邻三段作为上下文
        </div>
      </div>
    </aside>

    <main class="main">
      <header class="topbar">
        <div>
          <div class="title">上海大学 · 校园百事通</div>
          <div class="meta">ChatGPT 风格交互（Markdown 渲染）</div>
        </div>
        <div class="meta">
          <span class="pill">API: POST /api/chat</span>
        </div>
      </header>

      <section class="chat" id="chat">
        <div class="chat-inner" id="chatInner"></div>
      </section>

      <section class="composer">
        <div class="composer-inner">
          <textarea id="prompt" placeholder="请输入问题，例如：VPN怎么用？研究生培养计划怎么查看？"></textarea>
          <button class="send" id="sendBtn" type="button">发送</button>
        </div>
        <div class="footnote">
          本系统默认调用本地 Ollama（可用环境变量切换 DeepSeek）。回答仅供参考，具体以学校官方通知/规章为准。
        </div>
      </section>
    </main>
  </div>

  <div class="modal" id="modal" aria-hidden="true">
    <div class="modal-card" role="dialog" aria-modal="true">
      <div class="modal-title" id="modalTitle">提示</div>
      <div class="modal-body" id="modalBody"></div>
      <div class="modal-actions">
        <button class="btn ghost" type="button" id="modalClose">关闭</button>
        <button class="btn primary" type="button" id="modalOk">知道了</button>
      </div>
    </div>
  </div>

  <script src="/assets/app.js"></script>
</body>
</html>


```

```html
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>校园百事通 · FAQ</title>
  <meta name="description" content="上海大学校园百事通 FAQ（20条）"/>
  <link rel="stylesheet" href="/assets/style.css"/>
</head>
<body>
  <div class="page">
    <div class="page-head">
      <div>
        <div class="page-title">FAQ（20条）</div>
        <div class="page-sub">通用解答模板；具体以学校官方通知/学生手册/学院要求为准。</div>
      </div>
      <div class="page-actions">
        <a class="btn primary" href="/">返回聊天</a>
      </div>
    </div>

    <div class="faq-grid">
      <div class="card toc">
        <div class="toc-title">目录</div>
        <a href="#q01">01 学籍注册/报到</a>
        <a href="#q02">02 休学/复学/退学</a>
        <a href="#q03">03 转导师/转专业</a>
        <a href="#q04">04 选课与学分</a>
        <a href="#q05">05 请假与考勤</a>
        <a href="#q06">06 开题/中期</a>
        <a href="#q07">07 论文评审/盲审</a>
        <a href="#q08">08 答辩与毕业流程</a>
        <a href="#q09">09 培养计划/学分要求</a>
        <a href="#q10">10 研究生系统/一网通办</a>
        <a href="#q11">11 校园卡丢失/补办</a>
        <a href="#q12">12 图书馆借阅/资源</a>
        <a href="#q13">13 VPN/校外访问</a>
        <a href="#q14">14 宿舍报修/后勤</a>
        <a href="#q15">15 医疗/医保/报销</a>
        <a href="#q16">16 出国(境)交流/访学</a>
        <a href="#q17">17 奖助学金</a>
        <a href="#q18">18 困难认定/助学贷款</a>
        <a href="#q19">19 违纪处分/申诉</a>
        <a href="#q20">20 防诈骗/资金安全</a>
      </div>

      <div class="card">
        <div class="qa" id="q01">
          <div class="q">01 学籍注册/报到怎么做？</div>
          <div class="a">按学校通知完成线上信息确认 → 到学院/研究生院办理报到材料 → 完成学籍注册/缴费/住宿等事项。错过时间请尽快联系学院教务或辅导员。</div>
        </div>
        <div class="qa" id="q02">
          <div class="q">02 休学/复学/退学一般怎么申请？</div>
          <div class="a">向导师/学院提出申请 → 填写表单并准备证明材料 → 学院审核 → 学校审批。复学需按规定时间申请并完成注册；退学涉及学籍处理与离校手续，建议先咨询学院教务。</div>
        </div>
        <div class="qa" id="q03">
          <div class="q">03 想转导师/转专业怎么办？</div>
          <div class="a">先确认政策窗口期与条件 → 与现导师和拟接收导师沟通 → 提交学院审批材料（个人陈述、学习/科研情况、匹配说明等）。</div>
        </div>
        <div class="qa" id="q04">
          <div class="q">04 选课与学分认定有哪些要点？</div>
          <div class="a">按培养方案优先完成必修与学分结构；跨院/线上课程是否计入以学院规定为准。做学分认定通常需课程大纲、成绩单/证明并经学院审核。</div>
        </div>
        <div class="qa" id="q05">
          <div class="q">05 请假与考勤怎么走流程？</div>
          <div class="a">以学院/课题组要求为准。一般短期请假走系统或审批；离校/出差/长期请假需导师同意并备案。建议提前申请，避免影响课程与考核。</div>
        </div>
        <div class="qa" id="q06">
          <div class="q">06 论文开题/中期检查怎么准备？</div>
          <div class="a">开题要点：研究背景、文献综述、研究方案、计划进度、可行性与创新点；中期要点：阶段成果、问题与风险、后续计划。提前对齐学院模板与要求。</div>
        </div>
        <div class="qa" id="q07">
          <div class="q">07 论文评审/盲审有什么注意？</div>
          <div class="a">按学校要求去除可识别信息、严格排版与引用规范；重点写清核心贡献与可复现性。先做自检（格式/图表/引用/重复率）。</div>
        </div>
        <div class="qa" id="q08">
          <div class="q">08 毕业与答辩大致流程？</div>
          <div class="a">资格审核（学分/培养环节）→ 论文定稿 → 评审 → 答辩申请 → 答辩 → 提交终稿归档 → 离校手续。节点以学院通知为准。</div>
        </div>
        <div class="qa" id="q09">
          <div class="q">09 培养计划/学分要求在哪里看？</div>
          <div class="a">一般在研究生系统或相关应用中查看（不同学院入口略有差异）。建议保存培养方案截图/导出PDF，按学期核对学分结构与培养环节。</div>
        </div>
        <div class="qa" id="q10">
          <div class="q">10 常见系统入口：一网通办/研究生系统怎么访问？</div>
          <div class="a">校内网络直接访问；校外通常需 VPN 或 WebVPN。遇到登录失败先检查账号状态、密码、验证码与网络，再联系信息办/网络中心。</div>
        </div>
        <div class="qa" id="q11">
          <div class="q">11 校园卡丢了怎么处理？</div>
          <div class="a">第一时间挂失 → 补办 → 同步处理门禁/图书馆/消费账户；若绑定第三方支付，及时检查资金安全。</div>
        </div>
        <div class="qa" id="q12">
          <div class="q">12 图书馆借阅/论文资源怎么用？</div>
          <div class="a">按图书馆规定借阅；数据库与资源按校内授权使用。论文查重与次数一般由学院/研究生院统一安排。</div>
        </div>
        <div class="qa" id="q13">
          <div class="q">13 VPN/校外访问怎么用？</div>
          <div class="a">安装学校指定 VPN 客户端 → 统一身份认证登录 → 连接校内网络 → 访问教务/图书馆/资产平台等。失败先检查账号、网络与客户端版本。</div>
        </div>
        <div class="qa" id="q14">
          <div class="q">14 宿舍报修/后勤故障怎么处理？</div>
          <div class="a">通过宿舍服务台/后勤报修平台提交：楼号房号、故障描述、联系方式、可上门时间。用电安全风险先断电并联系值班电话。</div>
        </div>
        <div class="qa" id="q15">
          <div class="q">15 医疗/医保/报销怎么走？</div>
          <div class="a">校医院或指定医院就诊 → 保存票据与病历 → 按学校/医保要求提交材料。政策更新较快，务必看学校最新说明。</div>
        </div>
        <div class="qa" id="q16">
          <div class="q">16 出国(境)交流/访学要做哪些手续？</div>
          <div class="a">项目申请/录取 → 学院/研究生院审批 → 出国(境)手续 → 培养计划衔接 → 风险告知与保险。提前评估是否影响毕业节点。</div>
        </div>
        <div class="qa" id="q17">
          <div class="q">17 奖助学金怎么评/怎么申？</div>
          <div class="a">一般按综合表现评审，按学院要求提交证明材料并关注公示与申诉时限。具体指标以学院/学校通知为准。</div>
        </div>
        <div class="qa" id="q18">
          <div class="q">18 困难认定/助学贷款怎么申请？</div>
          <div class="a">线上提交家庭经济情况与佐证 → 学院审核/公示 → 学校确认。警惕“代办/刷流水”等诈骗，注意信息安全。</div>
        </div>
        <div class="qa" id="q19">
          <div class="q">19 违纪处分或对结果有异议，能申诉吗？</div>
          <div class="a">一般有申诉渠道与时限：按规定提交书面材料并附证据。建议通过官方渠道办理并保留通知/公示证据。</div>
        </div>
        <div class="qa" id="q20">
          <div class="q">20 遇到诈骗/资金风险怎么办？</div>
          <div class="a">立即停止操作 → 保留证据 → 联系银行/支付平台止付冻结 → 报警并同步告知辅导员/保卫部门。任何“保证下款/低息秒批/刷流水”都高度可疑。</div>
        </div>
      </div>
    </div>
  </div>
</body>
</html>


```

```css
:root{
  --bg:#0b1020;
  --panel:#0f172a;
  --text:#e6eefc;
  --muted:#9db0d0;
  --border:rgba(255,255,255,.09);
  --accent:#4f8cff;
  --accent2:#22c55e;
  --shadow: 0 14px 44px rgba(0,0,0,.42);
  --radius:14px;
  --mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
  --sans: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial;
}
*{box-sizing:border-box}
html,body{height:100%}
body{
  margin:0;
  font-family:var(--sans);
  background:
    radial-gradient(1200px 800px at 18% 0%, rgba(79,140,255,.22), transparent 60%),
    radial-gradient(1000px 700px at 88% 18%, rgba(34,197,94,.16), transparent 55%),
    var(--bg);
  color:var(--text);
}
a{color:inherit}

.app{height:100%;display:flex}
.sidebar{
  width:310px;
  padding:18px 16px;
  border-right:1px solid var(--border);
  background: linear-gradient(180deg, rgba(255,255,255,.05), rgba(255,255,255,.02));
}
.brand{
  display:flex;gap:10px;align-items:center;
  padding:10px 10px;
  border:1px solid var(--border);
  border-radius:16px;
  background: rgba(255,255,255,.03);
}
.brand-badge{
  width:46px;height:46px;border-radius:16px;
  display:grid;place-items:center;
  font-weight:900;letter-spacing:.8px;
  background: rgba(79,140,255,.24);
  border:1px solid rgba(79,140,255,.36);
}
.brand-title{font-weight:900}
.brand-sub{margin-top:3px;color:var(--muted);font-size:12px;line-height:1.35}

.side-actions{margin-top:16px;display:flex;flex-direction:column;gap:10px}
.btn{
  display:flex;align-items:center;justify-content:center;
  padding:10px 12px;
  border-radius:12px;
  border:1px solid var(--border);
  background: rgba(255,255,255,.03);
  cursor:pointer;
  text-decoration:none;
  transition:.15s ease;
}
.btn:hover{transform: translateY(-1px); border-color: rgba(255,255,255,.16)}
.btn.primary{background: rgba(79,140,255,.22); border-color: rgba(79,140,255,.38)}
.btn.ghost{background: rgba(255,255,255,.02)}

.tips{
  margin-top:16px;
  padding:12px;
  border:1px solid var(--border);
  border-radius:12px;
  background: rgba(255,255,255,.02);
  color:var(--muted);
  line-height:1.6;
  font-size:13px;
}
.tips-title{font-weight:800;color:var(--text);margin-bottom:6px}
.tips code{font-family:var(--mono);font-size:12px}

.main{flex:1;min-width:0;display:flex;flex-direction:column}
.topbar{
  height:58px;
  padding:0 18px;
  display:flex;align-items:center;justify-content:space-between;
  border-bottom:1px solid var(--border);
  background: rgba(10,16,32,.66);
  backdrop-filter: blur(8px);
}
.title{font-weight:900}
.meta{color:var(--muted);font-size:13px}
.pill{
  display:inline-flex;align-items:center;
  padding:6px 10px;
  border-radius:999px;
  border:1px solid rgba(255,255,255,.12);
  background: rgba(255,255,255,.03);
  font-family:var(--mono);
  font-size:12px;
}

.chat{flex:1;overflow:auto;padding:18px 18px 10px}
.chat-inner{max-width:980px;margin:0 auto;display:flex;flex-direction:column;gap:14px}
.msg{display:flex;gap:10px;align-items:flex-end}
.msg.user{justify-content:flex-end}
.avatar{
  width:34px;height:34px;border-radius:12px;
  display:grid;place-items:center;
  border:1px solid var(--border);
  background: rgba(255,255,255,.03);
  font-weight:900;
  flex:0 0 auto;
}
.avatar.ai{background: rgba(34,197,94,.18); border-color: rgba(34,197,94,.28)}
.avatar.user{background: rgba(79,140,255,.18); border-color: rgba(79,140,255,.28)}

.bubble{
  max-width:min(760px, 92%);
  padding:12px 14px;
  border-radius:16px;
  border:1px solid var(--border);
  background: rgba(255,255,255,.03);
  box-shadow: 0 8px 18px rgba(0,0,0,.22);
  line-height:1.6;
  word-break:break-word;
}
.msg.user .bubble{background: rgba(79,140,255,.20); border-color: rgba(79,140,255,.32)}
.bubble .small{
  display:block;margin-top:8px;
  color:var(--muted);
  font-size:12px;
  font-family:var(--mono);
}

/* Markdown inside bubble */
.bubble > *:first-child{margin-top:0}
.bubble > *:last-child{margin-bottom:0}
.bubble p{margin:0 0 10px}
.bubble ul,.bubble ol{margin:0 0 10px; padding-left:18px}
.bubble li{margin:4px 0}
.bubble a{color:#b9d2ff}
.bubble a:hover{text-decoration:underline}
.bubble blockquote{
  margin:0 0 10px;
  padding:8px 12px;
  border-left:3px solid rgba(79,140,255,.55);
  background: rgba(79,140,255,.08);
  border-radius:10px;
}
.bubble code{
  font-family: var(--mono);
  font-size: 12.5px;
  padding: 1px 6px;
  border-radius: 8px;
  background: rgba(255,255,255,.06);
  border: 1px solid rgba(255,255,255,.08);
}
.bubble pre{
  margin:0 0 10px;
  padding:12px;
  border-radius:12px;
  overflow:auto;
  background: rgba(0,0,0,.35);
  border: 1px solid rgba(255,255,255,.10);
}
.bubble pre code{
  padding:0;border:none;background:transparent;
}
.bubble table{
  width:100%;
  border-collapse: collapse;
  margin:0 0 10px;
  overflow:hidden;
  border-radius:12px;
  border:1px solid rgba(255,255,255,.10);
}
.bubble th,.bubble td{
  padding:8px 10px;
  border-bottom:1px solid rgba(255,255,255,.08);
}
.bubble th{background: rgba(255,255,255,.04);text-align:left}
.bubble hr{
  border:none;height:1px;
  background: rgba(255,255,255,.10);
  margin:10px 0;
}

.composer{
  border-top:1px solid var(--border);
  background: rgba(10,16,32,.66);
  backdrop-filter: blur(8px);
  padding:14px 18px 18px;
}
.composer-inner{
  max-width:980px;
  margin:0 auto;
  display:flex;
  gap:10px;
  align-items:flex-end;
}
textarea{
  flex:1;
  min-height:52px;
  max-height:160px;
  resize:none;
  padding:12px 12px;
  border-radius:14px;
  border:1px solid var(--border);
  background: rgba(255,255,255,.03);
  color:var(--text);
  outline:none;
  line-height:1.45;
}
textarea::placeholder{color: rgba(157,176,208,.82)}
.send{
  padding:12px 14px;
  border-radius:14px;
  border:1px solid rgba(79,140,255,.38);
  background: rgba(79,140,255,.26);
  color:var(--text);
  cursor:pointer;
  transition:.15s ease;
  min-width:98px;
}
.send:hover{transform: translateY(-1px)}
.send:disabled{opacity:.55;cursor:not-allowed;transform:none}
.footnote{
  max-width:980px;
  margin:10px auto 0;
  color:var(--muted);
  font-size:12px;
  line-height:1.45;
}

.typing{display:inline-flex;align-items:center;gap:6px}
.dot{width:7px;height:7px;border-radius:50%;background: rgba(230,238,252,.7);animation: bounce 1.2s infinite ease-in-out}
.dot:nth-child(2){animation-delay:.15s}
.dot:nth-child(3){animation-delay:.3s}
@keyframes bounce{0%,80%,100%{transform: translateY(0);opacity:.55}40%{transform: translateY(-4px);opacity:1}}

.modal{
  position:fixed; inset:0;
  display:none;
  align-items:center;
  justify-content:center;
  background: rgba(0,0,0,.55);
  padding:20px;
  z-index:50;
}
.modal.show{display:flex}
.modal-card{
  width:min(520px, 96vw);
  background: rgba(15,23,42,.92);
  border:1px solid var(--border);
  border-radius:16px;
  padding:16px;
  box-shadow: var(--shadow);
}
.modal-title{font-weight:900;font-size:16px}
.modal-body{color:var(--muted); margin-top:10px; line-height:1.55; white-space:pre-wrap}
.modal-actions{margin-top:14px; display:flex; gap:10px; justify-content:flex-end}

/* FAQ */
.page{max-width:980px;margin:0 auto;padding:22px 18px 36px}
.page-head{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;margin-bottom:14px}
.page-title{font-weight:950;font-size:20px;letter-spacing:.3px}
.page-sub{margin-top:6px;color:var(--muted);line-height:1.5}
.page-actions{display:flex;gap:10px;align-items:center}
.card{
  border:1px solid var(--border);
  background: rgba(255,255,255,.03);
  border-radius:16px;
  padding:16px;
  box-shadow: 0 10px 30px rgba(0,0,0,.28);
}
.faq-grid{display:grid;grid-template-columns: 280px 1fr; gap:14px}
.toc-title{font-weight:900;margin-bottom:8px}
.toc a{
  display:block;
  padding:8px 10px;
  border-radius:10px;
  color:var(--muted);
  text-decoration:none;
  border:1px solid transparent;
}
.toc a:hover{
  color:var(--text);
  background: rgba(255,255,255,.03);
  border-color: var(--border);
}
.qa{
  padding:12px 12px;
  border-radius:14px;
  border:1px solid var(--border);
  background: rgba(255,255,255,.02);
  margin-bottom:10px;
}
.qa .q{font-weight:900}
.qa .a{color:var(--muted); margin-top:8px; line-height:1.65}

@media (max-width: 980px){
  .sidebar{display:none}
  .faq-grid{grid-template-columns:1fr}
}


```

```javascript
(function () {
  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function nowTime() {
    const d = new Date();
    const hh = String(d.getHours()).padStart(2, '0');
    const mm = String(d.getMinutes()).padStart(2, '0');
    return `${hh}:${mm}`;
  }

  function renderMarkdownToSafeHtml(md) {
    const text = String(md == null ? '' : md);
    if (!window.marked || !window.DOMPurify) {
      return escapeHtml(text).replace(/\n/g, '<br/>');
    }
    try {
      window.marked.setOptions({
        gfm: true,
        breaks: true,
        mangle: false,
        headerIds: false
      });
      const rawHtml = window.marked.parse(text);
      return window.DOMPurify.sanitize(rawHtml, { USE_PROFILES: { html: true } });
    } catch (e) {
      return escapeHtml(text).replace(/\n/g, '<br/>');
    }
  }

  function scrollToBottom() {
    const chat = document.getElementById('chat');
    if (!chat) return;
    chat.scrollTo({ top: chat.scrollHeight, behavior: 'smooth' });
  }

  function addMessage(role, text, meta) {
    const chatInner = document.getElementById('chatInner');
    const wrap = document.createElement('div');
    wrap.className = `msg ${role}`;

    const avatar = document.createElement('div');
    avatar.className = `avatar ${role === 'ai' ? 'ai' : 'user'}`;
    avatar.textContent = role === 'ai' ? 'AI' : '我';

    const bubble = document.createElement('div');
    bubble.className = 'bubble';

    if (role === 'ai') {
      bubble.innerHTML = renderMarkdownToSafeHtml(text);
    } else {
      bubble.innerHTML = escapeHtml(String(text == null ? '' : text)).replace(/\n/g, '<br/>');
    }

    if (meta) {
      const small = document.createElement('span');
      small.className = 'small';
      small.textContent = meta;
      bubble.appendChild(small);
    }

    if (role === 'user') {
      wrap.appendChild(bubble);
      wrap.appendChild(avatar);
    } else {
      wrap.appendChild(avatar);
      wrap.appendChild(bubble);
    }

    chatInner.appendChild(wrap);
    scrollToBottom();
  }

  function addTyping() {
    const chatInner = document.getElementById('chatInner');
    const wrap = document.createElement('div');
    wrap.className = 'msg ai';
    wrap.id = 'typingRow';

    const avatar = document.createElement('div');
    avatar.className = 'avatar ai';
    avatar.textContent = 'AI';

    const bubble = document.createElement('div');
    bubble.className = 'bubble';

    const typing = document.createElement('span');
    typing.className = 'typing';
    typing.innerHTML = '<span class="dot"></span><span class="dot"></span><span class="dot"></span>';

    bubble.appendChild(typing);
    wrap.appendChild(avatar);
    wrap.appendChild(bubble);
    chatInner.appendChild(wrap);
    scrollToBottom();
  }

  function removeTyping() {
    const row = document.getElementById('typingRow');
    if (row) row.remove();
  }

  function showModal(title, body) {
    document.getElementById('modalTitle').textContent = title;
    document.getElementById('modalBody').textContent = body;
    document.getElementById('modal').classList.add('show');
  }

  function hideModal() {
    document.getElementById('modal').classList.remove('show');
  }

  function setSending(sending) {
    document.getElementById('sendBtn').disabled = sending;
    document.getElementById('prompt').disabled = sending;
  }

  function normalizeMessage(msg) {
    return String(msg || '').replace(/\r\n/g, '\n').trim();
  }

  function autoGrowTextarea(el) {
    el.style.height = '0px';
    el.style.height = Math.min(el.scrollHeight, 160) + 'px';
  }

  async function send() {
    const textarea = document.getElementById('prompt');
    const msg = normalizeMessage(textarea.value);
    if (!msg) return;

    if (msg === '人工') {
      showModal('人工客服', '请联系学长：zhangdreamer@126.com');
      textarea.value = '';
      autoGrowTextarea(textarea);
      textarea.focus();
      return;
    }

    addMessage('user', msg, `发送于 ${nowTime()}`);
    textarea.value = '';
    autoGrowTextarea(textarea);
    setSending(true);
    addTyping();

    try {
      const resp = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: msg })
      });
      const data = await resp.json();
      removeTyping();

      if (data && data.type === 'human') {
        showModal('人工客服', data.answer || '请联系学长：zhangdreamer@126.com');
        return;
      }
      const answer = (data && data.answer) ? String(data.answer) : '（未获取到答案）';
      addMessage('ai', answer, `回答于 ${nowTime()}`);
    } catch (e) {
      removeTyping();
      addMessage('ai', `请求失败：${String(e)}`, `错误于 ${nowTime()}`);
    } finally {
      setSending(false);
      textarea.focus();
    }
  }

  document.addEventListener('DOMContentLoaded', function () {
    const textarea = document.getElementById('prompt');
    const sendBtn = document.getElementById('sendBtn');
    const newChatBtn = document.getElementById('newChatBtn');

    addMessage(
      'ai',
      '你好！我是**上海大学校园百事通**。\n\n' +
        '- 你可以问我：培养计划、选课学分、VPN、校园卡、图书馆、报修等\n' +
        '- 当问题与 `docs/2025_student_guidance.md` 有关时，我会自动附带相邻三段内容用于更准确回答\n\n' +
        '输入“人工”可获取人工联系方式。',
      '提示'
    );

    sendBtn.addEventListener('click', send);

    textarea.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        send();
      }
    });

    textarea.addEventListener('input', function () {
      autoGrowTextarea(textarea);
    });

    newChatBtn.addEventListener('click', function () {
      document.getElementById('chatInner').innerHTML = '';
      addMessage('ai', '新的对话已开始。你想咨询什么问题？', '提示');
      textarea.value = '';
      autoGrowTextarea(textarea);
      textarea.focus();
    });

    document.getElementById('modalClose').addEventListener('click', hideModal);
    document.getElementById('modalOk').addEventListener('click', hideModal);
    document.getElementById('modal').addEventListener('click', function (e) {
      if (e.target && e.target.id === 'modal') hideModal();
    });

    autoGrowTextarea(textarea);
    textarea.focus();
  });
})();


```

前端页面已经补齐并且“AI 回复 Markdown 正确渲染”这条链路也接通了：前端用 `marked + DOMPurify` 渲染，后端返回的 Markdown 会像 ChatGPT 一样显示列表、代码块、引用等。接下来我会补 README（含 M4 + Ollama 一键启动），然后实际跑一下服务，确认 `/`、`/faq`、`/api/chat` 都正常工作。

```markdown
## 上海大学「校园百事通」(Local RAG) - 本地运行版

### 你将得到什么
- **ChatGPT 风格聊天前端**：`/`（支持 Markdown 渲染）
- **FAQ 静态页**：`/faq`
- **本地知识增强**：
  - **命中 `docs/2025_student_guidance.md` 时**：自动把“上一段+命中段+下一段”三段内容附带进同一次模型调用
  - **问题提到老师姓名时**：命中 `docs/teachers-ms-shu.json` 里的教师名录，并附带对应主页/介绍页链接

### 目录结构
- `docs/`：本地知识文档（已存在）
- `backend/app.py`：FastAPI 后端（`/api/chat`）
- `frontend/`：静态前端（无需编译）

### 运行环境（推荐：MacBook Air M4 / 16GB）
建议使用 **Ollama 本地大模型**（默认配置，无需外网 API）。

### 1) 安装 Ollama（本地LLM）
安装后启动 Ollama，然后拉取一个模型，例如：
- `qwen2.5:7b`（默认）

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

```bash
export LLM_PROVIDER=deepseek
export DEEPSEEK_API_KEY="你的key"
export DEEPSEEK_BASE_URL="https://api.deepseek.com"
export LLM_MODEL="deepseek-chat"
```

### 4) 本地RAG（本次实现的匹配策略）
- **Guidance 三段匹配**：把 `docs/2025_student_guidance.md` 按空行切段，基于关键词重叠评分，命中后取相邻三段作为上下文。
- **教师名命中**：用户问题中包含某位老师姓名（`docs/teachers-ms-shu.json` 的 key）时，附带该老师的链接信息。


```

Good catch on the runtime details:我发现当前 `backend/app.py` 里对“仓库根目录”的计算有一层偏移，会导致找不到 `docs/` 和 `frontend/`；另外 `StaticFiles` 需要 `frontend/assets/` 目录存在。接下来我会小修这两处，然后本地启动一次确认页面与接口都能访问。

```python
from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

import httpx
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.rag.guidance_match import GuidanceMatchService
from backend.rag.teacher_match import TeacherMatchService


REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = REPO_ROOT / "docs"
FRONTEND_DIR = REPO_ROOT / "frontend"


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, description="User message")


class ChatResponse(BaseModel):
    type: Literal["answer", "human"]
    answer: str


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
    if not api_key:
        return "系统未配置 `DEEPSEEK_API_KEY`，无法调用 DeepSeek。请先配置环境变量后重试。"
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
    timeout = float(os.getenv("DEEPSEEK_TIMEOUT", "60"))
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": model, "messages": messages, "temperature": 0.3},
        )
        resp.raise_for_status()
        data = resp.json()
        return (((data.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()


def get_llm_provider() -> str:
    return os.getenv("LLM_PROVIDER", "ollama").strip().lower()


def get_llm_model() -> str:
    # Good defaults for Apple Silicon: qwen2.5:7b / llama3.1:8b
    return os.getenv("LLM_MODEL", "qwen2.5:7b").strip()


app = FastAPI(title="SHU Campus Assistant (Local RAG)")

# Static frontend
FRONTEND_DIR.mkdir(exist_ok=True)
 (FRONTEND_DIR / "assets").mkdir(parents=True, exist_ok=True)
app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIR / "assets")), name="assets")


@app.get("/")
def index():
    index_file = FRONTEND_DIR / "index.html"
    if not index_file.exists():
        return {"error": "frontend/index.html not found"}
    return FileResponse(str(index_file))


@app.get("/faq")
def faq():
    faq_file = FRONTEND_DIR / "faq.html"
    if not faq_file.exists():
        return {"error": "frontend/faq.html not found"}
    return FileResponse(str(faq_file))


guidance_service = GuidanceMatchService(guidance_path=DOCS_DIR / "2025_student_guidance.md")
teacher_service = TeacherMatchService(teachers_json_path=DOCS_DIR / "teachers-ms-shu.json")


@app.get("/api/health")
def health():
    return {"ok": True}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    msg = (req.message or "").strip()
    if msg == "人工":
        return ChatResponse(type="human", answer="请联系学长：zhangdreamer@126.com")

    context_blocks: list[str] = []

    # Feature: guidance match -> add neighbor 3 paragraphs
    g = guidance_service.match_with_neighbors(msg)
    if g:
        context_blocks.append(
            "【本地资料片段：2025_student_guidance.md（相邻三段）】\n" + g.strip()
        )

    # Feature: teacher mention -> add teacher info
    t = teacher_service.build_teacher_context_if_mentioned(msg)
    if t:
        context_blocks.append(t.strip())

    context = "\n\n".join(context_blocks).strip()
    user_content = msg if not context else f"{context}\n\n【用户问题】\n{msg}"

    messages = [
        {"role": "system", "content": build_system_prompt()},
        {"role": "user", "content": user_content},
    ]

    provider = get_llm_provider()
    model = get_llm_model()

    try:
        if provider == "deepseek":
            answer = await call_deepseek(messages, model=model)
        else:
            answer = await call_ollama(messages, model=model)
    except Exception as e:
        return ChatResponse(type="answer", answer=f"调用模型失败：{type(e).__name__}: {e}")

    if not answer:
        answer = "（模型返回为空）"
    return ChatResponse(type="answer", answer=answer)



```

```python
from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

import httpx
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.rag.guidance_match import GuidanceMatchService
from backend.rag.teacher_match import TeacherMatchService


REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = REPO_ROOT / "docs"
FRONTEND_DIR = REPO_ROOT / "frontend"


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, description="User message")


class ChatResponse(BaseModel):
    type: Literal["answer", "human"]
    answer: str


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
    if not api_key:
        return "系统未配置 `DEEPSEEK_API_KEY`，无法调用 DeepSeek。请先配置环境变量后重试。"
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
    timeout = float(os.getenv("DEEPSEEK_TIMEOUT", "60"))
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": model, "messages": messages, "temperature": 0.3},
        )
        resp.raise_for_status()
        data = resp.json()
        return (((data.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()


def get_llm_provider() -> str:
    return os.getenv("LLM_PROVIDER", "ollama").strip().lower()


def get_llm_model() -> str:
    # Good defaults for Apple Silicon: qwen2.5:7b / llama3.1:8b
    return os.getenv("LLM_MODEL", "qwen2.5:7b").strip()


app = FastAPI(title="SHU Campus Assistant (Local RAG)")

# Static frontend
FRONTEND_DIR.mkdir(exist_ok=True)
(FRONTEND_DIR / "assets").mkdir(parents=True, exist_ok=True)
app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIR / "assets")), name="assets")


@app.get("/")
def index():
    index_file = FRONTEND_DIR / "index.html"
    if not index_file.exists():
        return {"error": "frontend/index.html not found"}
    return FileResponse(str(index_file))


@app.get("/faq")
def faq():
    faq_file = FRONTEND_DIR / "faq.html"
    if not faq_file.exists():
        return {"error": "frontend/faq.html not found"}
    return FileResponse(str(faq_file))


guidance_service = GuidanceMatchService(guidance_path=DOCS_DIR / "2025_student_guidance.md")
teacher_service = TeacherMatchService(teachers_json_path=DOCS_DIR / "teachers-ms-shu.json")


@app.get("/api/health")
def health():
    return {"ok": True}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    msg = (req.message or "").strip()
    if msg == "人工":
        return ChatResponse(type="human", answer="请联系学长：zhangdreamer@126.com")

    context_blocks: list[str] = []

    # Feature: guidance match -> add neighbor 3 paragraphs
    g = guidance_service.match_with_neighbors(msg)
    if g:
        context_blocks.append(
            "【本地资料片段：2025_student_guidance.md（相邻三段）】\n" + g.strip()
        )

    # Feature: teacher mention -> add teacher info
    t = teacher_service.build_teacher_context_if_mentioned(msg)
    if t:
        context_blocks.append(t.strip())

    context = "\n\n".join(context_blocks).strip()
    user_content = msg if not context else f"{context}\n\n【用户问题】\n{msg}"

    messages = [
        {"role": "system", "content": build_system_prompt()},
        {"role": "user", "content": user_content},
    ]

    provider = get_llm_provider()
    model = get_llm_model()

    try:
        if provider == "deepseek":
            answer = await call_deepseek(messages, model=model)
        else:
            answer = await call_ollama(messages, model=model)
    except Exception as e:
        return ChatResponse(type="answer", answer=f"调用模型失败：{type(e).__name__}: {e}")

    if not answer:
        answer = "（模型返回为空）"
    return ChatResponse(type="answer", answer=answer)



```

我刚试着做一次 Python 编译自检，沙盒环境不允许 Python 往系统缓存目录写入 `pyc`，所以失败了；我改成把 pyc 缓存强制写到仓库目录后再跑一次，这样就能验证代码是否有语法/导入问题。

### 已实现：提问先匹配《`docs/2025_student_guidance.md`》，命中就附带相邻三段给模型
后端 `POST /api/chat` 在收到问题后会：
- **先做本地匹配**：把 `docs/2025_student_guidance.md` 按空行切段，做关键词重叠评分
- **命中则附带上下文**：把“上一段 + 命中段 + 下一段”三段内容拼进同一次模型调用（作为 `【本地资料片段】`）
- **老师名增强**（你之前的需求也一起落地了）：若问题包含 `docs/teachers-ms-shu.json` 里的老师姓名，会把命中的老师链接也附带进去

### 关键文件
- `backend/rag/guidance_match.py`：段落匹配 + 相邻三段拼接
- `backend/app.py`：把命中三段（以及老师名命中）拼到 user message 后再调用模型
- `frontend/index.html` + `frontend/assets/app.js`：ChatGPT 风格 UI，AI 回复 **Markdown 正确渲染**

### 本地启动（Mac M4）
按 `README.md`：
- 启动：`uvicorn backend.app:app --reload --port 8000`
- 打开：`http://localhost:8000/`（聊天）与 `http://localhost:8000/faq`（FAQ）

如果你希望“匹配策略”从关键词重叠升级为更像向量检索（真正的 embedding RAG），我可以下一步把 `docs/` 全量索引成向量库，再做 TopK 检索与引用来源输出。

---

**User**

使用 embedding RAG + mac m4芯片可流畅运行的llm来跑

---

**Cursor**

目标是把现在的“关键词段落匹配”升级为**真正的 embedding RAG**：启动时把 `docs/` 文档切块→用本地 Ollama 的 embedding 模型生成向量→本地持久化（SQLite）并加载到内存；提问时先做向量检索 TopK，再把命中文本片段（带来源）一起送给本地 LLM（同样走 Ollama，M4 流畅）。我接下来会新增索引模块、加一个 `/api/rag/reindex` 手动重建接口，并更新 README 推荐的 M4 模型组合。

```python
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import struct
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import httpx


def _default_embed_model() -> str:
    # Light + common on Apple Silicon
    return os.getenv("EMBED_MODEL", "nomic-embed-text").strip() or "nomic-embed-text"


def _ollama_base_url() -> str:
    return os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")


def _chunk_text_by_paragraphs(text: str) -> list[str]:
    # Split by blank lines, then compact
    parts = re.split(r"\n\s*\n+", text.replace("\r\n", "\n"))
    out: list[str] = []
    for p in parts:
        s = (p or "").strip()
        if not s:
            continue
        if re.fullmatch(r"[#\-=*_ \t]+", s):
            continue
        out.append(s)
    return out


def _merge_to_chunks(paragraphs: list[str], max_chars: int = 900, overlap: int = 120) -> list[str]:
    """
    Merge paragraphs into ~max_chars chunks with a simple char-overlap.
    """
    chunks: list[str] = []
    buf: list[str] = []
    cur_len = 0

    def flush():
        nonlocal buf, cur_len
        if not buf:
            return
        chunk = "\n\n".join(buf).strip()
        if chunk:
            chunks.append(chunk)
        # overlap by tail chars
        if overlap > 0 and chunk:
            tail = chunk[-overlap:]
            buf = [tail]
            cur_len = len(tail)
        else:
            buf = []
            cur_len = 0

    for p in paragraphs:
        if cur_len + len(p) + 2 > max_chars and buf:
            flush()
        buf.append(p)
        cur_len += len(p) + 2
    flush()
    return chunks


def _iter_docs_markdown(docs_dir: Path) -> Iterable[Path]:
    for p in sorted(docs_dir.glob("*.md")):
        if p.name.startswith("."):
            continue
        yield p


def _fingerprint_files(paths: Iterable[Path]) -> str:
    h = hashlib.sha256()
    for p in paths:
        try:
            st = p.stat()
        except FileNotFoundError:
            continue
        h.update(str(p.name).encode("utf-8"))
        h.update(str(int(st.st_mtime)).encode("utf-8"))
        h.update(str(st.st_size).encode("utf-8"))
    return h.hexdigest()


def _pack_floats(vec: list[float]) -> bytes:
    return struct.pack(f"<{len(vec)}f", *vec)


def _unpack_floats(blob: bytes) -> list[float]:
    n = len(blob) // 4
    return list(struct.unpack(f"<{n}f", blob))


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _norm(a: list[float]) -> float:
    return max(1e-12, sum(x * x for x in a) ** 0.5)


def _cosine(a: list[float], b: list[float]) -> float:
    return _dot(a, b) / (_norm(a) * _norm(b))


async def _ollama_embed(text: str, model: str) -> list[float]:
    """
    Ollama embeddings:
    - Newer: POST /api/embed {model, input:[...]} -> {embeddings:[[...]]}
    - Older: POST /api/embeddings {model, prompt} -> {embedding:[...]}
    """
    base = _ollama_base_url()
    timeout = float(os.getenv("OLLAMA_TIMEOUT", "120"))
    async with httpx.AsyncClient(timeout=timeout) as client:
        # Try /api/embed first
        try:
            r = await client.post(f"{base}/api/embed", json={"model": model, "input": [text]})
            if r.status_code == 200:
                data = r.json()
                embs = data.get("embeddings") or []
                if embs and isinstance(embs[0], list):
                    return [float(x) for x in embs[0]]
        except Exception:
            pass

        r = await client.post(f"{base}/api/embeddings", json={"model": model, "prompt": text})
        r.raise_for_status()
        data = r.json()
        emb = data.get("embedding") or []
        return [float(x) for x in emb]


@dataclass(frozen=True)
class RagChunk:
    source: str
    chunk_index: int
    text: str
    embedding: list[float]


class EmbeddingRagIndex:
    """
    Local embedding index for docs/*.md:
    - Cached in SQLite
    - Loaded in-memory for fast cosine search
    """

    def __init__(self, docs_dir: Path, db_path: Path):
        self.docs_dir = docs_dir
        self.db_path = db_path
        self.embed_model = _default_embed_model()
        self._chunks: list[RagChunk] = []
        self._fingerprint: str | None = None

        self._init_db()

    def _init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as con:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS meta (
                  key TEXT PRIMARY KEY,
                  value TEXT NOT NULL
                )
                """
            )
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS chunks (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  source TEXT NOT NULL,
                  chunk_index INTEGER NOT NULL,
                  text TEXT NOT NULL,
                  embedding BLOB NOT NULL
                )
                """
            )

    def _get_meta(self, key: str) -> str | None:
        with sqlite3.connect(self.db_path) as con:
            row = con.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
            return row[0] if row else None

    def _set_meta(self, key: str, value: str) -> None:
        with sqlite3.connect(self.db_path) as con:
            con.execute(
                "INSERT INTO meta(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, value),
            )
            con.commit()

    def _load_from_db(self) -> list[RagChunk]:
        chunks: list[RagChunk] = []
        with sqlite3.connect(self.db_path) as con:
            for source, chunk_index, text, emb_blob in con.execute(
                "SELECT source, chunk_index, text, embedding FROM chunks ORDER BY source, chunk_index"
            ):
                chunks.append(
                    RagChunk(
                        source=source,
                        chunk_index=int(chunk_index),
                        text=str(text),
                        embedding=_unpack_floats(emb_blob),
                    )
                )
        return chunks

    def ensure_loaded(self) -> None:
        """
        Load chunks from sqlite; rebuild if docs changed or embedding model changed.
        """
        doc_paths = list(_iter_docs_markdown(self.docs_dir))
        fp = _fingerprint_files(doc_paths)
        cached_fp = self._get_meta("docs_fingerprint")
        cached_embed_model = self._get_meta("embed_model")

        if cached_fp == fp and cached_embed_model == self.embed_model:
            self._chunks = self._load_from_db()
            self._fingerprint = fp
            return

        # Rebuild synchronously on demand
        # (Indexing can take a while for very large docs; you can also call /api/rag/reindex explicitly)
        self._chunks = []
        self._fingerprint = None

    async def reindex(self) -> dict:
        """
        Rebuild the sqlite cache + in-memory chunks using Ollama embeddings.
        """
        start_ts = time.time()
        doc_paths = list(_iter_docs_markdown(self.docs_dir))
        fp = _fingerprint_files(doc_paths)

        # Clear
        with sqlite3.connect(self.db_path) as con:
            con.execute("DELETE FROM chunks")
            con.commit()

        total_chunks = 0
        for p in doc_paths:
            text = p.read_text(encoding="utf-8", errors="ignore")
            paras = _chunk_text_by_paragraphs(text)
            merged = _merge_to_chunks(paras)
            for i, chunk in enumerate(merged):
                emb = await _ollama_embed(chunk, model=self.embed_model)
                with sqlite3.connect(self.db_path) as con:
                    con.execute(
                        "INSERT INTO chunks(source, chunk_index, text, embedding) VALUES(?,?,?,?)",
                        (p.name, i, chunk, _pack_floats(emb)),
                    )
                    con.commit()
                total_chunks += 1

        self._set_meta("docs_fingerprint", fp)
        self._set_meta("embed_model", self.embed_model)
        self._chunks = self._load_from_db()
        self._fingerprint = fp

        return {
            "ok": True,
            "embed_model": self.embed_model,
            "docs": [p.name for p in doc_paths],
            "chunks": total_chunks,
            "seconds": round(time.time() - start_ts, 2),
        }

    async def search(self, query: str, top_k: int = 5) -> list[dict]:
        self.ensure_loaded()
        if not self._chunks:
            return []
        q_emb = await _ollama_embed(query, model=self.embed_model)
        scored = []
        for c in self._chunks:
            scored.append((_cosine(q_emb, c.embedding), c))
        scored.sort(key=lambda x: x[0], reverse=True)
        out = []
        for score, c in scored[: max(1, top_k)]:
            out.append(
                {
                    "score": float(score),
                    "source": c.source,
                    "chunk_index": c.chunk_index,
                    "text": c.text,
                }
            )
        return out

    def status(self) -> dict:
        doc_paths = list(_iter_docs_markdown(self.docs_dir))
        fp = _fingerprint_files(doc_paths)
        cached_fp = self._get_meta("docs_fingerprint")
        cached_embed_model = self._get_meta("embed_model")
        return {
            "docs_dir": str(self.docs_dir),
            "db_path": str(self.db_path),
            "embed_model": self.embed_model,
            "docs_count": len(doc_paths),
            "cached_docs_fingerprint": cached_fp,
            "current_docs_fingerprint": fp,
            "cached_embed_model": cached_embed_model,
            "in_memory_chunks": len(self._chunks),
            "ready": bool(self._chunks) and cached_fp == fp and cached_embed_model == self.embed_model,
        }


```

```python
from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

import httpx
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.rag.embedding_index import EmbeddingRagIndex
from backend.rag.teacher_match import TeacherMatchService


REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = REPO_ROOT / "docs"
FRONTEND_DIR = REPO_ROOT / "frontend"


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, description="User message")


class ChatResponse(BaseModel):
    type: Literal["answer", "human"]
    answer: str


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
    if not api_key:
        return "系统未配置 `DEEPSEEK_API_KEY`，无法调用 DeepSeek。请先配置环境变量后重试。"
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
    timeout = float(os.getenv("DEEPSEEK_TIMEOUT", "60"))
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": model, "messages": messages, "temperature": 0.3},
        )
        resp.raise_for_status()
        data = resp.json()
        return (((data.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()


def get_llm_provider() -> str:
    return os.getenv("LLM_PROVIDER", "ollama").strip().lower()


def get_llm_model() -> str:
    # Good defaults for Apple Silicon: qwen2.5:7b / llama3.1:8b
    return os.getenv("LLM_MODEL", "qwen2.5:7b").strip()


app = FastAPI(title="SHU Campus Assistant (Local RAG)")

# Static frontend
FRONTEND_DIR.mkdir(exist_ok=True)
(FRONTEND_DIR / "assets").mkdir(parents=True, exist_ok=True)
app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIR / "assets")), name="assets")


@app.get("/")
def index():
    index_file = FRONTEND_DIR / "index.html"
    if not index_file.exists():
        return {"error": "frontend/index.html not found"}
    return FileResponse(str(index_file))


@app.get("/faq")
def faq():
    faq_file = FRONTEND_DIR / "faq.html"
    if not faq_file.exists():
        return {"error": "frontend/faq.html not found"}
    return FileResponse(str(faq_file))


guidance_service = GuidanceMatchService(guidance_path=DOCS_DIR / "2025_student_guidance.md")
teacher_service = TeacherMatchService(teachers_json_path=DOCS_DIR / "teachers-ms-shu.json")
rag_index = EmbeddingRagIndex(docs_dir=DOCS_DIR, db_path=REPO_ROOT / "data" / "rag.sqlite")


@app.get("/api/health")
def health():
    return {"ok": True}

@app.get("/api/rag/status")
def rag_status():
    return rag_index.status()


@app.post("/api/rag/reindex")
async def rag_reindex():
    return await rag_index.reindex()


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    msg = (req.message or "").strip()
    if msg == "人工":
        return ChatResponse(type="human", answer="请联系学长：zhangdreamer@126.com")

    context_blocks: list[str] = []

    # Embedding RAG (TopK chunks from docs/*.md)
    top_k = int(os.getenv("RAG_TOP_K", "5"))
    rag_hits = await rag_index.search(msg, top_k=top_k)
    if rag_hits:
        lines = ["【本地资料片段：Embedding RAG TopK】"]
        for h in rag_hits:
            lines.append(f"- 来源：{h['source']}#{h['chunk_index']}（score={h['score']:.3f}）")
            lines.append(h["text"])
            lines.append("")  # spacer
        context_blocks.append("\n".join(lines).strip())

    # Feature: teacher mention -> add teacher info
    t = teacher_service.build_teacher_context_if_mentioned(msg)
    if t:
        context_blocks.append(t.strip())

    context = "\n\n".join(context_blocks).strip()
    user_content = msg if not context else f"{context}\n\n【用户问题】\n{msg}"

    messages = [
        {"role": "system", "content": build_system_prompt()},
        {"role": "user", "content": user_content},
    ]

    provider = get_llm_provider()
    model = get_llm_model()

    try:
        if provider == "deepseek":
            answer = await call_deepseek(messages, model=model)
        else:
            answer = await call_ollama(messages, model=model)
    except Exception as e:
        return ChatResponse(type="answer", answer=f"调用模型失败：{type(e).__name__}: {e}")

    if not answer:
        answer = "（模型返回为空）"
    return ChatResponse(type="answer", answer=answer)



```

Aha：embedding RAG 已经接进 `/api/chat` 了，但我需要再补一刀把旧的 `guidance_service` 引用完全移除（否则会运行时报错），并把 README 更新成“推荐：qwen2.5:7b + nomic-embed-text”以及如何 `POST /api/rag/reindex` 建索引。

```python
from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

import httpx
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.rag.embedding_index import EmbeddingRagIndex
from backend.rag.teacher_match import TeacherMatchService


REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = REPO_ROOT / "docs"
FRONTEND_DIR = REPO_ROOT / "frontend"


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, description="User message")


class ChatResponse(BaseModel):
    type: Literal["answer", "human"]
    answer: str


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
    if not api_key:
        return "系统未配置 `DEEPSEEK_API_KEY`，无法调用 DeepSeek。请先配置环境变量后重试。"
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
    timeout = float(os.getenv("DEEPSEEK_TIMEOUT", "60"))
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": model, "messages": messages, "temperature": 0.3},
        )
        resp.raise_for_status()
        data = resp.json()
        return (((data.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()


def get_llm_provider() -> str:
    return os.getenv("LLM_PROVIDER", "ollama").strip().lower()


def get_llm_model() -> str:
    # Good defaults for Apple Silicon: qwen2.5:7b / llama3.1:8b
    return os.getenv("LLM_MODEL", "qwen2.5:7b").strip()


app = FastAPI(title="SHU Campus Assistant (Local RAG)")

# Static frontend
FRONTEND_DIR.mkdir(exist_ok=True)
(FRONTEND_DIR / "assets").mkdir(parents=True, exist_ok=True)
app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIR / "assets")), name="assets")


@app.get("/")
def index():
    index_file = FRONTEND_DIR / "index.html"
    if not index_file.exists():
        return {"error": "frontend/index.html not found"}
    return FileResponse(str(index_file))


@app.get("/faq")
def faq():
    faq_file = FRONTEND_DIR / "faq.html"
    if not faq_file.exists():
        return {"error": "frontend/faq.html not found"}
    return FileResponse(str(faq_file))


teacher_service = TeacherMatchService(teachers_json_path=DOCS_DIR / "teachers-ms-shu.json")
rag_index = EmbeddingRagIndex(docs_dir=DOCS_DIR, db_path=REPO_ROOT / "data" / "rag.sqlite")


@app.get("/api/health")
def health():
    return {"ok": True}

@app.get("/api/rag/status")
def rag_status():
    return rag_index.status()


@app.post("/api/rag/reindex")
async def rag_reindex():
    return await rag_index.reindex()


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    msg = (req.message or "").strip()
    if msg == "人工":
        return ChatResponse(type="human", answer="请联系学长：zhangdreamer@126.com")

    context_blocks: list[str] = []

    # Embedding RAG (TopK chunks from docs/*.md)
    top_k = int(os.getenv("RAG_TOP_K", "5"))
    rag_hits = await rag_index.search(msg, top_k=top_k)
    if rag_hits:
        lines = ["【本地资料片段：Embedding RAG TopK】"]
        for h in rag_hits:
            lines.append(f"- 来源：{h['source']}#{h['chunk_index']}（score={h['score']:.3f}）")
            lines.append(h["text"])
            lines.append("")  # spacer
        context_blocks.append("\n".join(lines).strip())

    # Feature: teacher mention -> add teacher info
    t = teacher_service.build_teacher_context_if_mentioned(msg)
    if t:
        context_blocks.append(t.strip())

    context = "\n\n".join(context_blocks).strip()
    user_content = msg if not context else f"{context}\n\n【用户问题】\n{msg}"

    messages = [
        {"role": "system", "content": build_system_prompt()},
        {"role": "user", "content": user_content},
    ]

    provider = get_llm_provider()
    model = get_llm_model()

    try:
        if provider == "deepseek":
            answer = await call_deepseek(messages, model=model)
        else:
            answer = await call_ollama(messages, model=model)
    except Exception as e:
        return ChatResponse(type="answer", answer=f"调用模型失败：{type(e).__name__}: {e}")

    if not answer:
        answer = "（模型返回为空）"
    return ChatResponse(type="answer", answer=answer)



```

```markdown
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
默认使用本地 Ollama：
- `LLM_PROVIDER=ollama`
- `LLM_MODEL=qwen2.5:7b`
- `EMBED_MODEL=nomic-embed-text`
- `RAG_TOP_K=5`

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



```

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

**User**

1，日志输出本地资料的匹配情况；
2，日志输出调用大模型的输入输出报文
3，增加使用配置文件的方式设置大模型的url、模型、api_key


---

**Cursor**

计划：先把后端的配置统一收敛到一个 `.env` 配置文件（URL/模型/API Key 都从这里读），并加入标准日志（命中哪些本地资料、TopK 分数、以及调用大模型的入参/出参）。然后我会跑一次编译自检，确保你一启动就能看到清晰的日志输出。

计划：我会先把 `.env` 配置文件接入（启动时自动读取，统一管理 LLM 的 URL/模型/API Key），然后把日志补齐：每次提问都打印 RAG TopK 命中情况、以及大模型调用的入参/出参（默认截断，避免日志爆炸，可通过开关输出全量）。

```python
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Literal

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.rag.embedding_index import EmbeddingRagIndex
from backend.rag.teacher_match import TeacherMatchService


REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = REPO_ROOT / "docs"
FRONTEND_DIR = REPO_ROOT / "frontend"

load_dotenv(REPO_ROOT / ".env", override=False)

logger = logging.getLogger("campus_assistant")


def _setup_logging() -> None:
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


def _bool_env(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in {"1", "true", "yes", "y", "on"}


def _truncate(s: str, limit: int) -> str:
    if limit <= 0:
        return s
    if len(s) <= limit:
        return s
    return s[:limit] + f"...(truncated,{len(s)} chars)"


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, description="User message")


class ChatResponse(BaseModel):
    type: Literal["answer", "human"]
    answer: str


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
    log_io = _bool_env("LOG_LLM_IO", default=True)
    max_chars = int(os.getenv("LOG_LLM_MAX_CHARS", "4000"))
    if log_io:
        payload = {"model": model, "messages": messages, "stream": False}
        logger.info("LLM request (ollama): %s", _truncate(json.dumps(payload, ensure_ascii=False), max_chars))
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            f"{base_url}/api/chat",
            json={"model": model, "messages": messages, "stream": False},
        )
        resp.raise_for_status()
        data = resp.json()
        out = (data.get("message") or {}).get("content", "").strip()
        if log_io:
            logger.info("LLM response (ollama): %s", _truncate(out, max_chars))
        return out


async def call_deepseek(messages: list[dict], model: str) -> str:
    """
    Call DeepSeek (OpenAI-compatible chat/completions).
    """
    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        return "系统未配置 `DEEPSEEK_API_KEY`，无法调用 DeepSeek。请先配置环境变量后重试。"
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
    timeout = float(os.getenv("DEEPSEEK_TIMEOUT", "60"))
    log_io = _bool_env("LOG_LLM_IO", default=True)
    max_chars = int(os.getenv("LOG_LLM_MAX_CHARS", "4000"))
    if log_io:
        payload = {"model": model, "messages": messages, "temperature": 0.3}
        logger.info("LLM request (deepseek): %s", _truncate(json.dumps(payload, ensure_ascii=False), max_chars))
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": model, "messages": messages, "temperature": 0.3},
        )
        resp.raise_for_status()
        data = resp.json()
        out = (((data.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()
        if log_io:
            logger.info("LLM response (deepseek): %s", _truncate(out, max_chars))
        return out


def get_llm_provider() -> str:
    return os.getenv("LLM_PROVIDER", "ollama").strip().lower()


def get_llm_model() -> str:
    # Good defaults for Apple Silicon: qwen2.5:7b / llama3.1:8b
    return os.getenv("LLM_MODEL", "qwen2.5:7b").strip()


app = FastAPI(title="SHU Campus Assistant (Local RAG)")
_setup_logging()

# Static frontend
FRONTEND_DIR.mkdir(exist_ok=True)
(FRONTEND_DIR / "assets").mkdir(parents=True, exist_ok=True)
app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIR / "assets")), name="assets")


@app.get("/")
def index():
    index_file = FRONTEND_DIR / "index.html"
    if not index_file.exists():
        return {"error": "frontend/index.html not found"}
    return FileResponse(str(index_file))


@app.get("/faq")
def faq():
    faq_file = FRONTEND_DIR / "faq.html"
    if not faq_file.exists():
        return {"error": "frontend/faq.html not found"}
    return FileResponse(str(faq_file))


teacher_service = TeacherMatchService(teachers_json_path=DOCS_DIR / "teachers-ms-shu.json")
rag_index = EmbeddingRagIndex(docs_dir=DOCS_DIR, db_path=REPO_ROOT / "data" / "rag.sqlite")


@app.get("/api/health")
def health():
    return {"ok": True}

@app.get("/api/rag/status")
def rag_status():
    return rag_index.status()


@app.post("/api/rag/reindex")
async def rag_reindex():
    return await rag_index.reindex()


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    msg = (req.message or "").strip()
    logger.info("chat request: %s", _truncate(msg, int(os.getenv("LOG_MSG_MAX_CHARS", "500"))))
    if msg == "人工":
        return ChatResponse(type="human", answer="请联系学长：zhangdreamer@126.com")

    context_blocks: list[str] = []

    # Embedding RAG (TopK chunks from docs/*.md)
    top_k = int(os.getenv("RAG_TOP_K", "5"))
    rag_hits = await rag_index.search(msg, top_k=top_k)
    if rag_hits:
        logger.info(
            "RAG hits: %s",
            json.dumps(
                [
                    {
                        "source": h["source"],
                        "chunk_index": h["chunk_index"],
                        "score": round(float(h["score"]), 4),
                    }
                    for h in rag_hits
                ],
                ensure_ascii=False,
            ),
        )
        lines = ["【本地资料片段：Embedding RAG TopK】"]
        for h in rag_hits:
            lines.append(f"- 来源：{h['source']}#{h['chunk_index']}（score={h['score']:.3f}）")
            lines.append(h["text"])
            lines.append("")  # spacer
        context_blocks.append("\n".join(lines).strip())
    else:
        logger.info("RAG hits: none")

    # Feature: teacher mention -> add teacher info
    teacher_hits = teacher_service.find_mentions(msg)
    if teacher_hits:
        logger.info("Teacher hits: %s", json.dumps(teacher_hits, ensure_ascii=False))
        t = teacher_service.build_teacher_context(teacher_hits)
        if t:
            context_blocks.append(t.strip())
    else:
        logger.info("Teacher hits: none")

    context = "\n\n".join(context_blocks).strip()
    user_content = msg if not context else f"{context}\n\n【用户问题】\n{msg}"

    messages = [
        {"role": "system", "content": build_system_prompt()},
        {"role": "user", "content": user_content},
    ]

    provider = get_llm_provider()
    model = get_llm_model()

    try:
        if provider == "deepseek":
            answer = await call_deepseek(messages, model=model)
        else:
            answer = await call_ollama(messages, model=model)
    except Exception as e:
        logger.exception("LLM call failed")
        return ChatResponse(type="answer", answer=f"调用模型失败：{type(e).__name__}: {e}")

    if not answer:
        answer = "（模型返回为空）"
    return ChatResponse(type="answer", answer=answer)



```

```python
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TeacherMatchService:
    teachers_json_path: Path
    max_hits: int = 3

    _teacher_map: dict[str, str] | None = None
    _mtime: float | None = None

    def _reload_if_needed(self) -> None:
        if not self.teachers_json_path.exists():
            self._teacher_map = {}
            self._mtime = None
            return
        mtime = self.teachers_json_path.stat().st_mtime
        if self._teacher_map is not None and self._mtime == mtime:
            return
        try:
            raw = self.teachers_json_path.read_text(encoding="utf-8", errors="ignore")
            data = json.loads(raw) if raw.strip() else {}
            if isinstance(data, dict):
                self._teacher_map = {str(k).strip(): str(v).strip() for k, v in data.items() if str(k).strip()}
            else:
                self._teacher_map = {}
            self._mtime = mtime
        except Exception:
            self._teacher_map = {}
            self._mtime = mtime

    def find_mentions(self, user_message: str) -> list[dict]:
        msg = (user_message or "").strip()
        if not msg:
            return []
        self._reload_if_needed()
        teacher_map = self._teacher_map or {}
        if not teacher_map:
            return []

        hits: list[tuple[str, str]] = []
        for name, url in teacher_map.items():
            if len(name) < 2:
                continue
            if name in msg:
                hits.append((name, url))
                if len(hits) >= self.max_hits:
                    break

        return [{"name": n, "url": u} for n, u in hits]

    def build_teacher_context(self, hits: list[dict]) -> str | None:
        if not hits:
            return None
        lines = ["【本地资料片段：teachers-ms-shu.json（教师名录命中）】"]
        for h in hits:
            name = str(h.get("name") or "").strip()
            url = str(h.get("url") or "").strip()
            if not name:
                continue
            lines.append(f"- 教师：{name}")
            if url:
                lines.append(f"  主页/介绍页：{url}")
        return "\n".join(lines).strip()

    def build_teacher_context_if_mentioned(self, user_message: str) -> str | None:
        # Backward-compatible helper (if you call it elsewhere)
        return self.build_teacher_context(self.find_mentions(user_message))



```

Nice：日志链路已经补齐了——现在每次提问都会打印 **RAG TopK 命中/分数**、**教师名命中**、以及 **大模型请求/响应报文**（默认截断，避免过大）。接下来我补一个可复制的配置文件模板（用 `config.example.env`，不受忽略规则影响），你复制成 `.env` 就能生效。

```plaintext
# 复制本文件为 .env（与 README 一样放在仓库根目录），启动时会自动读取

# ======= LLM Provider =======
# ollama (local) | deepseek (remote)
LLM_PROVIDER=ollama

# ======= Ollama (Local) =======
OLLAMA_BASE_URL=http://localhost:11434
LLM_MODEL=qwen2.5:7b
EMBED_MODEL=nomic-embed-text

# ======= DeepSeek (Optional) =======
# DEEPSEEK_BASE_URL=https://api.deepseek.com
# DEEPSEEK_API_KEY=your_api_key_here
# LLM_MODEL=deepseek-chat

# ======= RAG =======
RAG_TOP_K=5

# ======= Logging =======
LOG_LEVEL=INFO
LOG_LLM_IO=true
LOG_LLM_MAX_CHARS=4000
LOG_MSG_MAX_CHARS=500


```

```markdown
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



```

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

**User**

RAG hits没有精确命中，不要匹配不相关的内容

---

**Cursor**

计划：我会把 RAG 检索改成“**先召回再过滤**”：先取一批候选（TopN），再按 **相似度阈值** + **关键词重叠** 过滤；如果过滤后为空，就直接认为“未命中”，不再把不相关片段塞给大模型。同时把过滤原因打到日志里，方便你调参。

```python
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import struct
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import httpx


def _default_embed_model() -> str:
    # Light + common on Apple Silicon
    return os.getenv("EMBED_MODEL", "nomic-embed-text").strip() or "nomic-embed-text"


def _ollama_base_url() -> str:
    return os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")


def _chunk_text_by_paragraphs(text: str) -> list[str]:
    # Split by blank lines, then compact
    parts = re.split(r"\n\s*\n+", text.replace("\r\n", "\n"))
    out: list[str] = []
    for p in parts:
        s = (p or "").strip()
        if not s:
            continue
        if re.fullmatch(r"[#\-=*_ \t]+", s):
            continue
        out.append(s)
    return out


def _merge_to_chunks(paragraphs: list[str], max_chars: int = 900, overlap: int = 120) -> list[str]:
    """
    Merge paragraphs into ~max_chars chunks with a simple char-overlap.
    """
    chunks: list[str] = []
    buf: list[str] = []
    cur_len = 0

    def flush():
        nonlocal buf, cur_len
        if not buf:
            return
        chunk = "\n\n".join(buf).strip()
        if chunk:
            chunks.append(chunk)
        # overlap by tail chars
        if overlap > 0 and chunk:
            tail = chunk[-overlap:]
            buf = [tail]
            cur_len = len(tail)
        else:
            buf = []
            cur_len = 0

    for p in paragraphs:
        if cur_len + len(p) + 2 > max_chars and buf:
            flush()
        buf.append(p)
        cur_len += len(p) + 2
    flush()
    return chunks


def _extract_keywords_for_filter(msg: str) -> list[str]:
    """
    A lightweight keyword extractor used only for filtering obvious false positives.
    """
    msg = (msg or "").strip()
    if not msg:
        return []
    zh = re.findall(r"[\u4e00-\u9fff]{2,4}", msg)
    en = re.findall(r"[A-Za-z0-9]{2,}", msg.lower())
    kws: list[str] = []
    seen = set()
    for k in zh + en:
        if k in seen:
            continue
        seen.add(k)
        kws.append(k)
    stop = {"什么", "怎么", "如何", "可以", "是否", "老师", "同学", "上海", "大学", "校园"}
    kws = [k for k in kws if k not in stop]
    kws.sort(key=len, reverse=True)
    return kws[:12]


def _keyword_overlap_count(text: str, keywords: list[str]) -> int:
    if not text or not keywords:
        return 0
    return sum(1 for k in keywords if k and (k in text))


def _iter_docs_markdown(docs_dir: Path) -> Iterable[Path]:
    for p in sorted(docs_dir.glob("*.md")):
        if p.name.startswith("."):
            continue
        yield p


def _fingerprint_files(paths: Iterable[Path]) -> str:
    h = hashlib.sha256()
    for p in paths:
        try:
            st = p.stat()
        except FileNotFoundError:
            continue
        h.update(str(p.name).encode("utf-8"))
        h.update(str(int(st.st_mtime)).encode("utf-8"))
        h.update(str(st.st_size).encode("utf-8"))
    return h.hexdigest()


def _pack_floats(vec: list[float]) -> bytes:
    return struct.pack(f"<{len(vec)}f", *vec)


def _unpack_floats(blob: bytes) -> list[float]:
    n = len(blob) // 4
    return list(struct.unpack(f"<{n}f", blob))


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _norm(a: list[float]) -> float:
    return max(1e-12, sum(x * x for x in a) ** 0.5)


def _cosine(a: list[float], b: list[float]) -> float:
    return _dot(a, b) / (_norm(a) * _norm(b))


async def _ollama_embed(text: str, model: str) -> list[float]:
    """
    Ollama embeddings:
    - Newer: POST /api/embed {model, input:[...]} -> {embeddings:[[...]]}
    - Older: POST /api/embeddings {model, prompt} -> {embedding:[...]}
    """
    base = _ollama_base_url()
    timeout = float(os.getenv("OLLAMA_TIMEOUT", "120"))
    async with httpx.AsyncClient(timeout=timeout) as client:
        # Try /api/embed first
        try:
            r = await client.post(f"{base}/api/embed", json={"model": model, "input": [text]})
            if r.status_code == 200:
                data = r.json()
                embs = data.get("embeddings") or []
                if embs and isinstance(embs[0], list):
                    return [float(x) for x in embs[0]]
        except Exception:
            pass

        r = await client.post(f"{base}/api/embeddings", json={"model": model, "prompt": text})
        r.raise_for_status()
        data = r.json()
        emb = data.get("embedding") or []
        return [float(x) for x in emb]


@dataclass(frozen=True)
class RagChunk:
    source: str
    chunk_index: int
    text: str
    embedding: list[float]


class EmbeddingRagIndex:
    """
    Local embedding index for docs/*.md:
    - Cached in SQLite
    - Loaded in-memory for fast cosine search
    """

    def __init__(self, docs_dir: Path, db_path: Path):
        self.docs_dir = docs_dir
        self.db_path = db_path
        self.embed_model = _default_embed_model()
        self._chunks: list[RagChunk] = []
        self._fingerprint: str | None = None

        self._init_db()

    def _init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as con:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS meta (
                  key TEXT PRIMARY KEY,
                  value TEXT NOT NULL
                )
                """
            )
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS chunks (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  source TEXT NOT NULL,
                  chunk_index INTEGER NOT NULL,
                  text TEXT NOT NULL,
                  embedding BLOB NOT NULL
                )
                """
            )

    def _get_meta(self, key: str) -> str | None:
        with sqlite3.connect(self.db_path) as con:
            row = con.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
            return row[0] if row else None

    def _set_meta(self, key: str, value: str) -> None:
        with sqlite3.connect(self.db_path) as con:
            con.execute(
                "INSERT INTO meta(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, value),
            )
            con.commit()

    def _load_from_db(self) -> list[RagChunk]:
        chunks: list[RagChunk] = []
        with sqlite3.connect(self.db_path) as con:
            for source, chunk_index, text, emb_blob in con.execute(
                "SELECT source, chunk_index, text, embedding FROM chunks ORDER BY source, chunk_index"
            ):
                chunks.append(
                    RagChunk(
                        source=source,
                        chunk_index=int(chunk_index),
                        text=str(text),
                        embedding=_unpack_floats(emb_blob),
                    )
                )
        return chunks

    def ensure_loaded(self) -> None:
        """
        Load chunks from sqlite; rebuild if docs changed or embedding model changed.
        """
        doc_paths = list(_iter_docs_markdown(self.docs_dir))
        fp = _fingerprint_files(doc_paths)
        cached_fp = self._get_meta("docs_fingerprint")
        cached_embed_model = self._get_meta("embed_model")

        if cached_fp == fp and cached_embed_model == self.embed_model:
            self._chunks = self._load_from_db()
            self._fingerprint = fp
            return

        # Rebuild synchronously on demand
        # (Indexing can take a while for very large docs; you can also call /api/rag/reindex explicitly)
        self._chunks = []
        self._fingerprint = None

    async def reindex(self) -> dict:
        """
        Rebuild the sqlite cache + in-memory chunks using Ollama embeddings.
        """
        start_ts = time.time()
        doc_paths = list(_iter_docs_markdown(self.docs_dir))
        fp = _fingerprint_files(doc_paths)

        # Clear
        with sqlite3.connect(self.db_path) as con:
            con.execute("DELETE FROM chunks")
            con.commit()

        total_chunks = 0
        for p in doc_paths:
            text = p.read_text(encoding="utf-8", errors="ignore")
            paras = _chunk_text_by_paragraphs(text)
            merged = _merge_to_chunks(paras)
            for i, chunk in enumerate(merged):
                emb = await _ollama_embed(chunk, model=self.embed_model)
                with sqlite3.connect(self.db_path) as con:
                    con.execute(
                        "INSERT INTO chunks(source, chunk_index, text, embedding) VALUES(?,?,?,?)",
                        (p.name, i, chunk, _pack_floats(emb)),
                    )
                    con.commit()
                total_chunks += 1

        self._set_meta("docs_fingerprint", fp)
        self._set_meta("embed_model", self.embed_model)
        self._chunks = self._load_from_db()
        self._fingerprint = fp

        return {
            "ok": True,
            "embed_model": self.embed_model,
            "docs": [p.name for p in doc_paths],
            "chunks": total_chunks,
            "seconds": round(time.time() - start_ts, 2),
        }

    async def search(
        self,
        query: str,
        top_k: int = 5,
        *,
        min_score: float = 0.38,
        min_keyword_hits: int = 1,
        preselect_k: int | None = None,
    ) -> list[dict]:
        self.ensure_loaded()
        if not self._chunks:
            return []
        q_emb = await _ollama_embed(query, model=self.embed_model)
        scored: list[tuple[float, RagChunk]] = []
        for c in self._chunks:
            scored.append((_cosine(q_emb, c.embedding), c))
        scored.sort(key=lambda x: x[0], reverse=True)

        # 1) Preselect a small top-N pool for filtering
        if preselect_k is None:
            preselect_k = max(20, int(top_k) * 6)
        pool = scored[: min(len(scored), max(1, int(preselect_k)))]

        # 2) Filter with score threshold + keyword overlap (to avoid irrelevant matches)
        keywords = _extract_keywords_for_filter(query)
        filtered: list[tuple[float, RagChunk, int]] = []
        for score, c in pool:
            if float(score) < float(min_score):
                continue
            kh = _keyword_overlap_count(c.text, keywords)
            if min_keyword_hits > 0 and kh < int(min_keyword_hits):
                continue
            filtered.append((float(score), c, int(kh)))

        filtered.sort(key=lambda x: x[0], reverse=True)
        out: list[dict] = []
        for score, c, kh in filtered[: max(1, int(top_k))]:
            out.append(
                {
                    "score": float(score),
                    "keyword_hits": int(kh),
                    "source": c.source,
                    "chunk_index": c.chunk_index,
                    "text": c.text,
                }
            )
        return out

    def status(self) -> dict:
        doc_paths = list(_iter_docs_markdown(self.docs_dir))
        fp = _fingerprint_files(doc_paths)
        cached_fp = self._get_meta("docs_fingerprint")
        cached_embed_model = self._get_meta("embed_model")
        return {
            "docs_dir": str(self.docs_dir),
            "db_path": str(self.db_path),
            "embed_model": self.embed_model,
            "docs_count": len(doc_paths),
            "cached_docs_fingerprint": cached_fp,
            "current_docs_fingerprint": fp,
            "cached_embed_model": cached_embed_model,
            "in_memory_chunks": len(self._chunks),
            "ready": bool(self._chunks) and cached_fp == fp and cached_embed_model == self.embed_model,
        }



```

```python
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Literal

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.rag.embedding_index import EmbeddingRagIndex
from backend.rag.teacher_match import TeacherMatchService


REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = REPO_ROOT / "docs"
FRONTEND_DIR = REPO_ROOT / "frontend"

load_dotenv(REPO_ROOT / ".env", override=False)

logger = logging.getLogger("campus_assistant")


def _setup_logging() -> None:
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


def _bool_env(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in {"1", "true", "yes", "y", "on"}


def _truncate(s: str, limit: int) -> str:
    if limit <= 0:
        return s
    if len(s) <= limit:
        return s
    return s[:limit] + f"...(truncated,{len(s)} chars)"


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, description="User message")


class ChatResponse(BaseModel):
    type: Literal["answer", "human"]
    answer: str


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
    log_io = _bool_env("LOG_LLM_IO", default=True)
    max_chars = int(os.getenv("LOG_LLM_MAX_CHARS", "4000"))
    if log_io:
        payload = {"model": model, "messages": messages, "stream": False}
        logger.info("LLM request (ollama): %s", _truncate(json.dumps(payload, ensure_ascii=False), max_chars))
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            f"{base_url}/api/chat",
            json={"model": model, "messages": messages, "stream": False},
        )
        resp.raise_for_status()
        data = resp.json()
        out = (data.get("message") or {}).get("content", "").strip()
        if log_io:
            logger.info("LLM response (ollama): %s", _truncate(out, max_chars))
        return out


async def call_deepseek(messages: list[dict], model: str) -> str:
    """
    Call DeepSeek (OpenAI-compatible chat/completions).
    """
    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        return "系统未配置 `DEEPSEEK_API_KEY`，无法调用 DeepSeek。请先配置环境变量后重试。"
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
    timeout = float(os.getenv("DEEPSEEK_TIMEOUT", "60"))
    log_io = _bool_env("LOG_LLM_IO", default=True)
    max_chars = int(os.getenv("LOG_LLM_MAX_CHARS", "4000"))
    if log_io:
        payload = {"model": model, "messages": messages, "temperature": 0.3}
        logger.info("LLM request (deepseek): %s", _truncate(json.dumps(payload, ensure_ascii=False), max_chars))
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": model, "messages": messages, "temperature": 0.3},
        )
        resp.raise_for_status()
        data = resp.json()
        out = (((data.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()
        if log_io:
            logger.info("LLM response (deepseek): %s", _truncate(out, max_chars))
        return out


def get_llm_provider() -> str:
    return os.getenv("LLM_PROVIDER", "ollama").strip().lower()


def get_llm_model() -> str:
    # Good defaults for Apple Silicon: qwen2.5:7b / llama3.1:8b
    return os.getenv("LLM_MODEL", "qwen2.5:7b").strip()


app = FastAPI(title="SHU Campus Assistant (Local RAG)")
_setup_logging()

# Static frontend
FRONTEND_DIR.mkdir(exist_ok=True)
(FRONTEND_DIR / "assets").mkdir(parents=True, exist_ok=True)
app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIR / "assets")), name="assets")


@app.get("/")
def index():
    index_file = FRONTEND_DIR / "index.html"
    if not index_file.exists():
        return {"error": "frontend/index.html not found"}
    return FileResponse(str(index_file))


@app.get("/faq")
def faq():
    faq_file = FRONTEND_DIR / "faq.html"
    if not faq_file.exists():
        return {"error": "frontend/faq.html not found"}
    return FileResponse(str(faq_file))


teacher_service = TeacherMatchService(teachers_json_path=DOCS_DIR / "teachers-ms-shu.json")
rag_index = EmbeddingRagIndex(docs_dir=DOCS_DIR, db_path=REPO_ROOT / "data" / "rag.sqlite")


@app.get("/api/health")
def health():
    return {"ok": True}

@app.get("/api/rag/status")
def rag_status():
    return rag_index.status()


@app.post("/api/rag/reindex")
async def rag_reindex():
    return await rag_index.reindex()


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    msg = (req.message or "").strip()
    logger.info("chat request: %s", _truncate(msg, int(os.getenv("LOG_MSG_MAX_CHARS", "500"))))
    if msg == "人工":
        return ChatResponse(type="human", answer="请联系学长：zhangdreamer@126.com")

    context_blocks: list[str] = []

    # Embedding RAG (TopK chunks from docs/*.md)
    top_k = int(os.getenv("RAG_TOP_K", "5"))
    rag_min_score = float(os.getenv("RAG_MIN_SCORE", "0.38"))
    rag_min_keyword_hits = int(os.getenv("RAG_MIN_KEYWORD_HITS", "1"))
    rag_hits = await rag_index.search(
        msg,
        top_k=top_k,
        min_score=rag_min_score,
        min_keyword_hits=rag_min_keyword_hits,
    )
    if rag_hits:
        logger.info(
            "RAG hits: %s",
            json.dumps(
                [
                    {
                        "source": h["source"],
                        "chunk_index": h["chunk_index"],
                        "score": round(float(h["score"]), 4),
                        "keyword_hits": int(h.get("keyword_hits", 0)),
                    }
                    for h in rag_hits
                ],
                ensure_ascii=False,
            ),
        )
        lines = ["【本地资料片段：Embedding RAG TopK】"]
        for h in rag_hits:
            lines.append(f"- 来源：{h['source']}#{h['chunk_index']}（score={h['score']:.3f}）")
            lines.append(h["text"])
            lines.append("")  # spacer
        context_blocks.append("\n".join(lines).strip())
    else:
        logger.info(
            "RAG hits: none (filtered). min_score=%s min_keyword_hits=%s top_k=%s",
            rag_min_score,
            rag_min_keyword_hits,
            top_k,
        )

    # Feature: teacher mention -> add teacher info
    teacher_hits = teacher_service.find_mentions(msg)
    if teacher_hits:
        logger.info("Teacher hits: %s", json.dumps(teacher_hits, ensure_ascii=False))
        t = teacher_service.build_teacher_context(teacher_hits)
        if t:
            context_blocks.append(t.strip())
    else:
        logger.info("Teacher hits: none")

    context = "\n\n".join(context_blocks).strip()
    user_content = msg if not context else f"{context}\n\n【用户问题】\n{msg}"

    messages = [
        {"role": "system", "content": build_system_prompt()},
        {"role": "user", "content": user_content},
    ]

    provider = get_llm_provider()
    model = get_llm_model()

    try:
        if provider == "deepseek":
            answer = await call_deepseek(messages, model=model)
        else:
            answer = await call_ollama(messages, model=model)
    except Exception as e:
        logger.exception("LLM call failed")
        return ChatResponse(type="answer", answer=f"调用模型失败：{type(e).__name__}: {e}")

    if not answer:
        answer = "（模型返回为空）"
    return ChatResponse(type="answer", answer=answer)



```

```plaintext
# 复制本文件为 .env（与 README 一样放在仓库根目录），启动时会自动读取

# ======= LLM Provider =======
# ollama (local) | deepseek (remote)
LLM_PROVIDER=ollama

# ======= Ollama (Local) =======
OLLAMA_BASE_URL=http://localhost:11434
LLM_MODEL=qwen2.5:7b
EMBED_MODEL=nomic-embed-text

# ======= DeepSeek (Optional) =======
# DEEPSEEK_BASE_URL=https://api.deepseek.com
# DEEPSEEK_API_KEY=your_api_key_here
# LLM_MODEL=deepseek-chat

# ======= RAG =======
RAG_TOP_K=5
# 命中阈值：太低会带入不相关内容；太高可能“宁可不命中”
RAG_MIN_SCORE=0.38
# 关键词重叠过滤：要求 RAG chunk 至少包含多少个来自问题的关键词片段
RAG_MIN_KEYWORD_HITS=1

# ======= Logging =======
LOG_LEVEL=INFO
LOG_LLM_IO=true
LOG_LLM_MAX_CHARS=4000
LOG_MSG_MAX_CHARS=500



```

```markdown
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

