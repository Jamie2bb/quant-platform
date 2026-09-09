# -*- coding: utf-8 -*-
"""
一键运行：我的持仓分析
双击此文件或在命令行运行 python run_my_portfolio.py
"""
import sys
import os

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from my_portfolio.main import (
    analyze_my_holdings,
    monitor_my_holdings,
    analyze_stock,
    add_holding,
    remove_holding,
    set_cost,
    backtest_holding,
    optimize_ma,
    calc_buy_position,
    print_menu
)

if __name__ == "__main__":
    print_menu()
    
    print("\n" + "="*60)
    print("开始分析持仓...")
    print("="*60)
    
    # 1. 监控（检查止损止盈）
    print("\n【第一步：持仓监控】")
    monitor = monitor_my_holdings()
    
    # 2. 详细分析
    print("\n【第二步：技术分析】")
    analyze_my_holdings()
    
    print("\n\n分析完成！")
    print("如需更多操作，请在 Python 交互模式下导入 my_portfolio.main")
    input("\n按回车键退出...")
