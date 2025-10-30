# Meeting Automation MCP Server

Fireflies, Asana, Notion MCP 서버들을 연결하는 회의 자동화 오케스트레이터

## 🎯 핵심 개념

이 MCP 서버는 **직접 API를 호출하지 않고**, 기존의 Fireflies, Asana, Notion MCP 서버들을 **중앙에서 조율**하는 역할을 합니다.

```
Claude Desktop
    ↓
Meeting Automation MCP (오케스트레이터)
    ↓
┌─────────────┬─────────────┬─────────────┐
│ Fireflies   │   Asana     │   Notion    │
│ MCP Server  │ MCP Server  │ MCP Server  │
└─────────────┴─────────────┴─────────────┘
```

## 📦 사전 요구사항

### 필수 MCP 서버 설치
이 서버가 작동하려면 다음 MCP 서버들이 먼저 설치되어 있어야 합니다:

1. **Fireflies MCP Server** - 회의 전사 및 검색 ✅ (Claude Desktop에서 연결)
2. **Asana MCP Server** - 태스크 관리 ✅ (Claude Desktop에서 연결)
3. **Notion MCP Server** - 문서화 ✅ (Claude Desktop에서 연결)

> 💡 Claude Desktop의 MCP 설정에서 위 3개 서버가 파란색으로 활성화되어 있는지 확인하세요.

### Python 환경
- Python 3.10 이상

## 🚀 설치 방법

### 0. 기존 MCP 서버 확인 (필수!)

Claude Desktop을 열고 MCP 설정에서 다음이 활성화되어 있는지 확인:
- ✅ Fireflies (파란색)
- ✅ Asana (파란색)
- ✅ Notion (파란색)

### 1. 저장소 클론 또는 다운로드
```bash
git clone https://github.com/Ramhori/meeting-automation-mcp.git
cd meeting-automation-mcp
```

또는 ZIP 파일 다운로드 후 압축 해제

### 2. 의존성 설치
```bash
pip install -r requirements.txt
```

### 3. Claude Desktop 설정

`claude_desktop_config.json` 파일에 **meeting-automation-mcp만** 추가:

**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`  
**Mac**: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "meeting-automation-mcp": {
      "command": "python",
      "args": ["C:\\다운로드경로\\meeting-automation-mcp\\server.py"]
    }
    // Fireflies, Asana, Notion MCP는 이미 Claude Desktop에서 활성화되어 있다고 가정
  }
}
```

> ⚠️ **중요**: 경로는 반드시 절대경로로 지정하세요.  
> 예: `C:\\Users\\사용자명\\Downloads\\meeting-automation-mcp\\server.py`

### 4. Claude Desktop 재시작

## 💡 사용 방법

### 빠른 시작 명령어

Claude에게 이렇게 요청하세요:

```
📋 회의 검색:
"10/24 회의 찾아줘"

📊 액션아이템 확인:
"이 회의 액션아이템 보여줘"

✅ 태스크 생성:
"액션아이템을 [프로젝트명]에 태스크로 만들어"

📝 문서화:
"[데이터베이스명]에 회의록 저장해줘"

🚀 전체 자동화:
"10/24 회의 완전 자동화해줘"
```

## 🛠️ 제공 도구

### Fireflies 도구들

#### `Fireflies:search`
회의 검색 (날짜, 키워드 기반)

**문법:**
```
- keyword:"검색어" - 키워드 검색
- from:YYYY-MM-DD - 시작 날짜
- to:YYYY-MM-DD - 종료 날짜
- limit:N - 결과 제한
- scope:title|sentences|all - 검색 범위
```

**예시:**
```python
query="from:2024-10-24 to:2024-10-24"
query='keyword:"프로젝트" scope:sentences'
```

#### `Fireflies:get_summary`
회의 요약, 액션아이템, 키워드 가져오기

**파라미터:**
- `transcriptId`: 회의 ID

#### `Fireflies:get_transcript`
전체 대화 내용 가져오기

**파라미터:**
- `transcriptId`: 회의 ID

### Asana 도구들

#### `Asana:asana_typeahead_search`
프로젝트, 사용자, 태그 등 검색

**파라미터:**
- `resource_type`: "project" | "user" | "task" | "team"
- `workspace_gid`: 워크스페이스 ID
- `query`: 검색어

#### `Asana:asana_create_task`
태스크 생성

**파라미터:**
- `name`: 태스크 이름 (필수)
- `notes`: 태스크 설명
- `project_id`: 프로젝트 ID
- `assignee`: 담당자
- `due_on`: 마감일 (YYYY-MM-DD)

#### `Asana:asana_list_workspaces`
접근 가능한 워크스페이스 목록 조회

### Notion 도구들

#### `Notion:notion-search`
Notion 워크스페이스 검색

**파라미터:**
- `query`: 검색어
- `query_type`: "internal" (기본값)

#### `Notion:notion-create-pages`
페이지 생성

**파라미터:**
- `parent`: 상위 페이지/데이터베이스
- `pages`: 페이지 배열
  - `properties`: 페이지 속성
  - `content`: Notion Markdown 형식 내용

## 📚 가이드 리소스

서버에 내장된 6가지 가이드:

1. **회의 검색 가이드** (`guide://meeting_search`)
2. **회의 상세정보 가이드** (`guide://meeting_details`)
3. **Asana 태스크 생성 가이드** (`guide://create_asana_tasks`)
4. **Notion 저장 가이드** (`guide://save_to_notion`)
5. **전체 워크플로우 가이드** (`guide://full_workflow`)
6. **빠른 실행 명령어** (`guide://quick_commands`)

## 🔄 전체 자동화 워크플로우

```
단계 1: 회의 검색
  ↓ Fireflies:search
단계 2: 회의 내용 가져오기
  ↓ Fireflies:get_summary
단계 3: Asana 태스크 생성
  ↓ Asana:asana_typeahead_search (프로젝트 찾기)
  ↓ Asana:asana_create_task (액션아이템마다)
단계 4: Notion 문서화
  ↓ Notion:notion-search (데이터베이스 찾기)
  ↓ Notion:notion-create-pages (회의록 작성)
단계 5: 결과 보고
```

## 🎓 사용 예시

### 예시 1: 특정 날짜 회의 찾기
```
사용자: "10/24 회의 찾아줘"

Claude가 실행:
1. Fireflies:search query="from:2024-10-24 to:2024-10-24"
2. 검색 결과 표시
```

### 예시 2: 액션아이템을 Asana에 등록
```
사용자: "이 회의 액션아이템을 '프로젝트 관리' 프로젝트에 태스크로 만들어"

Claude가 실행:
1. Fireflies:get_summary (액션아이템 추출)
2. Asana:asana_typeahead_search (프로젝트 찾기)
3. Asana:asana_create_task (각 액션아이템마다)
```

### 예시 3: 완전 자동화
```
사용자: "10/24 회의 완전 자동화해줘"

Claude가 실행:
1. 회의 검색
2. 요약 가져오기
3. Asana 태스크 생성
4. Notion 문서 저장
5. 결과 리포트 제공
```

## 🔧 문제 해결

### MCP 서버가 인식되지 않을 때
```bash
1. Claude Desktop 완전 종료 (작업 관리자에서 확인)
2. claude_desktop_config.json 경로 확인
3. Python 경로가 절대경로인지 확인
4. Claude Desktop 재시작
```

### Fireflies/Asana/Notion 도구가 작동하지 않을 때
```
→ 해당 MCP 서버들이 먼저 설치되어 있는지 확인
→ 각 서버의 API 키가 올바른지 확인
```

### 도구 목록이 보이지 않을 때
```bash
# Claude Desktop 로그 확인
Windows: %APPDATA%\Claude\logs
Mac: ~/Library/Logs/Claude
```

## 📊 성과

**전통적 방식:**
- 회의 후 후속작업 실행률: ~60%
- 소요 시간: 회의당 15-30분

**자동화 후:**
- 회의 후 후속작업 실행률: ~95%
- 소요 시간: 회의당 2-3분

## 🤝 기여

이슈와 PR 환영합니다!

## 📝 라이센스

MIT License

## 👤 제작자

OK금융그룹 IT기획팀 김정호
- 역할: 업무 담당자 (개발자 아님)
- 프로젝트: 차세대 은행 시스템 개발 참여
- 전문 분야: AI 활용 및 업무 자동화

---

**⭐ 이 프로젝트가 도움이 되었다면 Star를 눌러주세요!**
