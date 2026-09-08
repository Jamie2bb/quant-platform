"""
选股筛选示例
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from screener.stock_screener import (
    StockScreener,
    create_value_screener,
    create_momentum_screener
)


def main():
    print("=" * 60)
    print("股票筛选示例")
    print("=" * 60)
    
    # 方式1: 使用预设筛选器
    print("\n【价值股筛选】")
    screener = create_value_screener()
    results = screener.screen()
    
    if len(results) > 0:
        print(results[["symbol", "name", "price", "pct_change", "pe", "pb"]].head(20))
    
    # 方式2: 自定义筛选条件
    print("\n【自定义筛选：低价高换手】")
    custom_screener = (StockScreener()
        .exclude_st()
        .main_board_only()
        .price_range(5, 20)
        .turnover_min(5)
        .pct_change_range(-3, 5)
    )
    
    results2 = custom_screener.screen()
    
    if len(results2) > 0:
        print(results2[["symbol", "name", "price", "pct_change", "turnover"]].head(20))


if __name__ == "__main__":
    main()
