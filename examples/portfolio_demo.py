"""
组合回测示例
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest.portfolio import PortfolioBacktest, run_portfolio_backtest


def main():
    print("=" * 60)
    print("组合回测示例")
    print("=" * 60)
    
    # 选择几只股票构建组合
    symbols = [
        "600519",  # 贵州茅台
        "000858",  # 五粮液
        "000333",  # 美的集团
        "600036",  # 招商银行
        "601318",  # 中国平安
    ]
    
    # 方式1: 快速运行（等权重，月度再平衡）
    print("\n【方式1: 快速运行】")
    result = run_portfolio_backtest(
        symbols=symbols,
        start_date="20230101",
        end_date="20240101",
        initial_capital=1000000,
        rebalance_freq="monthly"
    )
    result.summary()
    
    # 方式2: 自定义权重
    print("\n【方式2: 自定义权重】")
    engine = PortfolioBacktest(
        symbols=symbols,
        start_date="20230101",
        end_date="20240101",
        initial_capital=1000000
    )
    
    # 设置权重：茅台40%，其他各15%
    weights = {
        "600519": 0.40,
        "000858": 0.15,
        "000333": 0.15,
        "600036": 0.15,
        "601318": 0.15
    }
    
    engine.load_data()
    engine.set_weights(weights)
    
    result2 = engine.run(rebalance_freq="quarterly")
    result2.summary()
    
    # 保存图表
    result2.plot(save_path="portfolio_result.png")
    print("\n图表已保存: portfolio_result.png")
    
    # 查看交易记录
    trades = result2.get_trades_df()
    if not trades.empty:
        print("\n【交易记录（前10条）】")
        print(trades.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
