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


