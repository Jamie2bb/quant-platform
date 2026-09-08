"""
组合策略
"""
import pandas as pd
import numpy as np
from .base import BaseStrategy


class CompositeStrategy(BaseStrategy):
    """
    多策略组合
    
    综合多个策略的信号，投票决定
    """
    
    def __init__(self, strategies: list, min_votes: int = 2):
        """
        Args:
            strategies: 策略列表
            min_votes: 最少需要多少个策略同意才交易
        """
        names = "+".join([s.name[:10] for s in strategies[:3]])
        super().__init__(name=f"Composite({names})")
        self.strategies = strategies
        self.min_votes = min_votes
    
    def prepare_data(self):
        # 为所有子策略准备数据
        for strategy in self.strategies:
            strategy.set_data(self.data)
    
    def generate_signals(self) -> pd.Series:
        signals = pd.Series(0, index=self.data.index)
        
        # 收集所有策略的信号
        all_signals = []
        for strategy in self.strategies:
            sig = strategy.generate_signals()
            all_signals.append(sig)
        
        # 合并信号
        signal_df = pd.concat(all_signals, axis=1)
        
        # 买入票数
        buy_votes = (signal_df == 1).sum(axis=1)
        # 卖出票数
        sell_votes = (signal_df == -1).sum(axis=1)
        
        # 投票决定
        signals[buy_votes >= self.min_votes] = 1
        signals[sell_votes >= self.min_votes] = -1
        
        return signals


class ConfirmationStrategy(BaseStrategy):
    """
    确认策略
    
    主策略发出信号后，需要确认策略也同意才执行
    """
    
    def __init__(self, main_strategy: BaseStrategy, confirm_strategy: BaseStrategy):
        super().__init__(name=f"Confirm({main_strategy.name})")
        self.main_strategy = main_strategy
        self.confirm_strategy = confirm_strategy
    
    def prepare_data(self):
        self.main_strategy.set_data(self.data)
        self.confirm_strategy.set_data(self.data)
    
    def generate_signals(self) -> pd.Series:
        main_signals = self.main_strategy.generate_signals()
        confirm_signals = self.confirm_strategy.generate_signals()
        
        signals = pd.Series(0, index=self.data.index)
        
        # 主策略买入 且 确认策略不反对（不是卖出信号）
        buy_signal = (main_signals == 1) & (confirm_signals != -1)
        
        # 主策略卖出 或 确认策略卖出
        sell_signal = (main_signals == -1) | (confirm_signals == -1)
        
        signals[buy_signal] = 1
        signals[sell_signal] = -1
        
        return signals


class FilteredStrategy(BaseStrategy):
    """
    过滤策略
    
    只在满足过滤条件时交易
    """
    
    def __init__(self, base_strategy: BaseStrategy, 
                 trend_period: int = 60,
                 volatility_filter: bool = True):
        """
        Args:
            base_strategy: 基础策略
            trend_period: 趋势判断周期
            volatility_filter: 是否过滤高波动
        """
        super().__init__(name=f"Filtered({base_strategy.name})")
        self.base_strategy = base_strategy
        self.trend_period = trend_period
        self.volatility_filter = volatility_filter
    
    def prepare_data(self):
        self.base_strategy.set_data(self.data)
        
        close = self.data["close"]
        
        # 趋势过滤
        self.data["ma_long"] = close.rolling(self.trend_period).mean()
        self.data["uptrend"] = close > self.data["ma_long"]
        
        # 波动率过滤
        if self.volatility_filter:
            volatility = close.pct_change().rolling(20).std()
            vol_threshold = volatility.rolling(60).quantile(0.8)
            self.data["low_vol"] = volatility < vol_threshold
        else:
            self.data["low_vol"] = True
    
    def generate_signals(self) -> pd.Series:
        base_signals = self.base_strategy.generate_signals()
        
        signals = pd.Series(0, index=self.data.index)
        
        uptrend = self.data["uptrend"]
        low_vol = self.data["low_vol"]
        
        # 只在上升趋势 + 低波动时买入
        buy_signal = (base_signals == 1) & uptrend & low_vol
        
        # 卖出信号不过滤
        sell_signal = base_signals == -1
        
        signals[buy_signal] = 1
        signals[sell_signal] = -1
        
        return signals


class RotationStrategy(BaseStrategy):
    """
    轮动策略框架
    
    比较多个标的，选择最强的持有
    （单股票回测时简化为趋势跟踪）
    """
    
    def __init__(self, momentum_period: int = 20, hold_period: int = 20):
        super().__init__(name=f"Rotation({momentum_period}d)")
        self.momentum_period = momentum_period
        self.hold_period = hold_period
    
    def prepare_data(self):
        close = self.data["close"]
        
        # 动量排名
        self.data["momentum"] = close.pct_change(self.momentum_period)
        
        # 动量排名的历史百分位
        self.data["momentum_rank"] = self.data["momentum"].rolling(60).apply(
            lambda x: pd.Series(x).rank(pct=True).iloc[-1]
        )
        
        self.data["ma20"] = close.rolling(20).mean()
    
    def generate_signals(self) -> pd.Series:
        signals = pd.Series(0, index=self.data.index)
        
        close = self.data["close"]
        momentum_rank = self.data["momentum_rank"]
        ma20 = self.data["ma20"]
        
        # 动量处于历史高位 + 站上均线
        buy_signal = (momentum_rank > 0.7) & (close > ma20)
        
        # 动量衰减
        sell_signal = momentum_rank < 0.3
        
        signals[buy_signal] = 1
        signals[sell_signal] = -1
        
        return signals
