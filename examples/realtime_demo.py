"""
实时行情获取示例
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.fetcher import DataFetcher


def main():
    print("=" * 60)
    print("AKShare 数据获取示例")
    print("=" * 60)
    
    # 1. 获取单只股票日K线
    print("\n【1. 获取平安银行日K线（最近10天）】")
    df = DataFetcher.get_stock_daily("000001", "20240101")
    print(df.tail(10))
    
    # 2. 获取实时行情（全市场）
    print("\n【2. 获取全市场实时行情（前10只）】")
    df = DataFetcher.get_realtime_quotes()
    print(df[["symbol", "name", "price", "pct_change", "volume"]].head(10))
    
    # 3. 获取股票基本信息
    print("\n【3. 获取贵州茅台基本信息】")
    info = DataFetcher.get_stock_info("600519")
    for k, v in info.items():
        print(f"  {k}: {v}")
    
    # 4. 获取行业板块
    print("\n【4. 获取行业板块列表（前10个）】")
    df = DataFetcher.get_industry_board()
    print(df.head(10))
    
    # 5. 获取概念板块
    print("\n【5. 获取概念板块列表（前10个）】")
    df = DataFetcher.get_concept_board()
    print(df.head(10))


if __name__ == "__main__":
    main()
