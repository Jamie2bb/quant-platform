@echo off
chcp 65001 >nul
echo ==========================================
echo   安装量化回测平台依赖
echo ==========================================
echo.

pip install -r requirements.txt

echo.
echo 安装完成！
echo 运行 run_demo.bat 开始演示
pause
