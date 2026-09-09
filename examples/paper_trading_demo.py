"""
模拟交易示例
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from simulator.paper_trading import PaperTrader


def main():
    print("=" * 60)
    print("模拟交易示例")
    print("=" * 60)
    
    # 创建模拟交易器（100万初始资金）
    trader = PaperTrader(initial_cash=1000000)
    
    # 查看初始账户
    print("\n【初始账户】")
    trader.summary()
    
    # 买入股票
    print("\n【买入操作】")
    
    # 买入平安银行 1000股
    order1 = trader.buy("000001", 1000, note="测试买入")
    print(f"订单1: {order1.order_id} - {order1.status}")
    
    # 买入贵州茅台 100股
    order2 = trader.buy("600519", 100, note="买入茅台")
    print(f"订单2: {order2.order_id} - {order2.status}")
    
    # 买入招商银行 500股
    order3 = trader.buy("600036", 500, note="买入招行")
    print(f"订单3: {order3.order_id} - {order3.status}")
    
    # 查看当前持仓
    print("\n【当前持仓】")
    trader.summary()
    
    # 卖出部分持仓
    print("\n【卖出操作】")
    order4 = trader.sell("000001", 500, note="减仓")
    print(f"订单4: {order4.order_id} - {order4.status}")
    
    # 查看最终账户
    print("\n【最终账户】")
    trader.summary()
    
    # 查看交易记录
    trades = trader.get_trade_history()
    if not trades.empty:
        print("\n【交易记录】")
        print(trades.to_string(index=False))
    
    print("\n" + "=" * 60)
    print("提示：")
    print("- 模拟交易状态会自动保存到 simulator/data/ 目录")
    print("- 下次运行时会自动恢复上次的持仓")
    print("- 调用 trader.reset() 可重置账户")
    print("=" * 60)


if __name__ == "__main__":
    main()
