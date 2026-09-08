"""
网格搜索参数优化器
"""
import pandas as pd
import numpy as np
from itertools import product
from typing import Type, Dict, List, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest.engine import BacktestEngine
from strategy.base import BaseStrategy


class GridSearchOptimizer:
    """
    网格搜索优化器
    
    遍历所有参数组合，找出最优参数
    """
    
    def __init__(self, symbol: str, start_date: str, end_date: str,
                 initial_capital: float = 100000):
        self.symbol = symbol
        self.start_date = start_date
        self.end_date = end_date
        self.initial_capital = initial_capital
        
        # 预加载数据，避免重复获取
        self._data = None
    
    def _load_data(self):
        """预加载数据"""
        if self._data is None:
            from data.fetcher import DataFetcher
            print(f"加载 {self.symbol} 数据...")
            self._data = DataFetcher.get_stock_daily(
                self.symbol, self.start_date, self.end_date
            )
            print(f"数据加载完成，共 {len(self._data)} 条")
    
    def optimize(self, strategy_class: Type[BaseStrategy], 
                 param_grid: Dict[str, List[Any]],
                 metric: str = "sharpe_ratio",
                 n_jobs: int = 1) -> pd.DataFrame:
        """
        执行网格搜索
        
        Args:
            strategy_class: 策略类
            param_grid: 参数网格，如 {"short_period": [5,10,15], "long_period": [20,30,40]}
            metric: 优化目标 - total_return/sharpe_ratio/calmar_ratio/max_drawdown
            n_jobs: 并行数（暂不支持，保留参数）
        
        Returns:
            DataFrame: 所有参数组合的回测结果
        """
        self._load_data()
        
        # 生成所有参数组合
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        combinations = list(product(*param_values))
        
        print(f"共 {len(combinations)} 个参数组合待测试")
        
        results = []
        
        for i, combo in enumerate(combinations):
            params = dict(zip(param_names, combo))
            
            # 跳过无效组合（如短周期 >= 长周期）
            if "short_period" in params and "long_period" in params:
                if params["short_period"] >= params["long_period"]:
                    continue
            
            if "short" in params and "long" in params:
                if params["short"] >= params["long"]:
                    continue
            
            try:
                # 创建策略实例
                strategy = strategy_class(**params)
                
                # 创建回测引擎（复用数据）
                engine = BacktestEngine(
                    symbol=self.symbol,
                    start_date=self.start_date,
                    end_date=self.end_date,
                    initial_capital=self.initial_capital
                )
                engine.data = self._data.copy()
                engine.set_strategy(strategy)
                
                # 运行回测
                result = engine.run()
                
                # 记录结果
                record = {
                    **params,
                    "total_return": result.total_return,
                    "annual_return": result.annual_return,
                    "max_drawdown": result.max_drawdown,
                    "sharpe_ratio": result.sharpe_ratio,
                    "calmar_ratio": result.calmar_ratio,
                    "win_rate": result.win_rate,
                    "total_trades": result.total_trades,
                    "profit_factor": result.profit_factor,
                }
                results.append(record)
                
                # 进度显示
                if (i + 1) % 10 == 0 or i == len(combinations) - 1:
                    print(f"进度: {i + 1}/{len(combinations)}")
                    
            except Exception as e:
                print(f"参数 {params} 回测失败: {e}")
                continue
        
        # 转为 DataFrame 并排序
        df = pd.DataFrame(results)
        
        if len(df) > 0:
            # 根据优化目标排序
            if metric == "max_drawdown":
                df = df.sort_values(metric, ascending=False)  # 回撤越小越好（负数）
            else:
                df = df.sort_values(metric, ascending=False)
        
        return df
    
    def report(self, results: pd.DataFrame, top_n: int = 10):
        """输出优化报告"""
        print("\n" + "=" * 70)
        print(f"参数优化结果 - {self.symbol}")
        print("=" * 70)
        
        if len(results) == 0:
            print("无有效结果")
            return
        
        print(f"\n【最优 {min(top_n, len(results))} 组参数】\n")
        
        # 格式化输出
        display_cols = results.columns.tolist()
        display_df = results.head(top_n).copy()
        
        # 格式化百分比列
        pct_cols = ["total_return", "annual_return", "max_drawdown", "win_rate"]
        for col in pct_cols:
            if col in display_df.columns:
                display_df[col] = display_df[col].apply(lambda x: f"{x:.2%}")
        
        # 格式化小数列
        float_cols = ["sharpe_ratio", "calmar_ratio", "profit_factor"]
        for col in float_cols:
            if col in display_df.columns:
                display_df[col] = display_df[col].apply(lambda x: f"{x:.2f}")
        
        print(display_df.to_string(index=False))
        
        # 最优参数
        best = results.iloc[0]
        print("\n【最优参数】")
        param_cols = [c for c in results.columns if c not in 
                      ["total_return", "annual_return", "max_drawdown", "sharpe_ratio", 
                       "calmar_ratio", "win_rate", "total_trades", "profit_factor"]]
        for col in param_cols:
            print(f"  {col}: {best[col]}")
        
        print(f"\n【最优绩效】")
        print(f"  总收益率: {best['total_return']:.2%}")
        print(f"  夏普比率: {best['sharpe_ratio']:.2f}")
        print(f"  最大回撤: {best['max_drawdown']:.2%}")
        print(f"  交易次数: {best['total_trades']}")
        print("=" * 70)
