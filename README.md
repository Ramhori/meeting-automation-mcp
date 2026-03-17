# Meeting Automation MCP Server

회의 녹음/텍스트 → STT 전사 → Asana 태스크 → Notion 회의록까지 자동 처리하는 **범용 MCP 서버**.

Claude, GPT, Gemini 등 어떤 LLM 클라이언트에서든 사용할 수 있습니다.

```
사용자: "회의 자동화해줘"
         ↓
  1. VITO API → 전사 (또는 텍스트 직접 입력)
  2. LLM → 요약 + 액션아이템 추출
  3. Asana API → 태스크 생성
  4. Notion API → 회의록 저장
         ↓
LLM: "완료! 태스크 N개, Notion 저장됨"
```

## 설치

```bash
git clone https://github.com/Ramhori/meeting-automation-mcp.git
cd meeting-automation-mcp
pip install -r requirements.txt
```

## 환경변수 설정

`.env.example`을 복사하여 `.env` 파일을 만들고 실제 값을 입력합니다.

```bash
cp .env.example .env
```

| 변수 | 필수 | 설명 |
|------|------|------|
| `VITO_CLIENT_ID` | 선택 | VITO STT API 클라이언트 ID (없으면 텍스트 입력만 가능) |
| `VITO_CLIENT_SECRET` | 선택 | VITO STT API 시크릿 |
| `ASANA_TOKEN` | 필수 | Asana Personal Access Token |
| `NOTION_TOKEN` | 필수 | Notion Internal Integration Token |
| `NOTION_DATABASE_ID` | 필수 | 회의록 저장할 Notion 데이터베이스 ID |
| `DEFAULT_AUTHOR` | 선택 | 기본 작성자 이름 |
| `LOG_LEVEL` | 선택 | 로그 레벨 (기본: INFO) |

## MCP 클라이언트 연동

### Claude Desktop

`claude_desktop_config.json`에 추가:

```json
{
  "mcpServers": {
    "meeting-automation": {
      "command": "python",
      "args": ["C:\\경로\\meeting-automation-mcp\\server.py"]
    }
  }
}
```

### Claude Code

`~/.claude/settings.json` 또는 프로젝트의 `.mcp.json`에 추가:

```json
{
  "mcpServers": {
    "meeting-automation": {
      "command": "python",
      "args": ["C:\\경로\\meeting-automation-mcp\\server.py"]
    }
  }
}
```

### Cursor

Settings → MCP Servers에서 동일한 command/args로 추가.

## 도구 목록 (11개)

### Setup

| 도구 | 설명 |
|------|------|
| `check_meeting_setup` | VITO/Asana/Notion 연결 상태 확인. 처음 사용 시 호출 |

### STT (전사)

| 도구 | 설명 |
|------|------|
| `process_meeting` | 오디오 파일(VITO) 또는 텍스트 입력 처리. 우선순위: text > text_file_path > audio_path |

### Asana (태스크 CRUD)

| 도구 | 설명 |
|------|------|
| `create_meeting_task` | 액션아이템 → Asana 태스크 생성 |
| `update_meeting_task` | 기존 태스크 수정 (이름, 담당자, 기한 등) |
| `get_meeting_tasks` | 프로젝트 내 태스크 목록 조회 |
| `delete_meeting_task` | 태스크 삭제 |

### Notion (회의록 CRUD)

| 도구 | 설명 |
|------|------|
| `save_meeting_notes` | 회의록 → Notion DB 저장 (13개 속성 자동 매핑) |
| `update_meeting_notes` | 기존 회의록 수정 |
| `get_meeting_notes` | 회의록 목록 조회 |
| `delete_meeting_notes` | 회의록 아카이브(삭제) |

### Pipeline (원샷)

| 도구 | 설명 |
|------|------|
| `run_full_pipeline` | 전사 → Asana → Notion 일괄 처리 (확인 없이 한번에) |

## 동작 모드

| 모드 | 사용 방식 | 대상 |
|------|----------|------|
| **단계별** | LLM이 도구를 개별 호출, 중간에 사용자 확인 | Claude, GPT-4 등 |
| **원샷** | `run_full_pipeline` 하나로 일괄 처리 | 자동화 스크립트 |

## 사용 예시

### 텍스트로 회의록 처리 (단계별)

```
1. process_meeting(text="회의 내용...") → 전사 텍스트 반환
2. LLM이 요약 + 액션아이템 추출 → 사용자에게 보여줌
3. 사용자 OK → create_meeting_task × N회
4. 사용자 OK → save_meeting_notes
```

### 오디오 파일 전사 (VITO 키 필요)

```
1. check_meeting_setup() → 연결 상태 확인
2. process_meeting(audio_path="회의녹음.m4a") → 전사
3. 이하 동일
```

### 원샷 파이프라인

```
run_full_pipeline(
    text="회의 내용...",
    project_id="12345",
    action_items_json='[{"name":"API 개발","assignee":"kim@co.kr","due_on":"2026-03-20"}]',
    meeting_title="3월 정기회의",
    meeting_date="2026-03-17"
)
```

## Notion DB 속성 매핑

| DB 속성 | 타입 | 도구 파라미터 |
|---------|------|--------------|
| 회의명 | title | `title` |
| 회의일시 | date | `date_str` |
| 회의장소 | text | `location` |
| 주관부서 | text | `host_dept` |
| 참석부서 | text | `attend_dept` |
| 참석자 | text | `attendees` |
| 회의안건 | text | `agenda` |
| 회의내용 | text | `summary` |
| 결정사항 | text | `decisions` |
| 기타 | text | `etc` |
| 작성일 | date | 자동 (오늘 날짜) |
| 작성자 | text | `author` (기본: DEFAULT_AUTHOR) |
| URL | url | `url` |

## 에러 코드

| 코드 | 설명 | 대응 |
|------|------|------|
| `VITO_NOT_CONFIGURED` | VITO API 키 미설정 | .env에 키 추가 또는 텍스트 입력 사용 |
| `AUTH_EXPIRED` | API 인증 토큰 만료 | .env에서 토큰 갱신 |
| `AUTH_FAILED` | 인증 실패 | API 키 확인 |
| `FILE_NOT_FOUND` | 파일 없음 | 파일 경로 확인 |
| `UNSUPPORTED_FORMAT` | 미지원 오디오 포맷 | wav, mp3, m4a, flac, aac만 지원 |
| `FILE_TOO_LARGE` | 파일 1GB 초과 | 파일 분할 |
| `STT_TIMEOUT` | 전사 10분 초과 | 재시도 또는 짧은 파일 사용 |
| `RATE_LIMIT` | API 요청 제한 초과 | 자동 재시도 (서버 처리) |
| `PERMISSION_DENIED` | 접근 권한 없음 | Notion Integration 설정 확인 |
| `NO_DATABASE_ID` | DB ID 미설정 | .env에 NOTION_DATABASE_ID 추가 |
| `NO_INPUT` | 입력값 없음 | text, text_file_path, audio_path 중 하나 제공 |

## 프로젝트 구조

```
meeting-automation-mcp/
├── server.py          ← FastMCP 엔트리포인트 (도구 등록 + lifespan)
├── config.py          ← 설정 관리 (.env 기반)
├── models.py          ← 공통 타입 (ServiceResult, TranscriptResult)
├── utils.py           ← 공유 유틸리티 (with_retry)
├── services/
│   ├── vito.py        ← VITO STT API (전사 + JWT 토큰 관리)
│   ├── asana.py       ← Asana REST API (태스크 CRUD)
│   └── notion.py      ← Notion API (회의록 CRUD)
├── .env.example       ← 환경변수 템플릿
├── requirements.txt
└── README.md
```

## 라이센스

MIT License

## 제작자

OK금융그룹 IT기획팀 김정호
