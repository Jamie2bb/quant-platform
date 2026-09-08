"""
快速入门示例
运行: python -m examples.quick_start
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest.engine import BacktestEngine
from strategy.ma_cross import MACrossStrategy


def main():
    # 创建回测引擎
    engine = BacktestEngine(
        symbol="000001",          # 平安银行
        start_date="20230101",    # 开始日期
        end_date="20231231",      # 结束日期
        initial_capital=100000    # 初始资金10万
    )
    
    # 设置策略：5日均线与20日均线交叉
    strategy = MACrossStrategy(short_period=5, long_period=20)
    engine.set_strategy(strategy)
    
    # 运行回测
    result = engine.run()
    
    # 输出结果摘要
    result.summary()
    
    # 查看交易明细
    trades_df = result.get_trades_df()
    if not trades_df.empty:
        print("\n【交易明细】")
        print(trades_df.to_string(index=False))
    
    # 绘制图表
    result.plot()


if __name__ == "__main__":
    main()
