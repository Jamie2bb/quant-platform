"""
测试回测功能
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backtest.engine import BacktestEngine
from strategy.ma_cross import MACrossStrategy

print("=" * 60)
print("量化回测测试")
print("=" * 60)

# 创建回测引擎
engine = BacktestEngine(
    symbol="000001",          # 平安银行
    start_date="20240101",    # 开始日期
    end_date="20240901",      # 结束日期
    initial_capital=100000    # 初始资金10万
)

# 设置策略：5日均线与20日均线交叉
strategy = MACrossStrategy(short_period=5, long_period=20)
engine.set_strategy(strategy)

# 运行回测
print("\n运行回测中...")
result = engine.run()

# 输出结果摘要
result.summary()

# 查看交易明细
trades_df = result.get_trades_df()
if not trades_df.empty:
    print("\n【交易明细】")
    print(trades_df.to_string(index=False))
else:
    print("\n无交易记录")

print("\n回测完成！")

# 保存图表
print("\n正在生成图表...")
result.plot(save_path="backtest_result.png")
print("图表已保存到 backtest_result.png")
