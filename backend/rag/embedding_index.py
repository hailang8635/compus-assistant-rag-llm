from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import sqlite3
import struct
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import httpx


logger = logging.getLogger("campus_assistant")


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

        logger.info(
            "RAG reindex start: docs_dir=%s db_path=%s embed_model=%s docs_count=%s",
            str(self.docs_dir),
            str(self.db_path),
            self.embed_model,
            len(doc_paths),
        )

        # Clear
        with sqlite3.connect(self.db_path) as con:
            con.execute("DELETE FROM chunks")
            con.commit()

        total_chunks = 0
        per_doc_chunks: dict[str, int] = {}
        for p in doc_paths:
            doc_start = time.time()
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
                per_doc_chunks[p.name] = per_doc_chunks.get(p.name, 0) + 1

            logger.info(
                "RAG reindex doc done: source=%s chunks=%s seconds=%s",
                p.name,
                per_doc_chunks.get(p.name, 0),
                round(time.time() - doc_start, 2),
            )

        self._set_meta("docs_fingerprint", fp)
        self._set_meta("embed_model", self.embed_model)
        self._chunks = self._load_from_db()
        self._fingerprint = fp

        per_doc_list = [{"source": k, "chunks": int(v)} for k, v in sorted(per_doc_chunks.items())]
        logger.info(
            "RAG reindex done: %s",
            json.dumps(
                {
                    "docs_count": len(doc_paths),
                    "total_chunks": int(total_chunks),
                    "per_doc": per_doc_list,
                    "embed_model": self.embed_model,
                    "seconds": round(time.time() - start_ts, 2),
                },
                ensure_ascii=False,
            ),
        )

        return {
            "ok": True,
            "embed_model": self.embed_model,
            "docs": [p.name for p in doc_paths],
            "chunks": total_chunks,
            "per_doc_chunks": per_doc_list,
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


