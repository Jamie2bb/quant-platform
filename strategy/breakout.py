"""
突破策略
"""
import pandas as pd
import numpy as np
from .base import BaseStrategy


class BreakoutStrategy(BaseStrategy):
    """
    通道突破策略（海龟交易法变体）
    
    买入：价格突破N日最高价
    卖出：价格跌破M日最低价
    """
    
    def __init__(self, entry_period: int = 20, exit_period: int = 10):
        super().__init__(name=f"Breakout({entry_period},{exit_period})")
        self.entry_period = entry_period  # 入场周期
        self.exit_period = exit_period    # 出场周期
    
    def prepare_data(self):
        """计算通道上下轨"""
        # 入场通道：N日最高价
        self.data["entry_high"] = self.data["high"].rolling(self.entry_period).max().shift(1)
        
        # 出场通道：M日最低价
        self.data["exit_low"] = self.data["low"].rolling(self.exit_period).min().shift(1)
    
    def generate_signals(self) -> pd.Series:
        signals = pd.Series(0, index=self.data.index)
        
        # 突破N日最高价买入
        buy_signal = self.data["close"] > self.data["entry_high"]
        
        # 跌破M日最低价卖出
        sell_signal = self.data["close"] < self.data["exit_low"]
        
        signals[buy_signal] = 1
        signals[sell_signal] = -1
        
        return signals


class BollingerBreakoutStrategy(BaseStrategy):
    """
    布林带突破策略
    
    买入：价格突破上轨
    卖出：价格跌破中轨
    """
    
    def __init__(self, period: int = 20, std_dev: float = 2.0):
        super().__init__(name=f"Bollinger({period},{std_dev})")
        self.period = period
        self.std_dev = std_dev
    
    def prepare_data(self):
        """计算布林带"""
        self.data["bb_mid"] = self.data["close"].rolling(self.period).mean()
        self.data["bb_std"] = self.data["close"].rolling(self.period).std()
        self.data["bb_upper"] = self.data["bb_mid"] + self.std_dev * self.data["bb_std"]
        self.data["bb_lower"] = self.data["bb_mid"] - self.std_dev * self.data["bb_std"]
    
    def generate_signals(self) -> pd.Series:
        signals = pd.Series(0, index=self.data.index)
        
        # 突破上轨买入
        buy_signal = (
            (self.data["close"] > self.data["bb_upper"]) & 
            (self.data["close"].shift(1) <= self.data["bb_upper"].shift(1))
        )
        
        # 跌破中轨卖出
        sell_signal = (
            (self.data["close"] < self.data["bb_mid"]) & 
            (self.data["close"].shift(1) >= self.data["bb_mid"].shift(1))
        )
        
        signals[buy_signal] = 1
        signals[sell_signal] = -1
        
        return signals


class VolumeBreakoutStrategy(BaseStrategy):
    """
    放量突破策略
    
    买入：价格创N日新高 且 成交量放大M倍
    卖出：价格跌破均线
    """
    
    def __init__(self, price_period: int = 20, volume_mult: float = 2.0, ma_period: int = 10):
        super().__init__(name=f"VolumeBreakout({price_period})")
        self.price_period = price_period
        self.volume_mult = volume_mult
        self.ma_period = ma_period
    
    def prepare_data(self):
        # N日最高价
        self.data["highest"] = self.data["high"].rolling(self.price_period).max().shift(1)
        
        # 成交量均值
        self.data["vol_ma"] = self.data["volume"].rolling(self.price_period).mean()
        
        # 均线
        self.data["ma"] = self.data["close"].rolling(self.ma_period).mean()
    
    def generate_signals(self) -> pd.Series:
        signals = pd.Series(0, index=self.data.index)
        
        # 价格突破 + 放量
        buy_signal = (
            (self.data["close"] > self.data["highest"]) & 
            (self.data["volume"] > self.volume_mult * self.data["vol_ma"])
        )
        
        # 跌破均线卖出
        sell_signal = (
            (self.data["close"] < self.data["ma"]) & 
            (self.data["close"].shift(1) >= self.data["ma"].shift(1))
        )
        
        signals[buy_signal] = 1
        signals[sell_signal] = -1
        
        return signals
