@echo off
chcp 65001 >nul
echo ========================================
echo 設置 Windows 定時任務 (Email版)
echo ========================================
echo.

REM 獲取當前目錄
set CURRENT_DIR=%~dp0
set RUN_SCRIPT=%CURRENT_DIR%run.bat

echo 任務配置:
echo - 任務名稱: MacauNewsMonitorEmail
echo - 運行時間: 每天 09:00
echo - 腳本路徑: %RUN_SCRIPT%
echo.

REM 檢查run.bat是否存在
if not exist "%RUN_SCRIPT%" (
    echo [錯誤] 找不到 run.bat
    pause
    exit /b 1
)

echo 正在建立定時任務...
echo.

REM 刪除已存在的同名任務（如果有）
schtasks /query /tn "MacauNewsMonitorEmail" >nul 2>&1
if not errorlevel 1 (
    echo 偵測到已存在的任務，正在刪除...
    schtasks /delete /tn "MacauNewsMonitorEmail" /f
)

REM 建立新的定時任務
schtasks /create /tn "MacauNewsMonitorEmail" /tr "\"%RUN_SCRIPT%\"" /sc daily /st 09:00 /f

if errorlevel 1 (
    echo.
    echo [錯誤] 建立定時任務失敗
    echo 請確保以管理員權限運行此腳本
    pause
    exit /b 1
)

echo.
echo ========================================
echo 定時任務建立成功！
echo ========================================
echo.
echo 任務詳情:
schtasks /query /tn "MacauNewsMonitorEmail" /fo list /v
echo.
echo 提示:
echo - 可以在「任務計畫程式」中查看和管理此任務
echo - 運行 Win+R，輸入 taskschd.msc 開啟任務計畫程式
echo - 如需修改時間，請編輯此腳本中的 /st 09:00 參數
echo.
pause
