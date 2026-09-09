# -*- coding: utf-8 -*-
"""
回测验证 - 快速验证你的交易想法
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from datetime import datetime, timedelta
from typing import List, Tuple, Optional
from dataclasses import dataclass

from data.fetcher import DataFetcher
from backtest.engine import BacktestEngine
from backtest.result import BacktestResult
from strategy.base import BaseStrategy
from strategy.ma_cross import MACrossStrategy
from strategy.macd import MACDStrategy
from strategy.kdj import KDJStrategy


@dataclass
class QuickBacktestResult:
    """快速回测结果"""
    symbol: str
    name: str
    strategy_name: str
    start_date: str
    end_date: str
    
    # 收益指标
    total_return: float      # 总收益率
    annual_return: float     # 年化收益率
    max_drawdown: float      # 最大回撤
    sharpe_ratio: float      # 夏普比率
    
    # 交易统计
    trade_count: int         # 交易次数
    win_rate: float          # 胜率
    avg_profit: float        # 平均盈利
    avg_loss: float          # 平均亏损
    profit_factor: float     # 盈亏比
    
    # 对比
    buy_hold_return: float   # 买入持有收益率
    excess_return: float     # 超额收益


def quick_backtest(symbol: str, 
                   strategy: BaseStrategy,
                   start_date: str = None,
                   end_date: str = None,
                   initial_capital: float = 100000,
                   name: str = "") -> QuickBacktestResult:
    """
    快速回测
    
    Args:
        symbol: 股票代码
        strategy: 策略实例
        start_date: 开始日期，默认一年前
        end_date: 结束日期，默认今天
        initial_capital: 初始资金
        name: 股票名称
    
    Returns:
        QuickBacktestResult: 回测结果
    """
    if start_date is None:
        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
    if end_date is None:
        end_date = datetime.now().strftime("%Y%m%d")
    
    # 运行回测
    engine = BacktestEngine(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        initial_capital=initial_capital
    )
    engine.set_strategy(strategy)
    result = engine.run()
    
    # 计算买入持有收益
    df = engine.data
    buy_hold_return = (df['close'].iloc[-1] / df['close'].iloc[0] - 1) * 100
    
    # 获取交易统计
    trades = result.trades
    win_trades = [t for t in trades if t.pnl > 0]
    loss_trades = [t for t in trades if t.pnl <= 0]
    
    win_rate = len(win_trades) / len(trades) * 100 if trades else 0
    avg_profit = sum(t.pnl for t in win_trades) / len(win_trades) if win_trades else 0
    avg_loss = sum(t.pnl for t in loss_trades) / len(loss_trades) if loss_trades else 0
    profit_factor = abs(avg_profit / avg_loss) if avg_loss != 0 else 0
    
    return QuickBacktestResult(
        symbol=symbol,
        name=name,
        strategy_name=strategy.name,
        start_date=start_date,
        end_date=end_date,
        total_return=result.total_return * 100,
        annual_return=result.annual_return * 100,
        max_drawdown=result.max_drawdown * 100,
        sharpe_ratio=result.sharpe_ratio,
        trade_count=len(trades),
        win_rate=win_rate,
        avg_profit=avg_profit,
        avg_loss=avg_loss,
        profit_factor=profit_factor,
        buy_hold_return=buy_hold_return,
        excess_return=result.total_return * 100 - buy_hold_return
    )


def print_backtest_result(result: QuickBacktestResult):
    """打印回测结果"""
    print(f"\n{'='*60}")
    print(f"回测结果: {result.symbol} {result.name}")
    print(f"策略: {result.strategy_name}")
    print(f"时间: {result.start_date} ~ {result.end_date}")
    print(f"{'='*60}")
    
    print(f"\n【收益指标】")
    print(f"  策略收益:     {result.total_return:>+8.2f}%")
    print(f"  买入持有:     {result.buy_hold_return:>+8.2f}%")
    print(f"  超额收益:     {result.excess_return:>+8.2f}%")
    print(f"  年化收益:     {result.annual_return:>+8.2f}%")
    print(f"  最大回撤:     {result.max_drawdown:>8.2f}%")
    print(f"  夏普比率:     {result.sharpe_ratio:>8.2f}")
    
    print(f"\n【交易统计】")
    print(f"  交易次数:     {result.trade_count:>8}")
    print(f"  胜率:         {result.win_rate:>8.1f}%")
    print(f"  平均盈利:     ¥{result.avg_profit:>7.0f}")
    print(f"  平均亏损:     ¥{result.avg_loss:>7.0f}")
    print(f"  盈亏比:       {result.profit_factor:>8.2f}")
    
    # 综合评价
    print(f"\n【综合评价】")
    if result.excess_return > 5 and result.max_drawdown < 15:
        print(f"  ✅ 策略表现优于买入持有，且回撤可控")
    elif result.excess_return > 0:
        print(f"  ⚠️ 策略略优于买入持有")
    else:
        print(f"  ❌ 策略不如买入持有，建议调整参数")
    
    print(f"{'='*60}")


def compare_strategies(symbol: str,
                       strategies: List[BaseStrategy],
                       start_date: str = None,
                       end_date: str = None,
                       name: str = "") -> List[QuickBacktestResult]:
    """
    比较多个策略
    
    Args:
        symbol: 股票代码
        strategies: 策略列表
        start_date: 开始日期
        end_date: 结束日期
        name: 股票名称
    
    Returns:
        List[QuickBacktestResult]: 各策略回测结果
    """
    results = []
    
    for strategy in strategies:
        print(f"\n回测策略: {strategy.name}...")
        result = quick_backtest(symbol, strategy, start_date, end_date, name=name)
        results.append(result)
    
    # 打印比较表
    print(f"\n{'='*80}")
    print(f"策略比较: {symbol} {name}")
    print(f"{'='*80}")
    print(f"{'策略':<20}{'总收益':>10}{'买持':>10}{'超额':>10}{'回撤':>10}{'夏普':>10}{'胜率':>10}")
    print(f"{'-'*80}")
    
    for r in results:
        print(f"{r.strategy_name:<20}"
              f"{r.total_return:>+9.1f}%"
              f"{r.buy_hold_return:>+9.1f}%"
              f"{r.excess_return:>+9.1f}%"
              f"{r.max_drawdown:>9.1f}%"
              f"{r.sharpe_ratio:>10.2f}"
              f"{r.win_rate:>9.1f}%")
    
    print(f"{'='*80}")
    
    # 找出最佳策略
    best = max(results, key=lambda x: x.excess_return)
    print(f"\n🏆 最佳策略: {best.strategy_name} (超额收益 {best.excess_return:+.1f}%)")
    
    return results


def test_ma_params(symbol: str,
                   short_periods: List[int] = [5, 10],
                   long_periods: List[int] = [20, 30, 60],
                   start_date: str = None,
                   name: str = "") -> pd.DataFrame:
    """
    测试不同均线参数组合
    
    Args:
        symbol: 股票代码
        short_periods: 短期均线列表
        long_periods: 长期均线列表
    """
    results = []
    
    for short in short_periods:
        for long in long_periods:
            if short >= long:
                continue
            
            strategy = MACrossStrategy(short, long)
            print(f"测试 MA{short}/MA{long}...", end=" ")
            
            try:
                result = quick_backtest(symbol, strategy, start_date, name=name)
                results.append({
                    "短期均线": short,
                    "长期均线": long,
                    "总收益%": round(result.total_return, 2),
                    "超额收益%": round(result.excess_return, 2),
                    "最大回撤%": round(result.max_drawdown, 2),
                    "夏普": round(result.sharpe_ratio, 2),
                    "交易次数": result.trade_count,
                    "胜率%": round(result.win_rate, 1)
                })
                print(f"收益 {result.total_return:+.1f}%")
            except Exception as e:
                print(f"失败: {e}")
    
    df = pd.DataFrame(results)
    
    if not df.empty:
        print(f"\n{'='*80}")
        print(f"均线参数优化结果: {symbol} {name}")
        print(f"{'='*80}")
        print(df.sort_values("超额收益%", ascending=False).to_string(index=False))
        
        best = df.loc[df["超额收益%"].idxmax()]
        print(f"\n🏆 最佳参数: MA{int(best['短期均线'])}/MA{int(best['长期均线'])} "
              f"(超额收益 {best['超额收益%']:+.1f}%)")
    
    return df


# 便捷函数
def test_idea(symbol: str, name: str = ""):
    """
    测试多种常用策略（便捷函数）
    
    示例：
        test_idea("600519", "贵州茅台")
    """
    strategies = [
        MACrossStrategy(5, 20),
        MACrossStrategy(10, 30),
        MACDStrategy(),
        KDJStrategy(),
    ]
    
    return compare_strategies(symbol, strategies, name=name)


if __name__ == "__main__":
    # 示例：测试贵州茅台
    test_idea("600519", "贵州茅台")
