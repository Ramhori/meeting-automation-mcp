import logging

import httpx

import config
from models import ServiceResult

logger = logging.getLogger(__name__)

ASANA_BASE_URL = "https://app.asana.com/api/1.0"


class AsanaService:
    def __init__(self):
        self.client = httpx.AsyncClient(
            base_url=ASANA_BASE_URL,
            headers={
                "Authorization": f"Bearer {config.ASANA_TOKEN}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

    async def create_task(
        self,
        name: str,
        project_id: str,
        assignee: str | None = None,
        due_on: str | None = None,
        notes: str | None = None,
    ) -> ServiceResult:
        """Create a single Asana task."""
        body = {"name": name, "projects": [project_id]}
        if assignee:
            body["assignee"] = assignee
        if due_on:
            body["due_on"] = due_on
        if notes:
            body["notes"] = notes

        try:
            resp = await self.client.post("/tasks", json={"data": body})
            if resp.status_code == 201:
                task = resp.json().get("data", {})
                return ServiceResult(
                    success=True,
                    data={"task_id": task.get("gid"), "name": task.get("name"), "url": task.get("permalink_url")},
                )
            return self._handle_error(resp)
        except Exception as e:
            return ServiceResult(success=False, error_code="UNKNOWN", error_message=str(e))

    async def update_task(
        self,
        task_id: str,
        name: str | None = None,
        notes: str | None = None,
        due_on: str | None = None,
        assignee: str | None = None,
    ) -> ServiceResult:
        """Update an existing Asana task."""
        body = {}
        if name is not None:
            body["name"] = name
        if notes is not None:
            body["notes"] = notes
        if due_on is not None:
            body["due_on"] = due_on
        if assignee is not None:
            body["assignee"] = assignee

        if not body:
            return ServiceResult(success=False, error_code="NO_FIELDS", error_message="No fields to update.")

        try:
            resp = await self.client.put(f"/tasks/{task_id}", json={"data": body})
            if resp.status_code == 200:
                task = resp.json().get("data", {})
                return ServiceResult(
                    success=True,
                    data={"task_id": task.get("gid"), "name": task.get("name")},
                )
            return self._handle_error(resp)
        except Exception as e:
            return ServiceResult(success=False, error_code="UNKNOWN", error_message=str(e))

    async def get_tasks(self, project_id: str) -> ServiceResult:
        """List tasks in an Asana project."""
        try:
            resp = await self.client.get(
                "/tasks",
                params={
                    "project": project_id,
                    "opt_fields": "name,assignee.name,due_on,completed,notes,permalink_url",
                },
            )
            if resp.status_code == 200:
                tasks = resp.json().get("data", [])
                return ServiceResult(
                    success=True,
                    data={
                        "tasks": [
                            {
                                "task_id": t.get("gid"),
                                "name": t.get("name"),
                                "assignee": t.get("assignee", {}).get("name") if t.get("assignee") else None,
                                "due_on": t.get("due_on"),
                                "completed": t.get("completed"),
                                "url": t.get("permalink_url"),
                            }
                            for t in tasks
                        ],
                        "count": len(tasks),
                    },
                )
            return self._handle_error(resp)
        except Exception as e:
            return ServiceResult(success=False, error_code="UNKNOWN", error_message=str(e))

    async def delete_task(self, task_id: str) -> ServiceResult:
        """Delete an Asana task."""
        try:
            resp = await self.client.delete(f"/tasks/{task_id}")
            if resp.status_code == 200:
                return ServiceResult(success=True, data={"deleted": task_id})
            return self._handle_error(resp)
        except Exception as e:
            return ServiceResult(success=False, error_code="UNKNOWN", error_message=str(e))

    async def check_connection(self) -> ServiceResult:
        """Check if Asana API is configured and accessible."""
        if not config.ASANA_TOKEN:
            return ServiceResult(
                success=True,
                data={"status": "not_configured", "message": "ASANA_TOKEN not set in .env file."},
            )
        try:
            resp = await self.client.get("/users/me")
            if resp.status_code == 200:
                user = resp.json().get("data", {})
                return ServiceResult(
                    success=True,
                    data={"status": "connected", "message": f"Connected as {user.get('name', 'unknown')}"},
                )
            return self._handle_error(resp)
        except Exception as e:
            return ServiceResult(success=False, error_code="UNKNOWN", error_message=str(e))

    def _handle_error(self, resp: httpx.Response) -> ServiceResult:
        """Convert HTTP error response to ServiceResult."""
        recoverable = resp.status_code in {429, 500, 502, 503}
        error_code_map = {
            400: "BAD_REQUEST",
            401: "AUTH_EXPIRED",
            403: "PERMISSION_DENIED",
            404: "NOT_FOUND",
            429: "RATE_LIMIT",
        }
        error_code = error_code_map.get(resp.status_code, f"HTTP_{resp.status_code}")

        data = None
        if resp.status_code == 429:
            retry_after = resp.headers.get("Retry-After")
            if retry_after:
                data = {"retry_after": int(retry_after)}

        return ServiceResult(
            success=False,
            error_code=error_code,
            error_message=f"Asana API error {resp.status_code}: {resp.text[:200]}",
            recoverable=recoverable,
            data=data,
        )

    async def close(self):
        """Close httpx connection pool."""
        await self.client.aclose()
