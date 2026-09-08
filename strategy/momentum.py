"""
动量策略
"""
import pandas as pd
import numpy as np
from .base import BaseStrategy


class MomentumStrategy(BaseStrategy):
    """
    动量策略
    
    基于过去N日涨幅判断趋势
    买入：N日涨幅超过阈值
    卖出：N日跌幅超过阈值 或 持有超过M日
    """
    
    def __init__(self, lookback: int = 20, buy_threshold: float = 0.1, 
                 sell_threshold: float = -0.05, hold_days: int = 10):
        super().__init__(name=f"Momentum({lookback}d)")
        self.lookback = lookback
        self.buy_threshold = buy_threshold      # 买入阈值：10%涨幅
        self.sell_threshold = sell_threshold    # 止损阈值：-5%
        self.hold_days = hold_days              # 最大持有天数
    
    def prepare_data(self):
        """计算动量指标"""
        # N日涨幅
        self.data["momentum"] = self.data["close"].pct_change(self.lookback)
        
        # N日最高价涨幅（用于突破判断）
        self.data["high_momentum"] = (
            self.data["high"].rolling(self.lookback).max() / 
            self.data["close"].shift(self.lookback) - 1
        )
    
    def generate_signals(self) -> pd.Series:
        signals = pd.Series(0, index=self.data.index)
        
        # 动量突破阈值买入
        buy_condition = self.data["momentum"] > self.buy_threshold
        
        # 动量跌破阈值卖出
        sell_condition = self.data["momentum"] < self.sell_threshold
        
        signals[buy_condition] = 1
        signals[sell_condition] = -1
        
        return signals


class RSIMomentumStrategy(BaseStrategy):
    """
    RSI 动量策略
    
    基于 RSI 指标的超买超卖策略
    买入：RSI 从超卖区（<30）回升
    卖出：RSI 进入超买区（>70）
    """
    
    def __init__(self, period: int = 14, oversold: int = 30, overbought: int = 70):
        super().__init__(name=f"RSI({period})")
        self.period = period
        self.oversold = oversold
        self.overbought = overbought
    
    def prepare_data(self):
        """计算 RSI"""
        delta = self.data["close"].diff()
        
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=self.period).mean()
        avg_loss = loss.rolling(window=self.period).mean()
        
        rs = avg_gain / avg_loss
        self.data["rsi"] = 100 - (100 / (1 + rs))
    
    def generate_signals(self) -> pd.Series:
        signals = pd.Series(0, index=self.data.index)
        
        rsi = self.data["rsi"]
        
        # RSI 从超卖区回升（上穿30）
        buy_signal = (rsi > self.oversold) & (rsi.shift(1) <= self.oversold)
        
        # RSI 进入超买区（上穿70）
        sell_signal = (rsi > self.overbought) & (rsi.shift(1) <= self.overbought)
        
        signals[buy_signal] = 1
        signals[sell_signal] = -1
        
        return signals
