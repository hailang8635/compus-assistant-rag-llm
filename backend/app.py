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
        "你是热心的大学校园生活助手，帮上海大学的同学们提供提供学习、生活方面的各种咨询答疑。\n"
        "你会收到一些【本地资料片段】作为上下文，请优先基于这些资料回答，并给出清晰可执行的步骤。\n"
        "若资料不足，请明确说明不确定，并给出建议的官方咨询路径（学院教务/研究生院/信息办/辅导员等）。\n"
        "输出支持 Markdown。\n"
    )


async def call_ollama(messages: list[dict], model: str) -> str:
    """
    Call local Ollama: https://ollama.com
    """
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    timeout = float(os.getenv("OLLAMA_TIMEOUT", "120"))
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
            "<-------- RAG hits: none (filtered). min_score=%s min_keyword_hits=%s top_k=%s",
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


