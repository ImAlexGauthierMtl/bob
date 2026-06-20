"""Factory Supabase read adapter for Bob's MCP gateway."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import psycopg
from psycopg.rows import dict_row


class FactorySupabaseAdapterError(Exception):
    def __init__(self, code: str, message: str | None = None) -> None:
        super().__init__(message or code)
        self.code = code


@dataclass(frozen=True)
class FactorySupabaseAdapter:
    db_url: str | None = None
    connect_timeout: int = 10

    @classmethod
    def from_env(cls) -> "FactorySupabaseAdapter":
        raw_timeout = os.environ.get("FACTORY_SUPABASE_CONNECT_TIMEOUT_SECONDS", "10")
        try:
            timeout = int(raw_timeout)
        except ValueError:
            timeout = 10
        return cls(
            db_url=os.environ.get("FACTORY_SUPABASE_DB_URL") or os.environ.get("SUPABASE_DB_URL"),
            connect_timeout=max(1, min(timeout, 30)),
        )

    def list_requests(
        self,
        *,
        project_id: str = "",
        query: str = "",
        status: str = "",
        limit: int = 25,
        offset: int = 0,
    ) -> dict[str, Any]:
        max_limit = max(1, min(int(limit or 25), 100))
        safe_offset = max(0, int(offset or 0))
        filters = ["true"]
        params: dict[str, Any] = {
            "project_id": project_id.strip(),
            "query": f"%{query.strip()}%",
            "status": status.strip().upper(),
            "limit": max_limit,
            "offset": safe_offset,
        }
        if params["project_id"]:
            filters.append("r.project_id = %(project_id)s::uuid")
        if params["status"]:
            filters.append("r.status = %(status)s")
        if query.strip():
            filters.append(
                """
                concat_ws(' ',
                    r.id::text,
                    r.project_name::text,
                    r.client_name::text,
                    r.title::text,
                    r.status::text,
                    r.summary::text,
                    r.target_area::text
                ) ILIKE %(query)s
                """
            )
        where_sql = " AND ".join(filters)
        with self._connect() as conn:
            total = self._fetch_one(
                conn,
                f"SELECT COUNT(*)::int AS total_matching FROM public.v_factory_request_light r WHERE {where_sql}",
                params,
            )
            rows = self._fetch_all(
                conn,
                f"""
                SELECT
                  r.id::text AS request_id,
                  r.project_id::text AS project_id,
                  r.project_number,
                  r.project_name,
                  r.client_name,
                  r.title,
                  r.status,
                  r.priority_label,
                  r.summary,
                  r.target_area,
                  r.url,
                  r.screenshot_path,
                  r.annotated_screenshot_path,
                  r.created_at,
                  r.updated_at
                FROM public.v_factory_request_light r
                WHERE {where_sql}
                ORDER BY r.created_at, r.id
                LIMIT %(limit)s
                OFFSET %(offset)s
                """,
                params,
            )
        total_matching = int(total.get("total_matching") or 0)
        return {
            "source": "Factory Supabase",
            "surface": "public.v_factory_request_light",
            "capability": "requests-queues",
            "operation": "list_requests",
            "status": params["status"],
            "project_id": params["project_id"],
            "query": query.strip(),
            "limit": max_limit,
            "offset": safe_offset,
            "total_matching": total_matching,
            "returned": len(rows),
            "coverage": "complete" if safe_offset + len(rows) >= total_matching else "incomplete",
            "requests": rows,
        }

    def list_queue_by_project(
        self,
        *,
        status: str = "NEW",
        limit: int = 25,
        offset: int = 0,
    ) -> dict[str, Any]:
        max_limit = max(1, min(int(limit or 25), 100))
        safe_offset = max(0, int(offset or 0))
        params: dict[str, Any] = {
            "status": (status or "NEW").strip().upper(),
            "limit": max_limit,
            "offset": safe_offset,
        }
        with self._connect() as conn:
            totals = self._fetch_one(
                conn,
                """
                SELECT
                  COUNT(DISTINCT r.project_id)::int AS total_projects,
                  COUNT(*)::int AS total_requests
                FROM public.v_factory_request_light r
                WHERE r.status = %(status)s
                """,
                params,
            )
            rows = self._fetch_all(
                conn,
                """
                WITH ranked AS (
                  SELECT
                    r.project_id::text AS project_id,
                    r.project_number,
                    r.project_name,
                    r.client_name,
                    r.id::text AS request_id,
                    r.title,
                    r.priority_label,
                    r.created_at,
                    COUNT(*) OVER (PARTITION BY r.project_id)::int AS request_count,
                    ROW_NUMBER() OVER (
                      PARTITION BY r.project_id
                      ORDER BY r.created_at, r.id
                    ) AS project_rank
                  FROM public.v_factory_request_light r
                  WHERE r.status = %(status)s
                )
                SELECT
                  project_id,
                  project_number,
                  project_name,
                  client_name,
                  request_count,
                  request_id AS oldest_request_id,
                  title AS oldest_request_title,
                  priority_label AS oldest_request_priority,
                  created_at AS oldest_request_created_at
                FROM ranked
                WHERE project_rank = 1
                ORDER BY created_at, client_name, project_name
                LIMIT %(limit)s
                OFFSET %(offset)s
                """,
                params,
            )
        total_projects = int(totals.get("total_projects") or 0)
        return {
            "source": "Factory Supabase",
            "surface": "public.v_factory_request_light",
            "capability": "requests-queues",
            "operation": "list_queue_by_project",
            "status": params["status"],
            "limit": max_limit,
            "offset": safe_offset,
            "total_projects": total_projects,
            "total_requests": int(totals.get("total_requests") or 0),
            "returned_projects": len(rows),
            "coverage": "complete" if safe_offset + len(rows) >= total_projects else "incomplete",
            "projects": rows,
        }

    def get_request(self, *, request_id: str) -> dict[str, Any]:
        cleaned_request_id = request_id.strip()
        if not cleaned_request_id:
            raise FactorySupabaseAdapterError("request_id_required")
        with self._connect() as conn:
            row = self._fetch_one(
                conn,
                """
                SELECT
                  r.id::text AS request_id,
                  r.organization_id::text AS organization_id,
                  r.project_id::text AS project_id,
                  r.project_number,
                  r.project_name,
                  r.client_name,
                  r.factory_external_id,
                  r.title,
                  r.status,
                  r.priority_label,
                  r.summary,
                  r.classification,
                  r.target_area,
                  r.acceptance_criteria,
                  r.expected_state,
                  r.expected_user_outcome,
                  r.dev_validation_qa,
                  r.url,
                  r.screenshot_path,
                  r.annotated_screenshot_path,
                  r.created_at,
                  r.updated_at
                FROM public.v_factory_request_light r
                WHERE r.id = %(request_id)s::uuid
                LIMIT 1
                """,
                {"request_id": cleaned_request_id},
            )
        if not row:
            raise FactorySupabaseAdapterError("factory_request_not_found")
        return {
            "source": "Factory Supabase",
            "surface": "public.v_factory_request_light",
            "capability": "requests-queues",
            "operation": "get_request",
            "request": row,
        }

    def _connect(self) -> psycopg.Connection:
        if not self.db_url:
            raise FactorySupabaseAdapterError("factory_supabase_db_url_missing")
        try:
            return psycopg.connect(
                self.db_url,
                row_factory=dict_row,
                connect_timeout=self.connect_timeout,
            )
        except Exception as exc:  # pragma: no cover - exact psycopg errors vary by environment.
            raise FactorySupabaseAdapterError("factory_supabase_connection_failed", str(exc)) from exc

    @staticmethod
    def _fetch_one(conn: psycopg.Connection, query: str, params: dict[str, Any]) -> dict[str, Any]:
        with conn.cursor() as cur:
            cur.execute(query, params)
            row = cur.fetchone()
            return dict(row) if row else {}

    @staticmethod
    def _fetch_all(conn: psycopg.Connection, query: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return [dict(row) for row in cur.fetchall()]
