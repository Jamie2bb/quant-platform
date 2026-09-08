"""
MACD 策略
"""
import pandas as pd
import numpy as np
from .base import BaseStrategy


class MACDStrategy(BaseStrategy):
    """
    MACD 金叉死叉策略
    
    买入：DIF 上穿 DEA（金叉）
    卖出：DIF 下穿 DEA（死叉）
    """
    
    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        super().__init__(name=f"MACD({fast},{slow},{signal})")
        self.fast = fast
        self.slow = slow
        self.signal = signal
    
    def prepare_data(self):
        close = self.data["close"]
        
        # 计算 EMA
        ema_fast = close.ewm(span=self.fast, adjust=False).mean()
        ema_slow = close.ewm(span=self.slow, adjust=False).mean()
        
        # DIF = 快线 - 慢线
        self.data["dif"] = ema_fast - ema_slow
        
        # DEA = DIF 的 EMA
        self.data["dea"] = self.data["dif"].ewm(span=self.signal, adjust=False).mean()
        
        # MACD 柱 = (DIF - DEA) * 2
        self.data["macd"] = (self.data["dif"] - self.data["dea"]) * 2
    
    def generate_signals(self) -> pd.Series:
        signals = pd.Series(0, index=self.data.index)
        
        dif = self.data["dif"]
        dea = self.data["dea"]
        
        # 金叉：DIF 上穿 DEA
        golden = (dif > dea) & (dif.shift(1) <= dea.shift(1))
        
        # 死叉：DIF 下穿 DEA
        death = (dif < dea) & (dif.shift(1) >= dea.shift(1))
        
        signals[golden] = 1
        signals[death] = -1
        
        return signals


class MACDDivergenceStrategy(BaseStrategy):
    """
    MACD 背离策略
    
    底背离买入：价格创新低，但 MACD 不创新低
    顶背离卖出：价格创新高，但 MACD 不创新高
    """
    
    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9, lookback: int = 20):
        super().__init__(name=f"MACD_Divergence({lookback})")
        self.fast = fast
        self.slow = slow
        self.signal = signal
        self.lookback = lookback
    
    def prepare_data(self):
        close = self.data["close"]
        
        ema_fast = close.ewm(span=self.fast, adjust=False).mean()
        ema_slow = close.ewm(span=self.slow, adjust=False).mean()
        
        self.data["dif"] = ema_fast - ema_slow
        self.data["dea"] = self.data["dif"].ewm(span=self.signal, adjust=False).mean()
        self.data["macd"] = (self.data["dif"] - self.data["dea"]) * 2
        
        # 计算滚动最低/最高
        self.data["price_low"] = close.rolling(self.lookback).min()
        self.data["price_high"] = close.rolling(self.lookback).max()
        self.data["macd_low"] = self.data["macd"].rolling(self.lookback).min()
        self.data["macd_high"] = self.data["macd"].rolling(self.lookback).max()
    
    def generate_signals(self) -> pd.Series:
        signals = pd.Series(0, index=self.data.index)
        
        close = self.data["close"]
        macd = self.data["macd"]
        
        # 底背离：价格创新低，MACD 没创新低
        price_new_low = close <= self.data["price_low"]
        macd_higher_low = macd > self.data["macd_low"]
        bottom_divergence = price_new_low & macd_higher_low & (macd > macd.shift(1))
        
        # 顶背离：价格创新高，MACD 没创新高
        price_new_high = close >= self.data["price_high"]
        macd_lower_high = macd < self.data["macd_high"]
        top_divergence = price_new_high & macd_lower_high & (macd < macd.shift(1))
        
        signals[bottom_divergence] = 1
        signals[top_divergence] = -1
        
        return signals
