@echo off
chcp 65001 >nul
echo ==========================================
echo   A股量化回测平台 - 快速演示
echo ==========================================
echo.

REM 检查依赖
echo [1/3] 检查依赖...
pip show akshare >nul 2>&1
if errorlevel 1 (
    echo 正在安装依赖...
    pip install akshare pandas numpy matplotlib
)

echo [2/3] 运行数据获取示例...
python -m examples.realtime_demo

echo.
echo [3/3] 运行回测示例...
python -m examples.quick_start

echo.
echo ==========================================
echo   演示完成！
echo ==========================================
pause
