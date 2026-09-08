"""
策略对比示例
比较不同策略在同一只股票上的表现
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest.engine import BacktestEngine
from strategy.ma_cross import MACrossStrategy, TripleMAStrategy
from strategy.momentum import MomentumStrategy, RSIMomentumStrategy
from strategy.breakout import BreakoutStrategy, BollingerBreakoutStrategy


def compare_strategies(symbol: str, start_date: str, end_date: str):
    """比较多个策略"""
    
    strategies = [
        MACrossStrategy(5, 20),
        MACrossStrategy(10, 30),
        TripleMAStrategy(5, 10, 20),
        RSIMomentumStrategy(14, 30, 70),
        BreakoutStrategy(20, 10),
        BollingerBreakoutStrategy(20, 2.0),
    ]
    
    results = []
    
    for strategy in strategies:
        engine = BacktestEngine(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            initial_capital=100000
        )
        engine.set_strategy(strategy)
        result = engine.run()
        results.append(result)
    
    # 输出对比表格
    print("\n" + "="*80)
    print(f"策略对比: {symbol} ({start_date} ~ {end_date})")
    print("="*80)
    print(f"{'策略名称':<25} {'总收益率':>10} {'年化收益':>10} {'最大回撤':>10} {'夏普比率':>10} {'交易次数':>8}")
    print("-"*80)
    
    for result in results:
        print(f"{result.strategy_name:<25} "
              f"{result.total_return:>9.2%} "
              f"{result.annual_return:>9.2%} "
              f"{result.max_drawdown:>9.2%} "
              f"{result.sharpe_ratio:>10.2f} "
              f"{result.total_trades:>8d}")
    
    print("="*80)
    
    # 找出最佳策略
    best_by_return = max(results, key=lambda x: x.total_return)
    best_by_sharpe = max(results, key=lambda x: x.sharpe_ratio)
    
    print(f"\n收益率最高: {best_by_return.strategy_name} ({best_by_return.total_return:.2%})")
    print(f"夏普最高:   {best_by_sharpe.strategy_name} ({best_by_sharpe.sharpe_ratio:.2f})")
    
    return results


def main():
    # 测试股票
    symbol = "600519"  # 贵州茅台
    
    # 回测时间段
    start_date = "20230101"
    end_date = "20231231"
    
    results = compare_strategies(symbol, start_date, end_date)
    
    # 绘制最佳策略的图表
    best = max(results, key=lambda x: x.sharpe_ratio)
    print(f"\n绘制最佳策略 ({best.strategy_name}) 的回测图表...")
    best.plot()


if __name__ == "__main__":
    main()
