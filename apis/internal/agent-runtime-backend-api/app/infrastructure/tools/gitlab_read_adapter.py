"""GitLab read adapter for Bob's MCP gateway."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import httpx


class GitLabReadAdapterError(Exception):
    def __init__(self, code: str, message: str | None = None) -> None:
        super().__init__(message or code)
        self.code = code


@dataclass(frozen=True)
class GitLabReadAdapter:
    api_url: str = "https://gitlab.tools.thesmartcrew.com/api/v4"
    token: str | None = None
    timeout_seconds: float = 10.0
    max_file_bytes: int = 16_000

    @classmethod
    def from_env(cls) -> "GitLabReadAdapter":
        raw_timeout = os.environ.get("CROO_GITLAB_TIMEOUT_SECONDS") or os.environ.get("GITLAB_TIMEOUT_SECONDS") or "10"
        try:
            timeout = float(raw_timeout)
        except ValueError:
            timeout = 10.0

        raw_max_file_bytes = os.environ.get("CROO_GITLAB_MAX_FILE_BYTES", "16000")
        try:
            max_file_bytes = int(raw_max_file_bytes)
        except ValueError:
            max_file_bytes = 16_000

        return cls(
            api_url=(
                os.environ.get("CROO_GITLAB_API_URL")
                or os.environ.get("GITLAB_API_URL")
                or "https://gitlab.tools.thesmartcrew.com/api/v4"
            ).rstrip("/"),
            token=os.environ.get("CROO_GITLAB_TOKEN") or os.environ.get("GITLAB_TOKEN") or os.environ.get("GLAB_TOKEN"),
            timeout_seconds=max(1.0, min(timeout, 30.0)),
            max_file_bytes=max(1_000, min(max_file_bytes, 64_000)),
        )

    def list_projects(self, *, query: str = "", limit: int = 20) -> dict[str, Any]:
        params: dict[str, Any] = {
            "membership": "true",
            "simple": "true",
            "per_page": self._limit(limit),
        }
        if query.strip():
            params["search"] = query.strip()
        rows = self._request_json("GET", "/projects", params=params)
        projects = [
            {
                "project_id": row.get("id"),
                "path_with_namespace": row.get("path_with_namespace"),
                "name": row.get("name"),
                "default_branch": row.get("default_branch"),
                "web_url": row.get("web_url"),
            }
            for row in rows
            if isinstance(row, dict)
        ]
        return {
            "source": "GitLab",
            "capability": "projects",
            "operation": "list_projects",
            "query": query.strip(),
            "limit": self._limit(limit),
            "returned": len(projects),
            "projects": projects,
        }

    def list_branches(self, *, project_id: str, limit: int = 20) -> dict[str, Any]:
        project = self._required_project_id(project_id)
        rows = self._request_json(
            "GET",
            f"/projects/{_url_part(project)}/repository/branches",
            params={"per_page": self._limit(limit)},
        )
        branches = [
            {
                "name": row.get("name"),
                "default": row.get("default"),
                "protected": row.get("protected"),
                "merged": row.get("merged"),
                "commit_id": (row.get("commit") or {}).get("id") if isinstance(row.get("commit"), dict) else None,
                "commit_title": (row.get("commit") or {}).get("title") if isinstance(row.get("commit"), dict) else None,
            }
            for row in rows
            if isinstance(row, dict)
        ]
        return {
            "source": "GitLab",
            "capability": "branches",
            "operation": "list_branches",
            "project_id": project,
            "limit": self._limit(limit),
            "returned": len(branches),
            "branches": branches,
        }

    def list_tree(self, *, project_id: str, path: str = "", ref: str = "", limit: int = 50) -> dict[str, Any]:
        project = self._required_project_id(project_id)
        params: dict[str, Any] = {"per_page": self._limit(limit)}
        if path.strip():
            params["path"] = path.strip().lstrip("/")
        if ref.strip():
            params["ref"] = ref.strip()
        rows = self._request_json("GET", f"/projects/{_url_part(project)}/repository/tree", params=params)
        items = [
            {
                "id": row.get("id"),
                "name": row.get("name"),
                "type": row.get("type"),
                "path": row.get("path"),
                "mode": row.get("mode"),
            }
            for row in rows
            if isinstance(row, dict)
        ]
        return {
            "source": "GitLab",
            "capability": "tree",
            "operation": "list_tree",
            "project_id": project,
            "path": path.strip().lstrip("/"),
            "ref": ref.strip(),
            "limit": self._limit(limit),
            "returned": len(items),
            "items": items,
        }

    def get_file(self, *, project_id: str, path: str, ref: str = "") -> dict[str, Any]:
        project = self._required_project_id(project_id)
        file_path = path.strip().lstrip("/")
        if not file_path:
            raise GitLabReadAdapterError("gitlab_file_path_required")
        params = {"ref": ref.strip() or "HEAD"}
        text = self._request_text(
            "GET",
            f"/projects/{_url_part(project)}/repository/files/{_url_part(file_path)}/raw",
            params=params,
        )
        encoded = text.encode("utf-8")
        truncated = len(encoded) > self.max_file_bytes
        if truncated:
            text = encoded[: self.max_file_bytes].decode("utf-8", errors="ignore")
        return {
            "source": "GitLab",
            "capability": "files",
            "operation": "get_file",
            "project_id": project,
            "path": file_path,
            "ref": params["ref"],
            "content": text,
            "content_truncated": truncated,
            "max_file_bytes": self.max_file_bytes,
        }

    def search_code(self, *, project_id: str, query: str, ref: str = "", limit: int = 20) -> dict[str, Any]:
        project = self._required_project_id(project_id)
        search = query.strip()
        if not search:
            raise GitLabReadAdapterError("gitlab_search_query_required")
        params: dict[str, Any] = {"scope": "blobs", "search": search, "per_page": self._limit(limit)}
        if ref.strip():
            params["ref"] = ref.strip()
        rows = self._request_json("GET", f"/projects/{_url_part(project)}/search", params=params)
        results = [
            {
                "filename": row.get("filename"),
                "path": row.get("path"),
                "ref": row.get("ref"),
                "startline": row.get("startline"),
                "project_id": row.get("project_id"),
            }
            for row in rows
            if isinstance(row, dict)
        ]
        return {
            "source": "GitLab",
            "capability": "search-code",
            "operation": "search_code",
            "project_id": project,
            "query": search,
            "ref": ref.strip(),
            "limit": self._limit(limit),
            "returned": len(results),
            "results": results,
        }

    def _request_json(self, method: str, path: str, *, params: dict[str, Any]) -> Any:
        response = self._request(method, path, params=params)
        try:
            return response.json()
        except ValueError as exc:
            raise GitLabReadAdapterError("gitlab_invalid_json_response") from exc

    def _request_text(self, method: str, path: str, *, params: dict[str, Any]) -> str:
        response = self._request(method, path, params=params)
        return response.text

    def _request(self, method: str, path: str, *, params: dict[str, Any]) -> httpx.Response:
        if not self.token:
            raise GitLabReadAdapterError("gitlab_token_missing")
        headers = {"PRIVATE-TOKEN": self.token}
        try:
            with httpx.Client(timeout=self.timeout_seconds, headers=headers) as client:
                response = client.request(method, f"{self.api_url}{path}", params=params)
                response.raise_for_status()
                return response
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code if exc.response is not None else "unknown"
            raise GitLabReadAdapterError(f"gitlab_http_{status_code}") from exc
        except httpx.RequestError as exc:
            raise GitLabReadAdapterError("gitlab_request_failed") from exc

    def _required_project_id(self, project_id: str) -> str:
        project = project_id.strip()
        if not project:
            raise GitLabReadAdapterError("gitlab_project_id_required")
        return project

    def _limit(self, value: int) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            parsed = 20
        return max(1, min(parsed, 100))


def _url_part(value: str) -> str:
    return quote(value, safe="")
