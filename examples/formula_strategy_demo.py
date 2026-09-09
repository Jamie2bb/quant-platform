# -*- coding: utf-8 -*-
"""
公式策略示例

展示如何使用类似通达信的公式语法定义买卖策略
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strategy.formula import (
    FormulaStrategy, 
    create_formula_strategy, 
    list_formula_strategies,
    StockScanner,
    create_scanner_from_preset,
    FORMULA_LIBRARY
)
from backtest.engine import BacktestEngine
from data.fetcher import DataFetcher
from datetime import datetime, timedelta


def demo_preset_strategies():
    """演示预设策略"""
    print("=" * 60)
    print("1. 预设公式策略列表")
    print("=" * 60)
    
    strategies = list_formula_strategies()
    for s in strategies:
        print(f"  - {s['name']}: {s['description']}")
    
    print(f"\n总计 {len(strategies)} 个预设策略")


def demo_custom_formula():
    """演示自定义公式策略"""
    print("\n" + "=" * 60)
    print("2. 自定义公式策略")
    print("=" * 60)
    
    # 创建自定义公式策略
    strategy = FormulaStrategy(
        buy_formula="CROSS(MA(df['close'],5), MA(df['close'],20)) & (df['volume'] > MA(df['volume'],5))",
        sell_formula="CROSS(MA(df['close'],20), MA(df['close'],5)) | (df['close'] < MA(df['close'],60))",
        name="放量均线金叉"
    )
    
    print(f"策略名称: {strategy.name}")
    print(f"买入条件: 5日均线上穿20日均线 且 成交量大于5日均量")
    print(f"卖出条件: 5日均线下穿20日均线 或 跌破60日均线")


def demo_backtest():
    """演示公式策略回测"""
    print("\n" + "=" * 60)
    print("3. 公式策略回测")
    print("=" * 60)
    
    # 使用预设策略回测
    strategy = create_formula_strategy("MACD金叉")
    
    print(f"回测策略: {strategy.name}")
    print("股票: 000001 平安银行")
    print("时间: 最近1年")
    
    try:
        engine = BacktestEngine(
            symbol="000001",
            start_date=(datetime.now() - timedelta(days=365)).strftime("%Y%m%d"),
            end_date=datetime.now().strftime("%Y%m%d"),
            initial_capital=100000
        )
        engine.set_strategy(strategy)
        result = engine.run()
        
        print(f"\n回测结果:")
        print(f"  - 总收益率: {result.total_return*100:+.2f}%")
        print(f"  - 最大回撤: {result.max_drawdown*100:.2f}%")
        print(f"  - 夏普比率: {result.sharpe_ratio:.2f}")
        print(f"  - 交易次数: {result.total_trades}")
        print(f"  - 胜率: {result.win_rate*100:.1f}%")
        
    except Exception as e:
        print(f"回测失败: {e}")


def demo_multi_strategy_comparison():
    """演示多策略对比"""
    print("\n" + "=" * 60)
    print("4. 多策略对比")
    print("=" * 60)
    
    strategies_to_test = ["双均线金叉", "MACD金叉", "RSI超卖", "海龟突破"]
    
    print("对比策略在 600519 贵州茅台 上的表现:\n")
    
    results = []
    for name in strategies_to_test:
        try:
            strategy = create_formula_strategy(name)
            engine = BacktestEngine(
                symbol="600519",
                start_date=(datetime.now() - timedelta(days=365)).strftime("%Y%m%d"),
                end_date=datetime.now().strftime("%Y%m%d"),
                initial_capital=100000
            )
            engine.set_strategy(strategy)
            result = engine.run()
            
            results.append({
                'name': name,
                'return': result.total_return * 100,
                'drawdown': result.max_drawdown * 100,
                'sharpe': result.sharpe_ratio,
                'trades': result.total_trades
            })
        except Exception as e:
            print(f"  {name}: 回测失败 - {e}")
    
    # 按收益排序
    results.sort(key=lambda x: x['return'], reverse=True)
    
    print(f"{'策略名称':<12} {'收益率':>10} {'最大回撤':>10} {'夏普比率':>10} {'交易次数':>10}")
    print("-" * 54)
    for r in results:
        print(f"{r['name']:<12} {r['return']:>+9.2f}% {r['drawdown']:>9.2f}% {r['sharpe']:>10.2f} {r['trades']:>10}")


def demo_stock_scanner():
    """演示选股扫描"""
    print("\n" + "=" * 60)
    print("5. 选股扫描")
    print("=" * 60)
    
    # 使用预设条件
    print("使用预设条件「强势股」扫描...")
    scanner = create_scanner_from_preset("强势股")
    
    # 扫描股票列表
    stocks = [
        {"code": "000001", "name": "平安银行"},
        {"code": "600519", "name": "贵州茅台"},
        {"code": "000858", "name": "五粮液"},
        {"code": "600036", "name": "招商银行"},
        {"code": "601318", "name": "中国平安"},
    ]
    
    print(f"\n扫描 {len(stocks)} 只股票...")
    
    for stock in stocks:
        try:
            start = (datetime.now() - timedelta(days=180)).strftime("%Y%m%d")
            df = DataFetcher.get_stock_daily(stock['code'], start)
            
            result = scanner.check_stock(df)
            all_pass = all(result.values())
            
            status = "✅ 符合" if all_pass else "❌ 不符合"
            print(f"\n  {stock['code']} {stock['name']}: {status}")
            for k, v in result.items():
                print(f"    - {k}: {'✓' if v else '✗'}")
                
        except Exception as e:
            print(f"  {stock['code']} {stock['name']}: 扫描失败 - {e}")


def demo_custom_scanner():
    """演示自定义选股条件"""
    print("\n" + "=" * 60)
    print("6. 自定义选股条件")
    print("=" * 60)
    
    # 创建自定义扫描器
    scanner = StockScanner()
    scanner.add_condition("价格突破20日高点", "df['close'] > HHV(df['high'].shift(1), 20)")
    scanner.add_condition("成交量放大", "df['volume'] > MA(df['volume'], 5) * 1.5")
    scanner.add_condition("MACD红柱", "MACD_HIST > 0")
    scanner.add_condition("RSI适中", "(RSI(df['close'],14) > 40) & (RSI(df['close'],14) < 70)")
    
    print("自定义条件:")
    for cond in scanner.conditions:
        print(f"  - {cond['name']}")
    
    print("\n扫描 000001 平安银行...")
    try:
        start = (datetime.now() - timedelta(days=180)).strftime("%Y%m%d")
        df = DataFetcher.get_stock_daily("000001", start)
        
        result = scanner.check_stock(df)
        for k, v in result.items():
            print(f"  - {k}: {'✓ 符合' if v else '✗ 不符合'}")
    except Exception as e:
        print(f"扫描失败: {e}")


if __name__ == "__main__":
    print("公式策略系统演示")
    print("参考通达信/同花顺/聚宽的公式语法")
    print("=" * 60)
    
    demo_preset_strategies()
    demo_custom_formula()
    demo_backtest()
    demo_multi_strategy_comparison()
    demo_stock_scanner()
    demo_custom_scanner()
    
    print("\n" + "=" * 60)
    print("演示完成！")
    print("=" * 60)
