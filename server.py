import json
import logging
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

from mcp.server.fastmcp import FastMCP

import config
from models import ServiceResult
from services.vito import VitoService
from services.asana import AsanaService
from services.notion import NotionService

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(server):
    """Manage service lifecycle - create on startup, close on shutdown."""
    services = {
        "vito": VitoService(),
        "asana": AsanaService(),
        "notion": NotionService(),
    }
    try:
        yield services
    finally:
        for svc in services.values():
            await svc.close()


mcp = FastMCP("meeting-automation", lifespan=lifespan)


# === Setup ===


@mcp.tool()
async def check_meeting_setup() -> str:
    """Check connection status for all external services (VITO, Asana, Notion).
    Returns which services are configured and accessible.
    Call this first to verify your setup before processing meetings."""
    ctx = mcp.get_context()
    services = ctx.request_context.lifespan_context

    vito_status = await services["vito"].check_connection()
    asana_status = await services["asana"].check_connection()
    notion_status = await services["notion"].check_connection()

    return ServiceResult(
        success=True,
        data={
            "vito": vito_status.data,
            "asana": asana_status.data,
            "notion": notion_status.data,
        },
    ).to_json()


# === STT ===


@mcp.tool()
async def process_meeting(
    audio_path: str = None,
    text: str = None,
    text_file_path: str = None,
) -> str:
    """Process meeting content for transcription.
    - audio_path: path to audio file - transcribes via VITO API (requires API key)
    - text: raw text input (e.g. copied from Clova Note)
    - text_file_path: path to .txt file
    Provide exactly one. Priority: text > text_file_path > audio_path.
    Returns transcript text for LLM to summarize and extract action items."""

    # Priority: text > text_file_path > audio_path
    if text:
        return ServiceResult(
            success=True,
            data={"text": text, "source": "direct_input"},
        ).to_json()

    if text_file_path:
        path = Path(text_file_path)
        if not path.exists():
            return ServiceResult(
                success=False,
                error_code="FILE_NOT_FOUND",
                error_message=f"Text file not found: {text_file_path}",
            ).to_json()
        try:
            content = path.read_text(encoding="utf-8")
            return ServiceResult(
                success=True,
                data={"text": content, "source": "text_file"},
            ).to_json()
        except Exception as e:
            return ServiceResult(
                success=False,
                error_code="FILE_READ_ERROR",
                error_message=f"Failed to read file: {e}",
            ).to_json()

    if audio_path:
        ctx = mcp.get_context()
        services = ctx.request_context.lifespan_context
        result = await services["vito"].transcribe(audio_path)
        return result.to_json()

    return ServiceResult(
        success=False,
        error_code="NO_INPUT",
        error_message="Provide one of: text, text_file_path, or audio_path.",
    ).to_json()


# === Asana (CRUD) ===


@mcp.tool()
async def create_meeting_task(
    name: str,
    project_id: str,
    assignee: str = None,
    due_on: str = None,
    notes: str = None,
) -> str:
    """Create a single Asana task from a meeting action item.
    - name: task title
    - project_id: Asana project GID (use get_meeting_tasks to find projects)
    - assignee: assignee email or GID (optional)
    - due_on: due date in YYYY-MM-DD format (optional)
    - notes: task description (optional)
    Returns created task_id. Call multiple times for multiple action items.
    Only call after user confirms the extracted action items."""
    ctx = mcp.get_context()
    services = ctx.request_context.lifespan_context
    result = await services["asana"].create_task(
        name=name, project_id=project_id, assignee=assignee, due_on=due_on, notes=notes
    )
    return result.to_json()


@mcp.tool()
async def update_meeting_task(
    task_id: str,
    name: str = None,
    notes: str = None,
    due_on: str = None,
    assignee: str = None,
) -> str:
    """Update an existing Asana task. Only provide fields to change.
    - task_id: Asana task GID (returned by create_meeting_task)"""
    ctx = mcp.get_context()
    services = ctx.request_context.lifespan_context
    result = await services["asana"].update_task(
        task_id=task_id, name=name, notes=notes, due_on=due_on, assignee=assignee
    )
    return result.to_json()


@mcp.tool()
async def get_meeting_tasks(project_id: str) -> str:
    """List tasks in an Asana project.
    - project_id: Asana project GID"""
    ctx = mcp.get_context()
    services = ctx.request_context.lifespan_context
    result = await services["asana"].get_tasks(project_id=project_id)
    return result.to_json()


@mcp.tool()
async def delete_meeting_task(task_id: str) -> str:
    """Delete an Asana task.
    - task_id: Asana task GID (returned by create_meeting_task)"""
    ctx = mcp.get_context()
    services = ctx.request_context.lifespan_context
    result = await services["asana"].delete_task(task_id=task_id)
    return result.to_json()


# === Notion (CRUD) ===


@mcp.tool()
async def save_meeting_notes(
    title: str,
    date_str: str,
    location: str = None,
    host_dept: str = None,
    attend_dept: str = None,
    attendees: str = None,
    agenda: str = None,
    summary: str = None,
    decisions: str = None,
    etc: str = None,
    author: str = None,
    url: str = None,
    database_id: str = None,
) -> str:
    """Save meeting notes to Notion database. Returns created page_id.
    - title: meeting title (회의명)
    - date_str: meeting date in YYYY-MM-DD format (회의일시)
    - location: meeting location (회의장소, optional)
    - host_dept: hosting department (주관부서, optional)
    - attend_dept: attending departments (참석부서, optional)
    - attendees: attendee names (참석자, optional)
    - agenda: meeting agenda (회의안건, optional)
    - summary: meeting content summary (회의내용, optional)
    - decisions: decisions and action items (결정사항, optional)
    - etc: other notes (기타, optional)
    - author: author name (작성자, defaults to DEFAULT_AUTHOR in .env)
    - url: related URL (optional)
    - database_id: overrides NOTION_DATABASE_ID in .env (optional)
    Today's date is set automatically as 작성일.
    Only call after user confirms the meeting summary."""
    ctx = mcp.get_context()
    services = ctx.request_context.lifespan_context

    properties = {
        "회의명": title,
        "date:회의일시:start": date_str,
        "date:회의일시:end": None,
        "회의장소": location or "",
        "주관부서": host_dept or "",
        "참석부서": attend_dept or "",
        "참석자": attendees or "",
        "회의안건": agenda or "",
        "회의내용": summary or "",
        "결정사항": decisions or "",
        "기타": etc or "",
        "date:작성일:start": date.today().isoformat(),
        "date:작성일:end": None,
        "작성자": author or config.DEFAULT_AUTHOR or "",
        "userDefined:URL": url or "",
    }

    result = await services["notion"].create_page(
        database_id=database_id or config.NOTION_DATABASE_ID,
        properties=properties,
    )
    return result.to_json()


@mcp.tool()
async def update_meeting_notes(
    page_id: str,
    title: str = None,
    date_str: str = None,
    location: str = None,
    host_dept: str = None,
    attend_dept: str = None,
    attendees: str = None,
    agenda: str = None,
    summary: str = None,
    decisions: str = None,
    etc: str = None,
    author: str = None,
    url: str = None,
) -> str:
    """Update existing Notion meeting notes. Only provide fields to change.
    - page_id: Notion page ID (returned by save_meeting_notes)"""
    ctx = mcp.get_context()
    services = ctx.request_context.lifespan_context

    properties = {}
    if title is not None:
        properties["회의명"] = title
    if date_str is not None:
        properties["date:회의일시:start"] = date_str
    if location is not None:
        properties["회의장소"] = location
    if host_dept is not None:
        properties["주관부서"] = host_dept
    if attend_dept is not None:
        properties["참석부서"] = attend_dept
    if attendees is not None:
        properties["참석자"] = attendees
    if agenda is not None:
        properties["회의안건"] = agenda
    if summary is not None:
        properties["회의내용"] = summary
    if decisions is not None:
        properties["결정사항"] = decisions
    if etc is not None:
        properties["기타"] = etc
    if author is not None:
        properties["작성자"] = author
    if url is not None:
        properties["userDefined:URL"] = url

    result = await services["notion"].update_page(page_id=page_id, properties=properties)
    return result.to_json()


@mcp.tool()
async def get_meeting_notes(database_id: str = None) -> str:
    """List meeting notes from Notion database.
    - database_id: overrides NOTION_DATABASE_ID in .env (optional)"""
    ctx = mcp.get_context()
    services = ctx.request_context.lifespan_context
    result = await services["notion"].get_pages(database_id=database_id)
    return result.to_json()


@mcp.tool()
async def delete_meeting_notes(page_id: str) -> str:
    """Archive (soft-delete) a Notion meeting notes page.
    - page_id: Notion page ID (returned by save_meeting_notes)"""
    ctx = mcp.get_context()
    services = ctx.request_context.lifespan_context
    result = await services["notion"].delete_page(page_id=page_id)
    return result.to_json()


# === Pipeline (One-shot) ===


@mcp.tool()
async def run_full_pipeline(
    audio_path: str = None,
    text: str = None,
    text_file_path: str = None,
    project_id: str = None,
    action_items_json: str = None,
    meeting_title: str = None,
    meeting_date: str = None,
    location: str = None,
    host_dept: str = None,
    attend_dept: str = None,
    attendees: str = None,
    agenda: str = None,
    summary: str = None,
    decisions: str = None,
    etc: str = None,
    author: str = None,
) -> str:
    """Run full meeting automation pipeline in one call (no intermediate confirmation).
    1. Transcribe audio or accept text input
    2. Create Asana tasks from action_items_json
    3. Save meeting notes to Notion
    For step-by-step control with user confirmation, use individual tools instead.
    - action_items_json: JSON array string, e.g. '[{"name":"...", "assignee":"...", "due_on":"..."}]'"""
    ctx = mcp.get_context()
    services = ctx.request_context.lifespan_context
    pipeline_results = {"steps": []}

    # Step 1: Process meeting input
    transcript_text = None
    if text:
        transcript_text = text
        pipeline_results["steps"].append({"step": "input", "source": "direct_text"})
    elif text_file_path:
        path = Path(text_file_path)
        if not path.exists():
            return ServiceResult(
                success=False,
                error_code="FILE_NOT_FOUND",
                error_message=f"Text file not found: {text_file_path}",
            ).to_json()
        transcript_text = path.read_text(encoding="utf-8")
        pipeline_results["steps"].append({"step": "input", "source": "text_file"})
    elif audio_path:
        vito_result = await services["vito"].transcribe(audio_path)
        if not vito_result.success:
            return vito_result.to_json()
        transcript_text = vito_result.data["text"]
        pipeline_results["steps"].append({"step": "transcription", "status": "success"})
    else:
        return ServiceResult(
            success=False,
            error_code="NO_INPUT",
            error_message="Provide one of: text, text_file_path, or audio_path.",
        ).to_json()

    # Step 2: Create Asana tasks
    created_tasks = []
    if action_items_json and project_id:
        try:
            action_items = json.loads(action_items_json)
        except json.JSONDecodeError as e:
            return ServiceResult(
                success=False,
                error_code="INVALID_JSON",
                error_message=f"Invalid action_items_json: {e}",
            ).to_json()

        for item in action_items:
            task_result = await services["asana"].create_task(
                name=item.get("name", ""),
                project_id=project_id,
                assignee=item.get("assignee"),
                due_on=item.get("due_on"),
                notes=item.get("notes"),
            )
            if task_result.success:
                created_tasks.append(task_result.data)
            else:
                created_tasks.append({"error": task_result.error_message, "name": item.get("name")})

        pipeline_results["steps"].append({
            "step": "asana_tasks",
            "created": len([t for t in created_tasks if "task_id" in t]),
            "failed": len([t for t in created_tasks if "error" in t]),
        })

    # Step 3: Save to Notion
    notion_result = None
    if meeting_title:
        properties = {
            "회의명": meeting_title,
            "date:회의일시:start": meeting_date or date.today().isoformat(),
            "date:회의일시:end": None,
            "회의장소": location or "",
            "주관부서": host_dept or "",
            "참석부서": attend_dept or "",
            "참석자": attendees or "",
            "회의안건": agenda or "",
            "회의내용": summary or transcript_text or "",
            "결정사항": decisions or "",
            "기타": etc or "",
            "date:작성일:start": date.today().isoformat(),
            "date:작성일:end": None,
            "작성자": author or config.DEFAULT_AUTHOR or "",
            "userDefined:URL": "",
        }
        notion_result = await services["notion"].create_page(
            database_id=config.NOTION_DATABASE_ID,
            properties=properties,
        )
        pipeline_results["steps"].append({
            "step": "notion",
            "status": "success" if notion_result.success else "failed",
            "page_id": notion_result.data.get("page_id") if notion_result.success else None,
        })

    pipeline_results["transcript_text"] = transcript_text
    pipeline_results["asana_tasks"] = created_tasks
    pipeline_results["notion"] = notion_result.data if notion_result and notion_result.success else None

    return ServiceResult(success=True, data=pipeline_results).to_json()


if __name__ == "__main__":
    mcp.run()
