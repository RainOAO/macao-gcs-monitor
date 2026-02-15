@echo off
chcp 65001 >nul
echo ========================================
echo 澳門新聞監控系統 - 環境設置
echo ========================================
echo.

REM 檢查Python是否安裝
python --version >nul 2>&1
if errorlevel 1 (
    echo [錯誤] 未檢測到 Python，請先安裝 Python 3.8 或更高版本
    echo 下載地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/4] 檢測到 Python:
python --version
echo.

REM 檢查虛擬環境是否已存在
if exist "venv\" (
    echo [警告] 虛擬環境已存在
    set /p RECREATE="是否重新創建？(Y/N): "
    if /i "%RECREATE%"=="Y" (
        echo [2/4] 刪除舊的虛擬環境...
        rmdir /s /q venv
    ) else (
        echo 保留現有虛擬環境
        goto :install_deps
    )
)

echo [2/4] 創建虛擬環境...
python -m venv venv
if errorlevel 1 (
    echo [錯誤] 創建虛擬環境失敗
    pause
    exit /b 1
)
echo 虛擬環境創建成功
echo.

:install_deps
echo [3/4] 激活虛擬環境並安裝依賴包...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [錯誤] 激活虛擬環境失敗
    pause
    exit /b 1
)

echo 正在安裝依賴包...
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo [錯誤] 安裝依賴包失敗
    pause
    exit /b 1
)
echo.

echo [4/4] 驗證安裝...
pip list
echo.

echo ========================================
echo 環境設置完成！
echo ========================================
echo.
echo 下一步:
echo 1. 編輯 config.json，配置email
echo 2. 運行 run.bat --test 進行測試
echo 3. 運行 setup_task.bat 設置定時任務
echo.
pause
