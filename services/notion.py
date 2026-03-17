import logging
from datetime import date

import httpx

import config
from models import ServiceResult

logger = logging.getLogger(__name__)

NOTION_BASE_URL = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


class NotionService:
    def __init__(self):
        self.client = httpx.AsyncClient(
            base_url=NOTION_BASE_URL,
            headers={
                "Authorization": f"Bearer {config.NOTION_TOKEN}",
                "Content-Type": "application/json",
                "Notion-Version": NOTION_VERSION,
            },
            timeout=30.0,
        )

    def _build_properties(self, props: dict) -> dict:
        """Convert flat key-value pairs to Notion property format.

        Key conventions:
        - "title_field": title property
        - "date:field_name:start" / "date:field_name:end": date property
        - "userDefined:field_name": prefixed to avoid Notion reserved words
        - everything else: rich_text property
        """
        notion_props = {}
        for key, value in props.items():
            if value is None:
                continue

            # Date property: "date:회의일시:start"
            if key.startswith("date:"):
                parts = key.split(":")
                field_name = parts[1]
                date_part = parts[2] if len(parts) > 2 else "start"

                if field_name not in notion_props:
                    notion_props[field_name] = {"date": {"start": None, "end": None}}

                notion_props[field_name]["date"][date_part] = value

            # URL property: "userDefined:URL"
            elif key.startswith("userDefined:"):
                field_name = key.split(":", 1)[1]
                notion_props[field_name] = {"url": value if value else None}

            # Title property: first key named "회의명" or explicit title
            elif key == "회의명":
                notion_props[key] = {
                    "title": [{"text": {"content": value}}]
                }

            # Default: rich_text
            else:
                notion_props[key] = {
                    "rich_text": [{"text": {"content": value}}]
                }

        return notion_props

    async def create_page(
        self,
        database_id: str,
        properties: dict,
    ) -> ServiceResult:
        """Create a page in a Notion database."""
        db_id = database_id or config.NOTION_DATABASE_ID
        if not db_id:
            return ServiceResult(
                success=False,
                error_code="NO_DATABASE_ID",
                error_message="NOTION_DATABASE_ID not set. Provide database_id or set it in .env file.",
            )

        notion_props = self._build_properties(properties)

        try:
            resp = await self.client.post(
                "/pages",
                json={
                    "parent": {"database_id": db_id},
                    "properties": notion_props,
                },
            )
            if resp.status_code == 200:
                page = resp.json()
                return ServiceResult(
                    success=True,
                    data={"page_id": page.get("id"), "url": page.get("url")},
                )
            return self._handle_error(resp)
        except Exception as e:
            return ServiceResult(success=False, error_code="UNKNOWN", error_message=str(e))

    async def update_page(self, page_id: str, properties: dict) -> ServiceResult:
        """Update an existing Notion page."""
        if not properties:
            return ServiceResult(success=False, error_code="NO_FIELDS", error_message="No fields to update.")

        notion_props = self._build_properties(properties)

        try:
            resp = await self.client.patch(
                f"/pages/{page_id}",
                json={"properties": notion_props},
            )
            if resp.status_code == 200:
                page = resp.json()
                return ServiceResult(
                    success=True,
                    data={"page_id": page.get("id"), "url": page.get("url")},
                )
            return self._handle_error(resp)
        except Exception as e:
            return ServiceResult(success=False, error_code="UNKNOWN", error_message=str(e))

    async def get_pages(self, database_id: str | None = None) -> ServiceResult:
        """List pages from a Notion database."""
        db_id = database_id or config.NOTION_DATABASE_ID
        if not db_id:
            return ServiceResult(
                success=False,
                error_code="NO_DATABASE_ID",
                error_message="NOTION_DATABASE_ID not set. Provide database_id or set it in .env file.",
            )

        try:
            resp = await self.client.post(
                f"/databases/{db_id}/query",
                json={"page_size": 50},
            )
            if resp.status_code == 200:
                results = resp.json().get("results", [])
                pages = []
                for page in results:
                    props = page.get("properties", {})
                    title = ""
                    if "회의명" in props:
                        title_arr = props["회의명"].get("title", [])
                        if title_arr:
                            title = title_arr[0].get("text", {}).get("content", "")
                    pages.append({
                        "page_id": page.get("id"),
                        "title": title,
                        "url": page.get("url"),
                        "created_time": page.get("created_time"),
                    })
                return ServiceResult(
                    success=True,
                    data={"pages": pages, "count": len(pages)},
                )
            return self._handle_error(resp)
        except Exception as e:
            return ServiceResult(success=False, error_code="UNKNOWN", error_message=str(e))

    async def delete_page(self, page_id: str) -> ServiceResult:
        """Archive (soft-delete) a Notion page."""
        try:
            resp = await self.client.patch(
                f"/pages/{page_id}",
                json={"archived": True},
            )
            if resp.status_code == 200:
                return ServiceResult(success=True, data={"archived": page_id})
            return self._handle_error(resp)
        except Exception as e:
            return ServiceResult(success=False, error_code="UNKNOWN", error_message=str(e))

    async def check_connection(self) -> ServiceResult:
        """Check if Notion API is configured and accessible."""
        if not config.NOTION_TOKEN:
            return ServiceResult(
                success=True,
                data={"status": "not_configured", "message": "NOTION_TOKEN not set in .env file."},
            )
        try:
            resp = await self.client.get("/users/me")
            if resp.status_code == 200:
                user = resp.json()
                return ServiceResult(
                    success=True,
                    data={"status": "connected", "message": f"Connected as {user.get('name', 'Notion Bot')}"},
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
            error_message=f"Notion API error {resp.status_code}: {resp.text[:200]}",
            recoverable=recoverable,
            data=data,
        )

    async def close(self):
        """Close httpx connection pool."""
        await self.client.aclose()
