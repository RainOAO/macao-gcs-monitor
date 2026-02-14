@echo off
chcp 65001 >nul

REM 切換到腳本所在目錄
cd /d "%~dp0"

REM 檢查虛擬環境是否存在
if not exist "venv\Scripts\activate.bat" (
    echo [錯誤] 虛擬環境不存在，請先運行 setup_env.bat
    pause
    exit /b 1
)

REM 激活虛擬環境
call venv\Scripts\activate.bat

REM 運行 Email 版監控程序，傳遞所有參數
python macau_news_monitor.py %*

REM 保存退出代碼
set EXIT_CODE=%ERRORLEVEL%

REM 停用虛擬環境
call venv\Scripts\deactivate.bat

REM 返回原始退出代碼
exit /b %EXIT_CODE%
