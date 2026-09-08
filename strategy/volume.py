"""
量价策略
"""
import pandas as pd
import numpy as np
from .base import BaseStrategy


class VolumeBreakthroughStrategy(BaseStrategy):
    """
    放量突破策略
    
    价格突破 + 成交量放大 = 有效突破
    """
    
    def __init__(self, price_period: int = 20, volume_mult: float = 1.5):
        """
        Args:
            price_period: 价格突破周期
            volume_mult: 成交量放大倍数
        """
        super().__init__(name=f"VolBreak({price_period},{volume_mult}x)")
        self.price_period = price_period
        self.volume_mult = volume_mult
    
    def prepare_data(self):
        high = self.data["high"]
        close = self.data["close"]
        volume = self.data["volume"]
        
        self.data["price_high"] = high.rolling(self.price_period).max().shift(1)
        self.data["vol_ma"] = volume.rolling(self.price_period).mean()
        self.data["ma20"] = close.rolling(20).mean()
    
    def generate_signals(self) -> pd.Series:
        signals = pd.Series(0, index=self.data.index)
        
        close = self.data["close"]
        volume = self.data["volume"]
        price_high = self.data["price_high"]
        vol_ma = self.data["vol_ma"]
        ma20 = self.data["ma20"]
        
        # 价格突破 + 放量
        buy_signal = (
            (close > price_high) & 
            (volume > vol_ma * self.volume_mult)
        )
        
        # 缩量跌破均线
        sell_signal = (
            (close < ma20) & 
            (volume < vol_ma * 0.8)
        )
        
        signals[buy_signal] = 1
        signals[sell_signal] = -1
        
        return signals


class OBVStrategy(BaseStrategy):
    """
    OBV（能量潮）策略
    
    OBV 领先于价格，OBV 突破新高预示价格将上涨
    """
    
    def __init__(self, period: int = 20):
        super().__init__(name=f"OBV({period})")
        self.period = period
    
    def prepare_data(self):
        close = self.data["close"]
        volume = self.data["volume"]
        
        # 计算 OBV
        direction = np.sign(close.diff())
        direction.iloc[0] = 0
        self.data["obv"] = (direction * volume).cumsum()
        
        # OBV 均线
        self.data["obv_ma"] = self.data["obv"].rolling(self.period).mean()
        
        # OBV 创新高
        self.data["obv_high"] = self.data["obv"].rolling(self.period).max()
        
        # 价格新高
        self.data["price_high"] = close.rolling(self.period).max()
        
        self.data["ma20"] = close.rolling(20).mean()
    
    def generate_signals(self) -> pd.Series:
        signals = pd.Series(0, index=self.data.index)
        
        close = self.data["close"]
        obv = self.data["obv"]
        obv_ma = self.data["obv_ma"]
        obv_high = self.data["obv_high"]
        ma20 = self.data["ma20"]
        
        # OBV 突破新高 + OBV 在均线上方 + 价格在均线上方
        buy_signal = (
            (obv >= obv_high) & 
            (obv > obv_ma) & 
            (close > ma20)
        )
        
        # OBV 跌破均线
        sell_signal = obv < obv_ma * 0.95
        
        signals[buy_signal] = 1
        signals[sell_signal] = -1
        
        return signals


class VolumeProfileStrategy(BaseStrategy):
    """
    成交量分布策略
    
    在高成交量区域（支撑/阻力位）附近交易
    """
    
    def __init__(self, lookback: int = 60):
        super().__init__(name=f"VolumeProfile({lookback})")
        self.lookback = lookback
    
    def prepare_data(self):
        close = self.data["close"]
        volume = self.data["volume"]
        
        # 成交量加权平均价（VWAP 近似）
        self.data["vwap"] = (close * volume).rolling(self.lookback).sum() / volume.rolling(self.lookback).sum()
        
        # 价格相对 VWAP 的位置
        self.data["vwap_dist"] = (close - self.data["vwap"]) / self.data["vwap"]
        
        self.data["ma20"] = close.rolling(20).mean()
    
    def generate_signals(self) -> pd.Series:
        signals = pd.Series(0, index=self.data.index)
        
        close = self.data["close"]
        vwap = self.data["vwap"]
        vwap_dist = self.data["vwap_dist"]
        ma20 = self.data["ma20"]
        
        # 价格在 VWAP 附近向上突破
        buy_signal = (
            (vwap_dist > 0) & 
            (vwap_dist < 0.03) &  # 刚刚突破
            (close > ma20)
        )
        
        # 跌破 VWAP 较多
        sell_signal = vwap_dist < -0.03
        
        signals[buy_signal] = 1
        signals[sell_signal] = -1
        
        return signals


class ShrinkingVolumeStrategy(BaseStrategy):
    """
    缩量调整买入策略
    
    上涨趋势中，缩量回调是买入机会
    """
    
    def __init__(self, trend_period: int = 60, pullback_days: int = 5):
        super().__init__(name=f"ShrinkPullback({pullback_days}d)")
        self.trend_period = trend_period
        self.pullback_days = pullback_days
    
    def prepare_data(self):
        close = self.data["close"]
        volume = self.data["volume"]
        
        # 长期趋势
        self.data["ma60"] = close.rolling(self.trend_period).mean()
        
        # 短期均线
        self.data["ma10"] = close.rolling(10).mean()
        
        # 成交量均值
        self.data["vol_ma"] = volume.rolling(20).mean()
        
        # 最近N日是否缩量
        self.data["shrinking"] = volume.rolling(self.pullback_days).mean() < self.data["vol_ma"] * 0.7
        
        # 最近N日是否回调
        self.data["pullback"] = close < close.rolling(self.pullback_days).max()
    
    def generate_signals(self) -> pd.Series:
        signals = pd.Series(0, index=self.data.index)
        
        close = self.data["close"]
        ma60 = self.data["ma60"]
        ma10 = self.data["ma10"]
        shrinking = self.data["shrinking"]
        
        # 上升趋势 + 缩量回调到短期均线 + 价格开始反弹
        buy_signal = (
            (close > ma60) &                    # 上升趋势
            (shrinking) &                        # 缩量
            (close > ma10) &                     # 站上短期均线
            (close > close.shift(1))             # 今日上涨
        )
        
        # 跌破长期均线
        sell_signal = close < ma60 * 0.97
        
        signals[buy_signal] = 1
        signals[sell_signal] = -1
        
        return signals
