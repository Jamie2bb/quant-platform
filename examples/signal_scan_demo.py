"""
策略信号扫描示例
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from monitor.signal_alert import SignalAlert, scan_market_signals
from strategy.macd import MACDStrategy
from strategy.kdj import KDJStrategy
from strategy.ma_cross import MACrossStrategy


def main():
    print("=" * 60)
    print("策略信号扫描")
    print("=" * 60)
    
    # 监控的股票列表
    watchlist = [
        "000001",  # 平安银行
        "000002",  # 万科A
        "000651",  # 格力电器
        "000858",  # 五粮液
        "600519",  # 贵州茅台
        "600036",  # 招商银行
        "601318",  # 中国平安
        "002415",  # 海康威视
        "300750",  # 宁德时代
    ]
    
    # 使用 MACD 策略扫描
    print("\n【MACD 策略信号】")
    macd_alert = SignalAlert(MACDStrategy())
    macd_alert.add_stocks(watchlist)
    macd_alert.report()
    
    # 使用均线策略扫描
    print("\n【均线交叉策略信号】")
    ma_alert = SignalAlert(MACrossStrategy(5, 20))
    ma_alert.add_stocks(watchlist)
    ma_alert.report()
    
    # 全市场扫描（扫描更多股票）
    print("\n【全市场 MACD 金叉扫描】")
    results = scan_market_signals(MACDStrategy(), max_stocks=50)
    
    if results["buy"]:
        print(f"买入信号 ({len(results['buy'])} 只):")
        for item in results["buy"][:10]:
            print(f"  {item['symbol']} 价格:{item['price']:.2f}")
    else:
        print("无买入信号")


if __name__ == "__main__":
    main()
