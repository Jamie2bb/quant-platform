@echo off
chcp 65001 >nul
echo ==========================================
echo   启动量化平台 Web 界面
echo ==========================================
echo.

REM 检查 streamlit
pip show streamlit >nul 2>&1
if errorlevel 1 (
    echo 正在安装 streamlit...
    pip install streamlit
)

echo 启动 Web 服务...
echo 浏览器将自动打开 http://localhost:8501
echo.
streamlit run web/app.py

pause
