"""
多因子策略
"""
import pandas as pd
import numpy as np
from .base import BaseStrategy


class MultiFactorStrategy(BaseStrategy):
    """
    多因子综合评分策略
    
    结合多个技术指标进行综合打分，分数高则买入
    """
    
    def __init__(self, score_threshold: float = 0.6):
        """
        Args:
            score_threshold: 买入阈值（0-1），分数超过此值买入
        """
        super().__init__(name=f"MultiFactor({score_threshold})")
        self.score_threshold = score_threshold
    
    def prepare_data(self):
        close = self.data["close"]
        high = self.data["high"]
        low = self.data["low"]
        volume = self.data["volume"]
        
        # 因子1: 趋势因子（价格在均线上方）
        ma20 = close.rolling(20).mean()
        ma60 = close.rolling(60).mean()
        self.data["trend_score"] = ((close > ma20).astype(int) + (close > ma60).astype(int) + (ma20 > ma60).astype(int)) / 3
        
        # 因子2: 动量因子（近期涨幅）
        ret_5 = close.pct_change(5)
        ret_20 = close.pct_change(20)
        # 归一化到 0-1
        self.data["momentum_score"] = (ret_5.rank(pct=True) + ret_20.rank(pct=True)) / 2
        
        # 因子3: 波动因子（低波动得分高）
        volatility = close.pct_change().rolling(20).std()
        self.data["volatility_score"] = 1 - volatility.rank(pct=True)
        
        # 因子4: 成交量因子（放量得分高）
        vol_ma = volume.rolling(20).mean()
        vol_ratio = volume / vol_ma
        self.data["volume_score"] = vol_ratio.clip(0, 3) / 3  # 限制在0-1
        
        # 因子5: RSI因子（超卖区得分高）
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        # RSI 30-70 正常，<30 超卖得分高，>70 超买得分低
        self.data["rsi_score"] = 1 - (rsi / 100)
        
        # 综合得分（等权重）
        self.data["total_score"] = (
            self.data["trend_score"] * 0.25 +
            self.data["momentum_score"] * 0.25 +
            self.data["volatility_score"] * 0.15 +
            self.data["volume_score"] * 0.15 +
            self.data["rsi_score"] * 0.20
        )
    
    def generate_signals(self) -> pd.Series:
        signals = pd.Series(0, index=self.data.index)
        
        score = self.data["total_score"]
        
        # 分数超过阈值且上升，买入
        buy_signal = (score > self.score_threshold) & (score > score.shift(1))
        
        # 分数低于阈值且下降，卖出
        sell_signal = (score < self.score_threshold * 0.7) & (score < score.shift(1))
        
        signals[buy_signal] = 1
        signals[sell_signal] = -1
        
        return signals


class ValueMomentumStrategy(BaseStrategy):
    """
    价值+动量双因子策略
    
    结合估值因子和动量因子
    低估值 + 强动量 = 买入
    """
    
    def __init__(self, momentum_period: int = 20, ma_period: int = 60):
        super().__init__(name=f"ValueMomentum({momentum_period})")
        self.momentum_period = momentum_period
        self.ma_period = ma_period
    
    def prepare_data(self):
        close = self.data["close"]
        
        # 动量因子：N日涨幅
        self.data["momentum"] = close.pct_change(self.momentum_period)
        
        # 价值因子：价格相对长期均线的偏离（越低越便宜）
        ma_long = close.rolling(self.ma_period).mean()
        self.data["value"] = (ma_long - close) / ma_long  # 正值表示低于均线
        
        # 趋势确认
        self.data["ma20"] = close.rolling(20).mean()
    
    def generate_signals(self) -> pd.Series:
        signals = pd.Series(0, index=self.data.index)
        
        momentum = self.data["momentum"]
        value = self.data["value"]
        close = self.data["close"]
        ma20 = self.data["ma20"]
        
        # 买入：动量为正 + 价格低于长期均线 + 站上短期均线
        buy_signal = (momentum > 0.05) & (value > 0) & (close > ma20)
        
        # 卖出：动量转负 或 跌破短期均线
        sell_signal = (momentum < -0.05) | (close < ma20 * 0.95)
        
        signals[buy_signal] = 1
        signals[sell_signal] = -1
        
        return signals


class QualityMomentumStrategy(BaseStrategy):
    """
    质量+动量策略
    
    用价格行为推断"质量"：
    - 回撤小
    - 上涨平稳
    - 成交量稳定
    """
    
    def __init__(self, lookback: int = 60):
        super().__init__(name=f"QualityMomentum({lookback})")
        self.lookback = lookback
    
    def prepare_data(self):
        close = self.data["close"]
        volume = self.data["volume"]
        
        # 动量
        self.data["return"] = close.pct_change(self.lookback)
        
        # 质量1：最大回撤（小回撤 = 高质量）
        rolling_max = close.rolling(self.lookback).max()
        drawdown = (close - rolling_max) / rolling_max
        self.data["max_dd"] = drawdown.rolling(self.lookback).min()
        
        # 质量2：波动率（低波动 = 高质量）
        self.data["volatility"] = close.pct_change().rolling(self.lookback).std()
        
        # 质量3：成交量稳定性（低波动 = 高质量）
        self.data["vol_stability"] = volume.rolling(self.lookback).std() / volume.rolling(self.lookback).mean()
        
        # 均线
        self.data["ma20"] = close.rolling(20).mean()
    
    def generate_signals(self) -> pd.Series:
        signals = pd.Series(0, index=self.data.index)
        
        ret = self.data["return"]
        max_dd = self.data["max_dd"]
        vol = self.data["volatility"]
        close = self.data["close"]
        ma20 = self.data["ma20"]
        
        # 买入：正收益 + 小回撤 + 低波动 + 站上均线
        buy_signal = (
            (ret > 0.1) &           # 涨幅超10%
            (max_dd > -0.15) &      # 回撤小于15%
            (vol < vol.rolling(60).mean()) &  # 波动低于平均
            (close > ma20)
        )
        
        # 卖出：跌破均线
        sell_signal = close < ma20 * 0.97
        
        signals[buy_signal] = 1
        signals[sell_signal] = -1
        
        return signals
