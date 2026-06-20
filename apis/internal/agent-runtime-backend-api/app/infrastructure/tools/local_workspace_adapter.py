"""Read-only local workspace adapter for Bob's MCP gateway."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class LocalWorkspaceAdapterError(Exception):
    def __init__(self, code: str, message: str | None = None) -> None:
        super().__init__(message or code)
        self.code = code


_BLOCKED_PARTS = {
    ".env",
    ".git",
    ".ssh",
    ".gnupg",
    ".npmrc",
    ".pypirc",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".venv",
    "venv",
}
_BLOCKED_FRAGMENTS = ("secret", "token", "credential", "password", "private-key", "id_rsa")
_DEFAULT_EXTENSIONS = {
    ".css",
    ".html",
    ".js",
    ".json",
    ".md",
    ".py",
    ".sql",
    ".toml",
    ".ts",
    ".txt",
    ".yaml",
    ".yml",
}


@dataclass(frozen=True)
class LocalWorkspaceAdapter:
    root: Path | None = None
    enabled: bool = False
    max_file_bytes: int = 16_000
    max_search_files: int = 500

    @classmethod
    def from_env(cls) -> "LocalWorkspaceAdapter":
        raw_root = os.environ.get("BOB_LOCAL_WORKSPACE_ROOT") or os.environ.get("CDE_WORKSPACE_ROOT")
        raw_enabled = os.environ.get("BOB_LOCAL_WORKSPACE_ENABLED", "").strip().lower()
        enabled = raw_enabled in {"1", "true", "yes", "on"}
        raw_max_file_bytes = os.environ.get("BOB_LOCAL_WORKSPACE_MAX_FILE_BYTES", "16000")
        raw_max_search_files = os.environ.get("BOB_LOCAL_WORKSPACE_MAX_SEARCH_FILES", "500")
        try:
            max_file_bytes = int(raw_max_file_bytes)
        except ValueError:
            max_file_bytes = 16_000
        try:
            max_search_files = int(raw_max_search_files)
        except ValueError:
            max_search_files = 500
        return cls(
            root=Path(raw_root).expanduser().resolve() if raw_root else None,
            enabled=enabled,
            max_file_bytes=max(1_000, min(max_file_bytes, 64_000)),
            max_search_files=max(50, min(max_search_files, 2_000)),
        )

    def list_path(self, *, path: str = "", limit: int = 50) -> dict[str, Any]:
        target = self._resolve(path)
        if not target.exists():
            raise LocalWorkspaceAdapterError("local_workspace_path_not_found")
        if target.is_file():
            return self.read_file(path=path)
        if not target.is_dir():
            raise LocalWorkspaceAdapterError("local_workspace_path_not_readable")
        max_limit = _bounded_int(limit, default=50, minimum=1, maximum=100)
        items: list[dict[str, Any]] = []
        for child in sorted(target.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower())):
            if len(items) >= max_limit:
                break
            if self._is_blocked(child):
                continue
            items.append(
                {
                    "name": child.name,
                    "path": self._relative_path(child),
                    "type": "directory" if child.is_dir() else "file",
                    "size_bytes": child.stat().st_size if child.is_file() else None,
                }
            )
        return {
            "source": "local_workspace",
            "capability": "local-files",
            "operation": "list_path",
            "path": self._relative_path(target),
            "limit": max_limit,
            "returned": len(items),
            "items": items,
        }

    def read_file(self, *, path: str) -> dict[str, Any]:
        target = self._resolve(path)
        if not target.exists():
            raise LocalWorkspaceAdapterError("local_workspace_path_not_found")
        if not target.is_file():
            raise LocalWorkspaceAdapterError("local_workspace_file_required")
        if target.suffix.lower() not in _DEFAULT_EXTENSIONS:
            raise LocalWorkspaceAdapterError("local_workspace_file_type_not_allowed")
        raw = target.read_bytes()
        truncated = len(raw) > self.max_file_bytes
        content = raw[: self.max_file_bytes].decode("utf-8", errors="ignore")
        return {
            "source": "local_workspace",
            "capability": "local-files",
            "operation": "read_file",
            "path": self._relative_path(target),
            "size_bytes": len(raw),
            "content": content,
            "content_truncated": truncated,
            "max_file_bytes": self.max_file_bytes,
        }

    def search(self, *, query: str, path: str = "", limit: int = 20) -> dict[str, Any]:
        search = " ".join(query.lower().split())
        if not search:
            raise LocalWorkspaceAdapterError("local_workspace_query_required")
        start = self._resolve(path)
        if not start.exists():
            raise LocalWorkspaceAdapterError("local_workspace_path_not_found")
        max_limit = _bounded_int(limit, default=20, minimum=1, maximum=100)
        scanned = 0
        matches: list[dict[str, Any]] = []
        files = [start] if start.is_file() else start.rglob("*")
        for candidate in files:
            if scanned >= self.max_search_files or len(matches) >= max_limit:
                break
            if not candidate.is_file() or self._is_blocked(candidate):
                continue
            if candidate.suffix.lower() not in _DEFAULT_EXTENSIONS:
                continue
            scanned += 1
            relative = self._relative_path(candidate)
            name_match = search in relative.lower()
            content_match = False
            preview = ""
            try:
                raw = candidate.read_bytes()[: self.max_file_bytes]
                text = raw.decode("utf-8", errors="ignore")
            except OSError:
                continue
            if search in text.lower():
                content_match = True
                preview = _preview(text=text, query=search)
            if name_match or content_match:
                matches.append(
                    {
                        "path": relative,
                        "match": "name_and_content" if name_match and content_match else "content" if content_match else "name",
                        "preview": preview,
                    }
                )
        return {
            "source": "local_workspace",
            "capability": "local-files",
            "operation": "search",
            "query": query,
            "path": self._relative_path(start),
            "limit": max_limit,
            "scanned_files": scanned,
            "returned": len(matches),
            "matches": matches,
        }

    def _resolve(self, path: str) -> Path:
        if not self.enabled:
            raise LocalWorkspaceAdapterError("local_workspace_disabled")
        if self.root is None:
            raise LocalWorkspaceAdapterError("local_workspace_root_missing")
        if not self.root.exists() or not self.root.is_dir():
            raise LocalWorkspaceAdapterError("local_workspace_root_not_found")
        relative = path.strip().lstrip("/")
        target = (self.root / relative).resolve()
        try:
            target.relative_to(self.root)
        except ValueError as exc:
            raise LocalWorkspaceAdapterError("local_workspace_path_outside_root") from exc
        if self._is_blocked(target):
            raise LocalWorkspaceAdapterError("local_workspace_path_blocked")
        return target

    def _is_blocked(self, path: Path) -> bool:
        lower_parts = {part.lower() for part in path.parts}
        if lower_parts & _BLOCKED_PARTS:
            return True
        lower_name = path.name.lower()
        return any(fragment in lower_name for fragment in _BLOCKED_FRAGMENTS)

    def _relative_path(self, path: Path) -> str:
        if self.root is None:
            return ""
        try:
            return str(path.resolve().relative_to(self.root))
        except ValueError:
            return ""


def _preview(*, text: str, query: str) -> str:
    normalized = text.lower()
    index = normalized.find(query)
    if index < 0:
        return ""
    start = max(0, index - 120)
    end = min(len(text), index + len(query) + 120)
    return " ".join(text[start:end].split())


def _bounded_int(value: Any, *, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))
