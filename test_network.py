"""测试网络稳定性"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.fetcher import DataFetcher
import time

print("测试数据获取...")
print("=" * 50)

# 测试1: 获取单只股票（最常用）
print("\n1. 获取平安银行最近数据")
start = time.time()
df = DataFetcher.get_stock_daily("000001", "20240801")
print(f"   成功! {len(df)} 条, 耗时 {time.time()-start:.1f}秒")
print(f"   最新: {df.index[-1].strftime('%Y-%m-%d')} 收盘 {df.iloc[-1]['close']:.2f}")

# 测试2: 批量获取（用于组合回测）
print("\n2. 批量获取3只股票")
start = time.time()
result = DataFetcher.get_multiple_stocks(
    ["000001", "600519", "000858"], 
    "20240801",
    show_progress=True
)
print(f"   成功获取 {len(result)} 只, 耗时 {time.time()-start:.1f}秒")

print("\n" + "=" * 50)
print("测试完成! 网络正常工作。")
print("\n提示: 全市场实时行情(get_realtime_quotes)数据量大，")
print("      需要请求59次，耗时较长是正常的。")
