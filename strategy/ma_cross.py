"""
均线交叉策略
"""
import pandas as pd
from .base import BaseStrategy


class MACrossStrategy(BaseStrategy):
    """
    双均线交叉策略
    
    买入条件：短期均线上穿长期均线（金叉）
    卖出条件：短期均线下穿长期均线（死叉）
    """
    
    def __init__(self, short_period: int = 5, long_period: int = 20):
        super().__init__(name=f"MA({short_period},{long_period})")
        self.short_period = short_period
        self.long_period = long_period
    
    def prepare_data(self):
        """计算均线"""
        self.data["ma_short"] = self.data["close"].rolling(window=self.short_period).mean()
        self.data["ma_long"] = self.data["close"].rolling(window=self.long_period).mean()
    
    def generate_signals(self) -> pd.Series:
        """
        生成交易信号
        
        金叉买入，死叉卖出
        """
        signals = pd.Series(0, index=self.data.index)
        
        # 计算均线位置关系
        ma_short = self.data["ma_short"]
        ma_long = self.data["ma_long"]
        
        # 金叉：短均线从下方穿越长均线
        golden_cross = (ma_short > ma_long) & (ma_short.shift(1) <= ma_long.shift(1))
        
        # 死叉：短均线从上方穿越长均线
        death_cross = (ma_short < ma_long) & (ma_short.shift(1) >= ma_long.shift(1))
        
        signals[golden_cross] = 1   # 买入信号
        signals[death_cross] = -1   # 卖出信号
        
        return signals


class TripleMAStrategy(BaseStrategy):
    """
    三均线策略
    
    使用短、中、长三条均线
    买入：短>中>长 且 短线刚上穿中线
    卖出：短<中 或 中<长
    """
    
    def __init__(self, short: int = 5, mid: int = 10, long: int = 20):
        super().__init__(name=f"TripleMA({short},{mid},{long})")
        self.short = short
        self.mid = mid
        self.long = long
    
    def prepare_data(self):
        self.data["ma_short"] = self.data["close"].rolling(window=self.short).mean()
        self.data["ma_mid"] = self.data["close"].rolling(window=self.mid).mean()
        self.data["ma_long"] = self.data["close"].rolling(window=self.long).mean()
    
    def generate_signals(self) -> pd.Series:
        signals = pd.Series(0, index=self.data.index)
        
        ma_s = self.data["ma_short"]
        ma_m = self.data["ma_mid"]
        ma_l = self.data["ma_long"]
        
        # 多头排列且短线刚上穿中线
        bullish = (ma_s > ma_m) & (ma_m > ma_l)
        cross_up = (ma_s > ma_m) & (ma_s.shift(1) <= ma_m.shift(1))
        
        buy_signal = bullish & cross_up
        
        # 短线下穿中线卖出
        sell_signal = (ma_s < ma_m) & (ma_s.shift(1) >= ma_m.shift(1))
        
        signals[buy_signal] = 1
        signals[sell_signal] = -1
        
        return signals
