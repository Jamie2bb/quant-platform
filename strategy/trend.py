"""
趋势跟踪策略
"""
import pandas as pd
import numpy as np
from .base import BaseStrategy


class TrendFollowingStrategy(BaseStrategy):
    """
    趋势跟踪策略（海龟交易法改良版）
    
    入场：突破N日高点
    出场：跌破M日低点 或 ATR止损
    """
    
    def __init__(self, entry_period: int = 20, exit_period: int = 10, atr_stop: float = 2.0):
        super().__init__(name=f"TrendFollow({entry_period},{atr_stop}ATR)")
        self.entry_period = entry_period
        self.exit_period = exit_period
        self.atr_stop = atr_stop
    
    def prepare_data(self):
        high = self.data["high"]
        low = self.data["low"]
        close = self.data["close"]
        
        # 入场通道
        self.data["entry_high"] = high.rolling(self.entry_period).max().shift(1)
        
        # 出场通道
        self.data["exit_low"] = low.rolling(self.exit_period).min().shift(1)
        
        # ATR
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        self.data["atr"] = tr.rolling(14).mean()
        
        # 趋势过滤：只在上升趋势中做多
        self.data["ma50"] = close.rolling(50).mean()
    
    def generate_signals(self) -> pd.Series:
        signals = pd.Series(0, index=self.data.index)
        
        close = self.data["close"]
        entry_high = self.data["entry_high"]
        exit_low = self.data["exit_low"]
        ma50 = self.data["ma50"]
        
        # 买入：突破N日高点 且 在上升趋势中
        buy_signal = (close > entry_high) & (close > ma50)
        
        # 卖出：跌破M日低点
        sell_signal = close < exit_low
        
        signals[buy_signal] = 1
        signals[sell_signal] = -1
        
        return signals


class DualThrustStrategy(BaseStrategy):
    """
    Dual Thrust 策略（经典日内/短线策略）
    
    根据前N日的波动范围设置上下轨
    突破上轨买入，跌破下轨卖出
    """
    
    def __init__(self, lookback: int = 4, k1: float = 0.5, k2: float = 0.5):
        super().__init__(name=f"DualThrust({lookback},{k1})")
        self.lookback = lookback
        self.k1 = k1  # 上轨系数
        self.k2 = k2  # 下轨系数
    
    def prepare_data(self):
        high = self.data["high"]
        low = self.data["low"]
        close = self.data["close"]
        open_price = self.data["open"]
        
        # 计算 Range
        hh = high.rolling(self.lookback).max()  # N日最高
        lc = close.rolling(self.lookback).min() # N日最低收盘
        hc = close.rolling(self.lookback).max() # N日最高收盘
        ll = low.rolling(self.lookback).min()   # N日最低
        
        range1 = hh - lc
        range2 = hc - ll
        range_val = pd.concat([range1, range2], axis=1).max(axis=1)
        
        # 上下轨
        self.data["upper"] = open_price + self.k1 * range_val.shift(1)
        self.data["lower"] = open_price - self.k2 * range_val.shift(1)
    
    def generate_signals(self) -> pd.Series:
        signals = pd.Series(0, index=self.data.index)
        
        close = self.data["close"]
        upper = self.data["upper"]
        lower = self.data["lower"]
        
        # 突破上轨买入
        buy_signal = close > upper
        
        # 跌破下轨卖出
        sell_signal = close < lower
        
        signals[buy_signal] = 1
        signals[sell_signal] = -1
        
        return signals


class AdaptiveTrendStrategy(BaseStrategy):
    """
    自适应趋势策略
    
    根据市场波动自动调整参数
    高波动 = 宽止损
    低波动 = 紧止损
    """
    
    def __init__(self, base_period: int = 20):
        super().__init__(name=f"AdaptiveTrend({base_period})")
        self.base_period = base_period
    
    def prepare_data(self):
        close = self.data["close"]
        high = self.data["high"]
        low = self.data["low"]
        
        # 波动率（用于自适应）
        volatility = close.pct_change().rolling(20).std()
        vol_percentile = volatility.rolling(60).apply(lambda x: pd.Series(x).rank(pct=True).iloc[-1])
        
        # 自适应周期：高波动用长周期，低波动用短周期
        adaptive_mult = 1 + vol_percentile  # 1-2 倍
        
        # 使用固定周期的通道（简化版）
        self.data["upper"] = high.rolling(self.base_period).max().shift(1)
        self.data["lower"] = low.rolling(self.base_period).min().shift(1)
        
        # ATR 用于止损
        tr = pd.concat([high - low, abs(high - close.shift(1)), abs(low - close.shift(1))], axis=1).max(axis=1)
        self.data["atr"] = tr.rolling(14).mean()
        
        # 自适应止损倍数
        self.data["stop_mult"] = 1.5 + vol_percentile  # 1.5-2.5 倍 ATR
        
        # 趋势方向
        self.data["ma"] = close.rolling(self.base_period).mean()
    
    def generate_signals(self) -> pd.Series:
        signals = pd.Series(0, index=self.data.index)
        
        close = self.data["close"]
        upper = self.data["upper"]
        lower = self.data["lower"]
        ma = self.data["ma"]
        
        # 突破上轨 且 在均线上方 = 买入
        buy_signal = (close > upper) & (close > ma)
        
        # 跌破下轨 或 跌破均线 = 卖出
        sell_signal = (close < lower) | (close < ma * 0.95)
        
        signals[buy_signal] = 1
        signals[sell_signal] = -1
        
        return signals
