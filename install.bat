@echo off
chcp 65001 > nul
echo ========================================
echo 회의록 자동화 MCP 서버 설치
echo ========================================
echo.

:: Python 확인
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python이 설치되어 있지 않습니다.
    echo https://www.python.org/downloads/ 에서 Python 3.10 이상을 설치하세요.
    pause
    exit /b 1
)

echo ✅ Python 확인 완료
echo.

:: 의존성 설치
echo 📦 필요한 패키지 설치 중...
pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ 패키지 설치 실패
    pause
    exit /b 1
)

echo ✅ 패키지 설치 완료
echo.

:: 현재 경로 저장
set "CURRENT_PATH=%CD%\server.py"

echo ========================================
echo ✅ 설치 완료!
echo ========================================
echo.
echo 🔧 다음 단계를 진행하세요:
echo.
echo 1️⃣  Claude Desktop 설정 파일을 여세요:
echo    %APPDATA%\Claude\claude_desktop_config.json
echo.
echo 2️⃣  아래 내용을 추가하세요:
echo.
echo {
echo   "mcpServers": {
echo     "meeting-automation": {
echo       "command": "python",
echo       "args": ["%CURRENT_PATH%"]
echo     }
echo   }
echo }
echo.
echo 💡 이미 다른 MCP 서버가 있다면:
echo    mcpServers 안에 "meeting-automation" 항목만 추가하세요!
echo.
echo 3️⃣  Claude Desktop을 완전히 종료 후 다시 시작
echo.
echo 4️⃣  Claude Desktop → 설정 → 개발자 도구에서 확인
echo    "meeting-automation" 서버가 보이면 성공!
echo.
echo ========================================
pause
