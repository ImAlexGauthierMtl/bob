#!/usr/bin/env python3
"""Fetch a Zoho Desk ticket and its attachments."""

import argparse
import json
import os
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    print("ERROR: 'requests' package required. Install with: pip install requests")
    sys.exit(1)


BASE_URL = "https://desk.zoho.com/api/v1"


def get_headers() -> dict:
    """Build Zoho API headers from environment variables."""
    token = os.environ.get("ZOHO_DESK_API_TOKEN")
    org_id = os.environ.get("ZOHO_DESK_ORG_ID")

    if not token or not org_id:
        print("ERROR: Set ZOHO_DESK_API_TOKEN and ZOHO_DESK_ORG_ID environment variables")
        sys.exit(1)

    return {
        "Authorization": f"Zoho-oauthtoken {token}",
        "orgId": org_id,
        "Content-Type": "application/json",
    }


def fetch_ticket(ticket_id: str, headers: dict) -> dict:
    """Fetch ticket metadata."""
    resp = requests.get(f"{BASE_URL}/tickets/{ticket_id}", headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()


def fetch_attachments(ticket_id: str, headers: dict, output_dir: Path) -> list[dict]:
    """Fetch and download ticket attachments."""
    resp = requests.get(
        f"{BASE_URL}/tickets/{ticket_id}/attachments",
        headers=headers,
        timeout=30,
    )

    if resp.status_code == 204:
        return []

    resp.raise_for_status()
    attachments = resp.json().get("data", [])

    downloaded = []
    for att in attachments:
        att_id = att["id"]
        name = att.get("name", f"attachment_{att_id}")
        file_path = output_dir / name

        content_resp = requests.get(
            f"{BASE_URL}/tickets/{ticket_id}/attachments/{att_id}/content",
            headers=headers,
            timeout=60,
        )
        content_resp.raise_for_status()

        file_path.write_bytes(content_resp.content)
        downloaded.append({
            "id": att_id,
            "name": name,
            "path": str(file_path),
            "size": len(content_resp.content),
            "content_type": att.get("contentType", "unknown"),
        })

    return downloaded


def main():
    parser = argparse.ArgumentParser(description="Fetch Zoho Desk ticket and attachments")
    parser.add_argument("--ticket-id", required=True, help="Zoho Desk ticket ID")
    parser.add_argument("--output-dir", default=None, help="Output directory for attachments")
    args = parser.parse_args()

    headers = get_headers()
    output_dir = Path(args.output_dir or f"/tmp/zoho-{args.ticket_id}")
    output_dir.mkdir(parents=True, exist_ok=True)

    ticket = fetch_ticket(args.ticket_id, headers)
    attachments = fetch_attachments(args.ticket_id, headers, output_dir)

    result = {
        "ticket": {
            "id": ticket.get("id"),
            "ticket_number": ticket.get("ticketNumber"),
            "subject": ticket.get("subject"),
            "description": ticket.get("description"),
            "priority": ticket.get("priority"),
            "status": ticket.get("status"),
            "assignee": ticket.get("assignee", {}).get("name"),
            "created_time": ticket.get("createdTime"),
            "due_date": ticket.get("dueDate"),
            "cf_project_id": ticket.get("cf", {}).get("cf_project_id"),
        },
        "attachments": attachments,
        "output_dir": str(output_dir),
    }

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
