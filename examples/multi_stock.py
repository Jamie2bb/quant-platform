"""
多股票组合回测示例
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest.engine import MultiStockBacktest
from strategy.ma_cross import MACrossStrategy


def main():
    # 选择一组股票
    symbols = [
        "600519",  # 贵州茅台
        "000858",  # 五粮液
        "000001",  # 平安银行
        "600036",  # 招商银行
        "601318",  # 中国平安
    ]
    
    # 创建多股票回测
    backtest = MultiStockBacktest(
        symbols=symbols,
        start_date="20230101",
        end_date="20231231",
        initial_capital=500000  # 总资金50万，每只股票10万
    )
    
    # 设置策略
    backtest.set_strategy(MACrossStrategy, short_period=5, long_period=20)
    
    # 运行回测
    results = backtest.run()
    
    # 输出汇总
    backtest.summary()
    
    # 单独查看每只股票的详细结果
    print("\n\n" + "="*60)
    print("各股票详细结果")
    print("="*60)
    
    for symbol, result in results.items():
        print(f"\n{symbol}:")
        result.summary()


if __name__ == "__main__":
    main()
