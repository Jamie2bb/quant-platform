"""
KDJ 策略
"""
import pandas as pd
import numpy as np
from .base import BaseStrategy


class KDJStrategy(BaseStrategy):
    """
    KDJ 超买超卖策略
    
    买入：K 从超卖区（<20）上穿 D
    卖出：K 从超买区（>80）下穿 D
    """
    
    def __init__(self, n: int = 9, m1: int = 3, m2: int = 3,
                 oversold: int = 20, overbought: int = 80):
        super().__init__(name=f"KDJ({n},{m1},{m2})")
        self.n = n
        self.m1 = m1
        self.m2 = m2
        self.oversold = oversold
        self.overbought = overbought
    
    def prepare_data(self):
        high = self.data["high"]
        low = self.data["low"]
        close = self.data["close"]
        
        # 计算 RSV
        lowest_low = low.rolling(window=self.n).min()
        highest_high = high.rolling(window=self.n).max()
        rsv = (close - lowest_low) / (highest_high - lowest_low) * 100
        rsv = rsv.fillna(50)
        
        # 计算 K、D、J
        self.data["k"] = rsv.ewm(com=self.m1 - 1, adjust=False).mean()
        self.data["d"] = self.data["k"].ewm(com=self.m2 - 1, adjust=False).mean()
        self.data["j"] = 3 * self.data["k"] - 2 * self.data["d"]
    
    def generate_signals(self) -> pd.Series:
        signals = pd.Series(0, index=self.data.index)
        
        k = self.data["k"]
        d = self.data["d"]
        
        # K 上穿 D 且在超卖区
        golden = (k > d) & (k.shift(1) <= d.shift(1)) & (k < self.oversold + 20)
        
        # K 下穿 D 且在超买区
        death = (k < d) & (k.shift(1) >= d.shift(1)) & (k > self.overbought - 20)
        
        signals[golden] = 1
        signals[death] = -1
        
        return signals


class KDJGoldenStrategy(BaseStrategy):
    """
    KDJ 金叉策略（不限制超买超卖区）
    
    买入：J < 0 后 K 上穿 D
    卖出：J > 100 后 K 下穿 D
    """
    
    def __init__(self, n: int = 9, m1: int = 3, m2: int = 3):
        super().__init__(name=f"KDJ_Golden({n})")
        self.n = n
        self.m1 = m1
        self.m2 = m2
    
    def prepare_data(self):
        high = self.data["high"]
        low = self.data["low"]
        close = self.data["close"]
        
        lowest_low = low.rolling(window=self.n).min()
        highest_high = high.rolling(window=self.n).max()
        rsv = (close - lowest_low) / (highest_high - lowest_low) * 100
        rsv = rsv.fillna(50)
        
        self.data["k"] = rsv.ewm(com=self.m1 - 1, adjust=False).mean()
        self.data["d"] = self.data["k"].ewm(com=self.m2 - 1, adjust=False).mean()
        self.data["j"] = 3 * self.data["k"] - 2 * self.data["d"]
        
        # 标记 J 值状态
        self.data["j_oversold"] = (self.data["j"] < 0).rolling(5).max()  # 最近5天J<0过
        self.data["j_overbought"] = (self.data["j"] > 100).rolling(5).max()
    
    def generate_signals(self) -> pd.Series:
        signals = pd.Series(0, index=self.data.index)
        
        k = self.data["k"]
        d = self.data["d"]
        
        # K 上穿 D 且最近 J 值曾经 < 0
        golden = (k > d) & (k.shift(1) <= d.shift(1)) & (self.data["j_oversold"] == 1)
        
        # K 下穿 D 且最近 J 值曾经 > 100
        death = (k < d) & (k.shift(1) >= d.shift(1)) & (self.data["j_overbought"] == 1)
        
        signals[golden] = 1
        signals[death] = -1
        
        return signals
