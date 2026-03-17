import time
import asyncio
import logging
from pathlib import Path

import httpx

import config
from models import ServiceResult, TranscriptResult

logger = logging.getLogger(__name__)

VITO_POLL_INTERVAL = 3  # seconds
VITO_MAX_WAIT = 600  # 10 minutes
SUPPORTED_FORMATS = {"wav", "mp3", "m4a", "flac", "aac"}
MAX_FILE_SIZE = 1 * 1024 * 1024 * 1024  # 1GB


class VitoService:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self._token: str | None = None
        self._token_expires: float = 0

    async def _ensure_token(self) -> ServiceResult:
        """Issue/cache/refresh JWT token."""
        if time.time() < self._token_expires:
            return ServiceResult(success=True)

        if not config.VITO_CLIENT_ID or not config.VITO_CLIENT_SECRET:
            return ServiceResult(
                success=False,
                error_code="VITO_NOT_CONFIGURED",
                error_message="VITO_CLIENT_ID and VITO_CLIENT_SECRET are required for audio transcription. Set them in .env file.",
            )

        try:
            resp = await self.client.post(
                "https://openapi.vito.ai/v1/authenticate",
                data={
                    "client_id": config.VITO_CLIENT_ID,
                    "client_secret": config.VITO_CLIENT_SECRET,
                },
            )
            if resp.status_code != 200:
                return ServiceResult(
                    success=False,
                    error_code="AUTH_FAILED",
                    error_message=f"VITO authentication failed: {resp.status_code} {resp.text}",
                )
            data = resp.json()
            self._token = data["access_token"]
            self._token_expires = time.time() + data.get("expire_at", 3600) - 60
            return ServiceResult(success=True)
        except Exception as e:
            return ServiceResult(
                success=False,
                error_code="AUTH_ERROR",
                error_message=f"VITO authentication error: {e}",
            )

    def _validate_file(self, audio_path: str) -> ServiceResult | None:
        """Validate audio file exists, format, and size."""
        path = Path(audio_path)
        if not path.exists():
            return ServiceResult(
                success=False,
                error_code="FILE_NOT_FOUND",
                error_message=f"Audio file not found: {audio_path}",
            )
        ext = path.suffix.lstrip(".").lower()
        if ext not in SUPPORTED_FORMATS:
            return ServiceResult(
                success=False,
                error_code="UNSUPPORTED_FORMAT",
                error_message=f"Unsupported format: .{ext}. Supported: {', '.join(SUPPORTED_FORMATS)}",
            )
        if path.stat().st_size > MAX_FILE_SIZE:
            return ServiceResult(
                success=False,
                error_code="FILE_TOO_LARGE",
                error_message=f"File exceeds 1GB limit: {path.stat().st_size / (1024**3):.1f}GB",
            )
        return None

    async def transcribe(self, audio_path: str) -> ServiceResult:
        """Transcribe audio file via VITO API."""
        # Validate file
        validation_error = self._validate_file(audio_path)
        if validation_error:
            return validation_error

        # Ensure token
        token_result = await self._ensure_token()
        if not token_result.success:
            return token_result

        headers = {"Authorization": f"Bearer {self._token}"}

        try:
            # Upload file
            path = Path(audio_path)
            with open(path, "rb") as f:
                resp = await self.client.post(
                    "https://openapi.vito.ai/v1/transcribe",
                    headers=headers,
                    files={"file": (path.name, f)},
                    data={"config": '{"use_diarization": true}'},
                    timeout=120.0,
                )

            if resp.status_code != 200:
                return ServiceResult(
                    success=False,
                    error_code="UPLOAD_FAILED",
                    error_message=f"VITO upload failed: {resp.status_code} {resp.text}",
                    recoverable=resp.status_code in {429, 500, 502, 503},
                )

            transcribe_id = resp.json()["id"]
            logger.info("Transcription started: %s", transcribe_id)

            # Poll for completion
            elapsed = 0
            while elapsed < VITO_MAX_WAIT:
                await asyncio.sleep(VITO_POLL_INTERVAL)
                elapsed += VITO_POLL_INTERVAL

                status_resp = await self.client.get(
                    f"https://openapi.vito.ai/v1/transcribe/{transcribe_id}",
                    headers=headers,
                )

                if status_resp.status_code != 200:
                    continue

                status_data = status_resp.json()
                status = status_data.get("status")

                if status == "completed":
                    results = status_data.get("results", {})
                    utterances = results.get("utterances", [])
                    text = "\n".join(
                        f"[Speaker {u.get('spk', '?')}] {u.get('msg', '')}"
                        for u in utterances
                    )
                    duration = results.get("duration", 0.0)

                    transcript = TranscriptResult(
                        text=text,
                        duration=duration,
                        language=results.get("language", "ko"),
                        segments=[
                            {
                                "speaker": u.get("spk"),
                                "start": u.get("start_at"),
                                "end": u.get("end_at"),
                                "text": u.get("msg"),
                            }
                            for u in utterances
                        ],
                    )
                    return ServiceResult(
                        success=True,
                        data={
                            "text": transcript.text,
                            "duration": transcript.duration,
                            "language": transcript.language,
                            "segments": transcript.segments,
                        },
                    )
                elif status == "failed":
                    return ServiceResult(
                        success=False,
                        error_code="STT_FAILED",
                        error_message=f"VITO transcription failed: {status_data.get('message', 'unknown error')}",
                    )

            return ServiceResult(
                success=False,
                error_code="STT_TIMEOUT",
                error_message=f"Transcription timed out after {VITO_MAX_WAIT}s. Try again later or use text input.",
            )

        except Exception as e:
            return ServiceResult(
                success=False,
                error_code="STT_ERROR",
                error_message=f"Transcription error: {e}",
            )

    async def check_connection(self) -> ServiceResult:
        """Check if VITO API is configured and accessible."""
        if not config.VITO_CLIENT_ID or not config.VITO_CLIENT_SECRET:
            return ServiceResult(
                success=True,
                data={"status": "not_configured", "message": "VITO API keys not set. Text input only."},
            )
        token_result = await self._ensure_token()
        if token_result.success:
            return ServiceResult(
                success=True,
                data={"status": "connected", "message": "VITO API is accessible."},
            )
        return token_result

    async def close(self):
        """Close httpx connection pool."""
        await self.client.aclose()
