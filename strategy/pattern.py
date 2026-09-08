"""
形态识别策略
"""
import pandas as pd
import numpy as np
from .base import BaseStrategy


class CandlePatternStrategy(BaseStrategy):
    """
    K线形态策略
    
    识别常见的看涨/看跌K线形态
    """
    
    def __init__(self):
        super().__init__(name="CandlePattern")
    
    def prepare_data(self):
        open_p = self.data["open"]
        high = self.data["high"]
        low = self.data["low"]
        close = self.data["close"]
        
        # 实体大小
        body = abs(close - open_p)
        body_pct = body / open_p
        
        # 上影线
        upper_shadow = high - pd.concat([open_p, close], axis=1).max(axis=1)
        
        # 下影线
        lower_shadow = pd.concat([open_p, close], axis=1).min(axis=1) - low
        
        # 锤子线（下影线长，实体小，在底部）
        self.data["hammer"] = (
            (lower_shadow > body * 2) &
            (upper_shadow < body * 0.5) &
            (body_pct < 0.02)
        )
        
        # 倒锤子（上影线长，实体小）
        self.data["inv_hammer"] = (
            (upper_shadow > body * 2) &
            (lower_shadow < body * 0.5) &
            (body_pct < 0.02)
        )
        
        # 吞没形态（今日实体完全包含昨日实体）
        prev_body_high = pd.concat([open_p.shift(1), close.shift(1)], axis=1).max(axis=1)
        prev_body_low = pd.concat([open_p.shift(1), close.shift(1)], axis=1).min(axis=1)
        curr_body_high = pd.concat([open_p, close], axis=1).max(axis=1)
        curr_body_low = pd.concat([open_p, close], axis=1).min(axis=1)
        
        # 看涨吞没
        self.data["bullish_engulf"] = (
            (close > open_p) &                    # 今日阳线
            (close.shift(1) < open_p.shift(1)) &  # 昨日阴线
            (curr_body_high > prev_body_high) &   # 今日实体上沿高于昨日
            (curr_body_low < prev_body_low)       # 今日实体下沿低于昨日
        )
        
        # 早晨之星（三K线形态）
        # 第一天大阴线，第二天小实体，第三天大阳线
        big_down = (close.shift(2) < open_p.shift(2)) & (body_pct.shift(2) > 0.02)
        small_body = body_pct.shift(1) < 0.01
        big_up = (close > open_p) & (body_pct > 0.02) & (close > (open_p.shift(2) + close.shift(2)) / 2)
        
        self.data["morning_star"] = big_down & small_body & big_up
        
        self.data["ma20"] = close.rolling(20).mean()
    
    def generate_signals(self) -> pd.Series:
        signals = pd.Series(0, index=self.data.index)
        
        close = self.data["close"]
        ma20 = self.data["ma20"]
        
        # 看涨形态 + 站上均线
        buy_signal = (
            (self.data["hammer"] | self.data["bullish_engulf"] | self.data["morning_star"]) &
            (close > ma20 * 0.98)  # 接近或在均线上方
        )
        
        # 跌破均线
        sell_signal = close < ma20 * 0.95
        
        signals[buy_signal] = 1
        signals[sell_signal] = -1
        
        return signals


class DoubleBottomStrategy(BaseStrategy):
    """
    双底形态策略
    
    识别 W 底形态
    """
    
    def __init__(self, lookback: int = 60, tolerance: float = 0.03):
        """
        Args:
            lookback: 回看周期
            tolerance: 两个底部价格的容差
        """
        super().__init__(name=f"DoubleBottom({lookback})")
        self.lookback = lookback
        self.tolerance = tolerance
    
    def prepare_data(self):
        close = self.data["close"]
        low = self.data["low"]
        
        # 滚动最低价
        self.data["rolling_low"] = low.rolling(self.lookback).min()
        
        # 价格相对最低价的位置
        self.data["from_low"] = (close - self.data["rolling_low"]) / self.data["rolling_low"]
        
        # 中间高点
        self.data["mid_high"] = close.rolling(self.lookback // 2).max()
        
        self.data["ma20"] = close.rolling(20).mean()
    
    def generate_signals(self) -> pd.Series:
        signals = pd.Series(0, index=self.data.index)
        
        close = self.data["close"]
        rolling_low = self.data["rolling_low"]
        from_low = self.data["from_low"]
        mid_high = self.data["mid_high"]
        ma20 = self.data["ma20"]
        
        # 简化的双底判断：
        # 1. 最近创过新低
        # 2. 现在反弹了一定幅度
        # 3. 突破中间高点
        
        buy_signal = (
            (from_low > 0.05) &                    # 从低点反弹超过5%
            (from_low < 0.15) &                    # 但还没涨太多
            (close > mid_high * 0.98) &            # 接近或突破中间高点
            (close > ma20)                         # 站上均线
        )
        
        sell_signal = close < ma20 * 0.95
        
        signals[buy_signal] = 1
        signals[sell_signal] = -1
        
        return signals


class BreakoutRetestStrategy(BaseStrategy):
    """
    突破回踩策略
    
    突破后回踩不破，确认突破有效
    """
    
    def __init__(self, breakout_period: int = 20, retest_days: int = 5):
        super().__init__(name=f"BreakoutRetest({breakout_period})")
        self.breakout_period = breakout_period
        self.retest_days = retest_days
    
    def prepare_data(self):
        high = self.data["high"]
        low = self.data["low"]
        close = self.data["close"]
        
        # 突破位
        self.data["resistance"] = high.rolling(self.breakout_period).max().shift(1)
        
        # 最近N日最低价
        self.data["recent_low"] = low.rolling(self.retest_days).min()
        
        # 是否曾经突破
        self.data["was_above"] = (close > self.data["resistance"]).rolling(self.retest_days).max()
        
        self.data["ma20"] = close.rolling(20).mean()
    
    def generate_signals(self) -> pd.Series:
        signals = pd.Series(0, index=self.data.index)
        
        close = self.data["close"]
        resistance = self.data["resistance"]
        recent_low = self.data["recent_low"]
        was_above = self.data["was_above"]
        ma20 = self.data["ma20"]
        
        # 曾经突破 + 回踩不破 + 现在再次站上
        buy_signal = (
            (was_above == 1) &                     # 最近突破过
            (recent_low >= resistance * 0.98) &    # 回踩没跌破太多
            (close > resistance) &                  # 现在又站上去了
            (close > ma20)
        )
        
        sell_signal = close < resistance * 0.95
        
        signals[buy_signal] = 1
        signals[sell_signal] = -1
        
        return signals
