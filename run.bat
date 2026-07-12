@echo off
setlocal EnableExtensions

cd /d "%~dp0"

if not exist "pyproject.toml" (
    echo [error] 请在 MomaPipeline 项目根目录运行 .\run.bat 或 .\run.ps1
    exit /b 1
)

where python >nul 2>&1
if errorlevel 1 (
    echo [error] 未找到 python，请先安装 Python 3.10+
    exit /b 1
)

where npm >nul 2>&1
if errorlevel 1 (
    echo [error] 未找到 npm，请先安装 Node.js
    exit /b 1
)

if not defined SERVICE_PORT set SERVICE_PORT=8100
if not defined WEB_PORT set WEB_PORT=5174

if not exist ".venv\Scripts\python.exe" (
    echo [setup] 创建虚拟环境并安装依赖...
    python -m venv .venv
    if errorlevel 1 exit /b 1
    call .venv\Scripts\activate.bat
    python -m pip install -U pip -q
    pip install -e .
    if errorlevel 1 exit /b 1
)

if not exist ".env" (
    echo [setup] 创建 .env ...
    copy /Y env.example .env >nul
)

if not exist "data\models\chat_models.json" (
    if exist "..\Pando-Harness\data\models\chat_models.json" (
        echo [setup] 从 Pando-Harness 复制 chat_models.json ...
        copy /Y "..\Pando-Harness\data\models\chat_models.json" "data\models\chat_models.json" >nul
    ) else if exist "data\models\chat_models.json.example" (
        echo [setup] 创建 chat_models.json ...
        copy /Y "data\models\chat_models.json.example" "data\models\chat_models.json" >nul
    )
)

if not exist "web\.env" (
    if exist "web\env.example" (
        echo [setup] 创建 web\.env ...
        copy /Y web\env.example web\.env >nul
    )
)

if not exist "web\node_modules" (
    echo [setup] 安装前端依赖...
    pushd web
    call npm install
    if errorlevel 1 (
        popd
        exit /b 1
    )
    popd
)

echo.
echo [run] 启动后端 API  http://localhost:%SERVICE_PORT%
start "MomaPipeline API" cmd /k "cd /d %CD% && call .venv\Scripts\activate.bat && set SERVICE_PORT=%SERVICE_PORT% && python start.py"

echo [run] 启动编排 UI  http://localhost:%WEB_PORT%
start "MomaPipeline Web" cmd /k "cd /d %CD%\web && npm run dev -- --port %WEB_PORT% --host"

timeout /t 2 /nobreak >nul
start "" "http://localhost:%WEB_PORT%"

echo.
echo 前后端已在独立窗口中运行，关闭对应窗口或按 Ctrl+C 即可停止。
echo   API:  http://localhost:%SERVICE_PORT%/health
echo   UI:   http://localhost:%WEB_PORT%
echo.

endlocal
