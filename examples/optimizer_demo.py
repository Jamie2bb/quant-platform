"""
参数优化示例
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from optimizer.grid_search import GridSearchOptimizer
from strategy.ma_cross import MACrossStrategy


def main():
    # 创建优化器
    optimizer = GridSearchOptimizer(
        symbol="000001",
        start_date="20230101",
        end_date="20231231",
        initial_capital=100000
    )
    
    # 定义参数网格
    param_grid = {
        "short_period": [3, 5, 8, 10, 13],
        "long_period": [15, 20, 30, 40, 60]
    }
    
    # 执行网格搜索
    print("开始参数优化...")
    results = optimizer.optimize(
        strategy_class=MACrossStrategy,
        param_grid=param_grid,
        metric="sharpe_ratio"
    )
    
    # 输出报告
    optimizer.report(results, top_n=10)
    
    # 保存结果
    results.to_csv("optimization_results.csv", index=False)
    print("\n结果已保存到 optimization_results.csv")


if __name__ == "__main__":
    main()
