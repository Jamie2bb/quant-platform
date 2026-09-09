@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo ========================================
echo    我的持仓量化分析系统
echo ========================================
echo.

python run_my_portfolio.py

pause
