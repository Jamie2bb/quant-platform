"""
因子分析示例
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from data.fetcher import DataFetcher
from report.factor_report import (
    FactorAnalyzer, 
    momentum_factor, volatility_factor, volume_factor, reversal_factor
)


def main():
    print("=" * 60)
    print("因子分析示例")
    print("=" * 60)
    
    # 获取股票数据
    print("\n正在获取数据...")
    symbol = "000001"
    df = DataFetcher.get_stock_daily(symbol, "20220101", "20240101")
    print(f"获取 {symbol} 数据: {len(df)} 条记录")
    
    # 计算多个因子
    print("\n正在计算因子...")
    factor_df = pd.DataFrame(index=df.index)
    factor_df["momentum_10"] = momentum_factor(df, 10)
    factor_df["momentum_20"] = momentum_factor(df, 20)
    factor_df["volatility"] = volatility_factor(df, 20)
    factor_df["volume_ratio"] = volume_factor(df, 20)
    factor_df["reversal"] = reversal_factor(df, 5)
    
    # 计算收益率
    returns = df["close"].pct_change()
    
    # 创建分析器
    analyzer = FactorAnalyzer(factor_df, returns)
    
    # 分析各因子
    print("\n" + "=" * 60)
    print("因子 IC 分析")
    print("=" * 60)
    print(f"\n{'因子':<15}{'IC':>10}{'IC均值':>10}{'IR':>10}")
    print("-" * 45)
    
    for factor_name in factor_df.columns:
        try:
            ic = analyzer.calculate_ic(factor_name)
            ic_series = analyzer.calculate_ic_series(factor_name)
            ir = analyzer.calculate_ir(factor_name)
            ic_mean = ic_series.mean() if len(ic_series) > 0 else 0
            
            print(f"{factor_name:<15}{ic:>10.4f}{ic_mean:>10.4f}{ir:>10.4f}")
        except Exception as e:
            print(f"{factor_name:<15} 计算失败: {e}")
    
    # 详细分析最佳因子
    print("\n" + "=" * 60)
    print("动量因子详细分析")
    print("=" * 60)
    
    analyzer.print_report("momentum_20")
    
    # 因子相关性
    print("\n【因子相关性矩阵】")
    corr = analyzer.factor_correlation()
    print(corr.round(3).to_string())
    
    # 分组收益
    print("\n【动量因子分组收益】")
    group_return = analyzer.factor_group_return("momentum_20", n_groups=5)
    print(group_return.round(4).to_string())


if __name__ == "__main__":
    main()
