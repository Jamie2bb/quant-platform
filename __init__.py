"""
A股量化回测平台

使用示例:
    from quant.backtest import BacktestEngine
    from quant.strategy import MACrossStrategy
    
    engine = BacktestEngine("000001", "20230101", "20231231")
    engine.set_strategy(MACrossStrategy(5, 20))
    result = engine.run()
    result.summary()
"""

__version__ = "1.0.0"
__author__ = "Quant"

from .backtest import BacktestEngine, BacktestResult
from .strategy import (
    BaseStrategy,
    MACrossStrategy, 
    MomentumStrategy, 
    BreakoutStrategy
)
from .data import DataFetcher

__all__ = [
    "BacktestEngine",
    "BacktestResult", 
    "BaseStrategy",
    "MACrossStrategy",
    "MomentumStrategy",
    "BreakoutStrategy",
    "DataFetcher",
]
