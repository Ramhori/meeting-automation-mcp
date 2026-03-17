from dataclasses import dataclass, asdict
import json


@dataclass
class ServiceResult:
    success: bool
    data: dict | None = None
    error_code: str | None = None
    error_message: str | None = None
    recoverable: bool = False

    def to_json(self) -> str:
        """Convert to JSON string for MCP tool return value."""
        return json.dumps(asdict(self), ensure_ascii=False)


@dataclass
class TranscriptResult:
    text: str
    duration: float
    language: str
    segments: list[dict] | None = None
