# -*- coding: utf-8 -*-
"""
我的持仓分析主程序
一站式分析你的持仓股票
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .config import load_holdings, save_holdings, PositionRules
from .analyzer import analyze_stock, print_analysis
from .monitor import PortfolioMonitor, run_monitor
from .position_calc import calc_position, calc_position_by_pct
from .backtest_idea import test_idea, compare_strategies, test_ma_params


def analyze_my_holdings():
    """分析我的所有持仓"""
    holdings = load_holdings()
    
    if not holdings:
        print("持仓列表为空，请先在 持仓配置.json 中添加持仓")
        return
    
    print(f"\n正在分析 {len(holdings)} 只持仓股票...\n")
    
    results = []
    for h in holdings:
        try:
            result = analyze_stock(h["code"], h.get("name", ""))
            results.append(result)
            print_analysis(result)
        except Exception as e:
            print(f"分析 {h['code']} 失败: {e}")
    
    # 汇总
    if results:
        print(f"\n{'='*60}")
        print("【持仓综合评分】")
        print(f"{'='*60}")
        
        for r in sorted(results, key=lambda x: x.score, reverse=True):
            score_bar = "█" * max(0, (r.score + 100) // 20) + "░" * (10 - max(0, (r.score + 100) // 20))
            print(f"  {r.symbol} {r.name:<8} [{score_bar}] {r.score:+3d}分 - {r.suggestion}")


def monitor_my_holdings():
    """监控我的持仓（检查止损止盈、技术信号）"""
    return run_monitor()


def add_holding(code: str, name: str, market: str = "0"):
    """
    添加持仓
    
    Args:
        code: 股票代码
        name: 股票名称
        market: 市场 0=深市 1=沪市
    """
    holdings = load_holdings()
    
    # 检查是否已存在
    if any(h["code"] == code for h in holdings):
        print(f"{code} 已在持仓列表中")
        return
    
    holdings.append({"code": code, "name": name, "market": market})
    save_holdings(holdings)
    print(f"已添加: {code} {name}")


def remove_holding(code: str):
    """移除持仓"""
    holdings = load_holdings()
    holdings = [h for h in holdings if h["code"] != code]
    save_holdings(holdings)
    print(f"已移除: {code}")


def set_cost(code: str, cost_price: float):
    """设置买入成本价"""
    monitor = PortfolioMonitor()
    monitor.set_cost_price(code, cost_price)


def backtest_holding(code: str, name: str = ""):
    """回测持仓股票的多种策略"""
    return test_idea(code, name)


def optimize_ma(code: str, name: str = ""):
    """优化均线参数"""
    return test_ma_params(code, name=name)


def calc_buy_position(price: float, stop_loss: float, capital: float = None):
    """
    计算买入仓位
    
    Args:
        price: 计划买入价
        stop_loss: 止损价
        capital: 总资金（可选，默认使用配置）
    """
    return calc_position(price, stop_loss, capital)


def print_menu():
    """打印菜单"""
    print(f"""
{'='*60}
        我的持仓量化分析系统
{'='*60}

【分析功能】
  1. analyze_my_holdings()     - 分析所有持仓股票
  2. monitor_my_holdings()     - 监控止损止盈信号
  3. analyze_stock(code,name)  - 分析单只股票

【持仓管理】
  4. add_holding(code,name)    - 添加持仓
  5. remove_holding(code)      - 移除持仓
  6. set_cost(code,price)      - 设置成本价

【回测验证】
  7. backtest_holding(code)    - 测试多种策略
  8. optimize_ma(code)         - 优化均线参数

【仓位计算】
  9. calc_buy_position(price,stop) - 计算建仓数量

【示例】
  analyze_stock("600519", "贵州茅台")
  set_cost("301005", 25.5)
  calc_buy_position(25.0, 23.0)
  backtest_holding("600519", "贵州茅台")

{'='*60}
""")


# 启动时显示菜单
if __name__ == "__main__":
    print_menu()
    
    # 默认执行分析
    print("\n自动执行持仓监控...\n")
    monitor_my_holdings()
