# -*- coding: utf-8 -*-
"""
公式策略快速体验（离线版）

使用模拟数据演示公式策略功能，无需联网
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np

from strategy.formula import (
    FormulaStrategy, 
    create_formula_strategy, 
    list_formula_strategies,
    StockScanner,
    FORMULA_LIBRARY
)
from utils.indicators_pro import (
    MA, EMA, MACD, RSI, KDJ, BOLL, 
    CROSS, HHV, LLV, ATR,
    add_all_indicators, generate_signals
)


def create_mock_data(days=200):
    """创建模拟股票数据"""
    np.random.seed(42)
    dates = pd.date_range(end=pd.Timestamp.now(), periods=days, freq='D')
    
    # 生成带趋势的价格
    base = 10
    trend = np.cumsum(np.random.randn(days) * 0.3)
    noise = np.random.randn(days) * 0.5
    close = base + trend + noise
    close = np.maximum(close, 1)  # 确保价格为正
    
    # 生成 OHLV
    high = close * (1 + np.abs(np.random.randn(days) * 0.02))
    low = close * (1 - np.abs(np.random.randn(days) * 0.02))
    open_price = close + np.random.randn(days) * 0.2
    volume = np.random.randint(1000000, 10000000, days)
    
    return pd.DataFrame({
        'open': open_price,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume
    }, index=dates)


def demo_indicators():
    """演示技术指标库"""
    print("=" * 60)
    print("1. 技术指标库演示")
    print("=" * 60)
    
    df = create_mock_data()
    print(f"模拟数据: {len(df)} 天")
    
    # 计算各种指标
    ma5 = MA(df['close'], 5)
    ma20 = MA(df['close'], 20)
    ema12 = EMA(df['close'], 12)
    rsi = RSI(df['close'], 14)
    dif, dea, macd_hist = MACD(df['close'])
    k, d, j = KDJ(df['high'], df['low'], df['close'])
    upper, mid, lower = BOLL(df['close'])
    atr = ATR(df['high'], df['low'], df['close'])
    
    print(f"\n最新指标值（最后一天）:")
    print(f"  - MA5:   {ma5.iloc[-1]:.2f}")
    print(f"  - MA20:  {ma20.iloc[-1]:.2f}")
    print(f"  - EMA12: {ema12.iloc[-1]:.2f}")
    print(f"  - RSI:   {rsi.iloc[-1]:.2f}")
    print(f"  - MACD DIF: {dif.iloc[-1]:.3f}")
    print(f"  - MACD DEA: {dea.iloc[-1]:.3f}")
    print(f"  - KDJ K: {k.iloc[-1]:.2f}, D: {d.iloc[-1]:.2f}, J: {j.iloc[-1]:.2f}")
    print(f"  - 布林上轨: {upper.iloc[-1]:.2f}, 中轨: {mid.iloc[-1]:.2f}, 下轨: {lower.iloc[-1]:.2f}")
    print(f"  - ATR:   {atr.iloc[-1]:.3f}")


def demo_cross_function():
    """演示 CROSS 函数"""
    print("\n" + "=" * 60)
    print("2. CROSS 函数演示")
    print("=" * 60)
    
    df = create_mock_data()
    ma5 = MA(df['close'], 5)
    ma20 = MA(df['close'], 20)
    
    # 金叉
    golden_cross = CROSS(ma5, ma20)
    # 死叉
    death_cross = CROSS(ma20, ma5)
    
    golden_dates = df.index[golden_cross].tolist()
    death_dates = df.index[death_cross].tolist()
    
    print(f"\nMA5/MA20 交叉情况（最近200天）:")
    print(f"  - 金叉次数: {len(golden_dates)}")
    print(f"  - 死叉次数: {len(death_dates)}")
    
    if golden_dates:
        print(f"\n  最近金叉日期:")
        for d in golden_dates[-3:]:
            print(f"    - {d.strftime('%Y-%m-%d')}")


def demo_formula_strategy():
    """演示公式策略"""
    print("\n" + "=" * 60)
    print("3. 公式策略演示")
    print("=" * 60)
    
    df = create_mock_data()
    
    # 创建公式策略
    strategy = FormulaStrategy(
        buy_formula="CROSS(MA(df['close'],5), MA(df['close'],20))",
        sell_formula="CROSS(MA(df['close'],20), MA(df['close'],5))",
        name="双均线金叉"
    )
    
    strategy.set_data(df)
    signals = strategy.generate_signals()
    
    buy_signals = (signals == 1).sum()
    sell_signals = (signals == -1).sum()
    
    print(f"\n策略: {strategy.name}")
    print(f"  - 买入条件: 5日均线上穿20日均线")
    print(f"  - 卖出条件: 5日均线下穿20日均线")
    print(f"\n信号统计:")
    print(f"  - 买入信号: {buy_signals} 次")
    print(f"  - 卖出信号: {sell_signals} 次")
    
    # 显示最近的信号
    buy_dates = df.index[signals == 1].tolist()
    sell_dates = df.index[signals == -1].tolist()
    
    if buy_dates:
        print(f"\n  最近买入信号:")
        for d in buy_dates[-3:]:
            idx = df.index.get_loc(d)
            print(f"    - {d.strftime('%Y-%m-%d')} 价格: {df['close'].iloc[idx]:.2f}")


def demo_preset_strategies():
    """演示预设策略"""
    print("\n" + "=" * 60)
    print("4. 预设公式策略库")
    print("=" * 60)
    
    strategies = list_formula_strategies()
    
    print(f"\n共 {len(strategies)} 个预设策略:\n")
    
    # 按类型分组
    categories = {
        "均线策略": ["双均线金叉", "三均线多头", "均线支撑"],
        "MACD策略": ["MACD金叉", "MACD零轴上金叉", "MACD底背离"],
        "KDJ/RSI策略": ["KDJ金叉", "KDJ超卖反弹", "RSI超卖", "RSI背离"],
        "布林带策略": ["布林带下轨支撑", "布林带收口突破"],
        "突破策略": ["N日新高", "放量突破", "跳空高开", "海龟突破", "ATR突破"],
        "量价策略": ["量价齐升", "缩量调整后放量"],
        "形态策略": ["锤子线", "吞没形态", "启明星"],
    }
    
    for cat, names in categories.items():
        print(f"【{cat}】")
        for name in names:
            if name in FORMULA_LIBRARY:
                desc = FORMULA_LIBRARY[name]['description']
                print(f"  - {name}: {desc}")
        print()


def demo_stock_scanner():
    """演示选股扫描器"""
    print("=" * 60)
    print("5. 选股扫描器演示")
    print("=" * 60)
    
    # 创建多只模拟股票
    stocks_data = {}
    for i in range(5):
        np.random.seed(i * 10)  # 不同的随机种子产生不同走势
        stocks_data[f"STOCK{i+1}"] = create_mock_data()
    
    # 创建选股扫描器
    scanner = StockScanner()
    scanner.add_condition("站上MA20", "df['close'] > MA(df['close'],20)")
    scanner.add_condition("MACD多头", "DIF > DEA")
    scanner.add_condition("RSI适中", "(RSI(df['close'],14) > 30) & (RSI(df['close'],14) < 70)")
    
    print("\n选股条件:")
    for cond in scanner.conditions:
        print(f"  - {cond['name']}")
    
    print("\n扫描结果:")
    passed = []
    for name, df in stocks_data.items():
        result = scanner.check_stock(df)
        all_pass = all(result.values())
        status = "✅" if all_pass else "❌"
        details = ", ".join([f"{k}:{'✓' if v else '✗'}" for k, v in result.items()])
        print(f"  {name}: {status} ({details})")
        if all_pass:
            passed.append(name)
    
    print(f"\n符合条件的股票: {len(passed)} 只")


def demo_signal_generation():
    """演示信号生成"""
    print("\n" + "=" * 60)
    print("6. 综合信号生成")
    print("=" * 60)
    
    df = create_mock_data()
    
    # 添加所有指标
    df_with_indicators = add_all_indicators(df)
    
    # 生成信号
    signals = generate_signals(df_with_indicators)
    
    print(f"\n当前综合信号分析:")
    print(f"\n✅ 多头信号 ({len(signals['bullish'])} 个):")
    for s in signals['bullish']:
        print(f"    - {s}")
    
    print(f"\n⚠️ 空头信号 ({len(signals['bearish'])} 个):")
    for s in signals['bearish']:
        print(f"    - {s}")
    
    print(f"\nℹ️ 中性信号 ({len(signals['neutral'])} 个):")
    for s in signals['neutral']:
        print(f"    - {s}")


def demo_complex_formula():
    """演示复杂公式"""
    print("\n" + "=" * 60)
    print("7. 复杂公式组合")
    print("=" * 60)
    
    df = create_mock_data()
    
    # 复杂买入条件：
    # 1. MA5 > MA20 (趋势向上)
    # 2. MACD金叉
    # 3. RSI < 70 (不超买)
    # 4. 成交量放大
    complex_strategy = FormulaStrategy(
        buy_formula="""
            (MA(df['close'],5) > MA(df['close'],20)) & 
            (CROSS(DIF, DEA)) & 
            (RSI(df['close'],14) < 70) & 
            (df['volume'] > MA(df['volume'],5) * 1.2)
        """,
        sell_formula="""
            (CROSS(DEA, DIF)) | 
            (RSI(df['close'],14) > 80) |
            (df['close'] < MA(df['close'],20) * 0.95)
        """,
        name="多条件综合策略"
    )
    
    print(f"\n策略: {complex_strategy.name}")
    print(f"\n买入条件（同时满足）:")
    print(f"  1. MA5 > MA20（趋势向上）")
    print(f"  2. MACD金叉")
    print(f"  3. RSI < 70（不超买）")
    print(f"  4. 成交量 > 5日均量*1.2（放量）")
    print(f"\n卖出条件（满足其一）:")
    print(f"  1. MACD死叉")
    print(f"  2. RSI > 80（超买）")
    print(f"  3. 跌破MA20的95%")
    
    complex_strategy.set_data(df)
    signals = complex_strategy.generate_signals()
    
    buy_count = (signals == 1).sum()
    sell_count = (signals == -1).sum()
    
    print(f"\n信号统计:")
    print(f"  - 买入信号: {buy_count} 次")
    print(f"  - 卖出信号: {sell_count} 次")


if __name__ == "__main__":
    print("╔" + "═" * 58 + "╗")
    print("║" + " 公式策略系统快速体验 ".center(56) + "║")
    print("║" + " （离线版 - 使用模拟数据）".center(52) + "║")
    print("╚" + "═" * 58 + "╝")
    
    demo_indicators()
    demo_cross_function()
    demo_formula_strategy()
    demo_preset_strategies()
    demo_stock_scanner()
    demo_signal_generation()
    demo_complex_formula()
    
    print("\n" + "=" * 60)
    print("✅ 演示完成！")
    print("\n下一步:")
    print("  1. 启动 Web 界面: streamlit run web/app.py")
    print("  2. 选择「我的持仓」→「公式策略」标签页")
    print("  3. 在网页上使用真实股票数据进行回测")
    print("=" * 60)
