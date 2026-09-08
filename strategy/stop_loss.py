"""
止盈止损策略
"""
import pandas as pd
import numpy as np
from .base import BaseStrategy


class TrailingStopStrategy(BaseStrategy):
    """
    移动止损策略
    
    入场后，止损线跟随价格上移，但不下移
    锁定利润的同时让利润奔跑
    """
    
    def __init__(self, entry_period: int = 20, trail_pct: float = 0.08):
        """
        Args:
            entry_period: 入场突破周期
            trail_pct: 移动止损比例（从最高点回撤X%止损）
        """
        super().__init__(name=f"TrailingStop({trail_pct:.0%})")
        self.entry_period = entry_period
        self.trail_pct = trail_pct
    
    def prepare_data(self):
        high = self.data["high"]
        close = self.data["close"]
        
        self.data["entry_high"] = high.rolling(self.entry_period).max().shift(1)
        self.data["ma20"] = close.rolling(20).mean()
    
    def generate_signals(self) -> pd.Series:
        signals = pd.Series(0, index=self.data.index)
        
        close = self.data["close"]
        entry_high = self.data["entry_high"]
        ma20 = self.data["ma20"]
        
        in_position = False
        highest_since_entry = 0
        
        for i in range(1, len(close)):
            if not in_position:
                # 入场条件：突破N日高点
                if close.iloc[i] > entry_high.iloc[i] and close.iloc[i] > ma20.iloc[i]:
                    signals.iloc[i] = 1
                    in_position = True
                    highest_since_entry = close.iloc[i]
            else:
                # 更新持仓最高价
                highest_since_entry = max(highest_since_entry, close.iloc[i])
                
                # 移动止损
                stop_price = highest_since_entry * (1 - self.trail_pct)
                
                if close.iloc[i] < stop_price:
                    signals.iloc[i] = -1
                    in_position = False
        
        return signals


class FixedRatioStopStrategy(BaseStrategy):
    """
    固定比例止盈止损策略
    
    入场后设置固定的止盈止损比例
    """
    
    def __init__(self, entry_period: int = 20, stop_loss: float = 0.05, take_profit: float = 0.15):
        """
        Args:
            entry_period: 入场突破周期
            stop_loss: 止损比例
            take_profit: 止盈比例
        """
        super().__init__(name=f"FixedRatio(SL{stop_loss:.0%},TP{take_profit:.0%})")
        self.entry_period = entry_period
        self.stop_loss = stop_loss
        self.take_profit = take_profit
    
    def prepare_data(self):
        high = self.data["high"]
        close = self.data["close"]
        
        self.data["entry_high"] = high.rolling(self.entry_period).max().shift(1)
        self.data["ma20"] = close.rolling(20).mean()
    
    def generate_signals(self) -> pd.Series:
        signals = pd.Series(0, index=self.data.index)
        
        close = self.data["close"]
        entry_high = self.data["entry_high"]
        ma20 = self.data["ma20"]
        
        in_position = False
        entry_price = 0
        
        for i in range(1, len(close)):
            if not in_position:
                # 入场
                if close.iloc[i] > entry_high.iloc[i] and close.iloc[i] > ma20.iloc[i]:
                    signals.iloc[i] = 1
                    in_position = True
                    entry_price = close.iloc[i]
            else:
                current_price = close.iloc[i]
                pnl_pct = (current_price - entry_price) / entry_price
                
                # 止损或止盈
                if pnl_pct <= -self.stop_loss or pnl_pct >= self.take_profit:
                    signals.iloc[i] = -1
                    in_position = False
        
        return signals


class ATRStopStrategy(BaseStrategy):
    """
    ATR 止损策略
    
    用 ATR（真实波幅）动态设置止损
    波动大时止损宽，波动小时止损紧
    """
    
    def __init__(self, entry_period: int = 20, atr_mult: float = 2.0):
        """
        Args:
            entry_period: 入场周期
            atr_mult: ATR 倍数（止损 = 入场价 - ATR * mult）
        """
        super().__init__(name=f"ATRStop({atr_mult}x)")
        self.entry_period = entry_period
        self.atr_mult = atr_mult
    
    def prepare_data(self):
        high = self.data["high"]
        low = self.data["low"]
        close = self.data["close"]
        
        # ATR
        tr = pd.concat([
            high - low,
            abs(high - close.shift(1)),
            abs(low - close.shift(1))
        ], axis=1).max(axis=1)
        self.data["atr"] = tr.rolling(14).mean()
        
        # 入场
        self.data["entry_high"] = high.rolling(self.entry_period).max().shift(1)
        self.data["ma20"] = close.rolling(20).mean()
    
    def generate_signals(self) -> pd.Series:
        signals = pd.Series(0, index=self.data.index)
        
        close = self.data["close"]
        atr = self.data["atr"]
        entry_high = self.data["entry_high"]
        ma20 = self.data["ma20"]
        
        in_position = False
        entry_price = 0
        entry_atr = 0
        
        for i in range(1, len(close)):
            if not in_position:
                if close.iloc[i] > entry_high.iloc[i] and close.iloc[i] > ma20.iloc[i]:
                    signals.iloc[i] = 1
                    in_position = True
                    entry_price = close.iloc[i]
                    entry_atr = atr.iloc[i]
            else:
                stop_price = entry_price - self.atr_mult * entry_atr
                
                if close.iloc[i] < stop_price:
                    signals.iloc[i] = -1
                    in_position = False
        
        return signals


class TimeStopStrategy(BaseStrategy):
    """
    时间止损策略
    
    持仓超过N天未达目标就平仓
    避免资金长期占用
    """
    
    def __init__(self, entry_period: int = 20, max_hold_days: int = 20, min_profit: float = 0.05):
        """
        Args:
            entry_period: 入场周期
            max_hold_days: 最大持仓天数
            min_profit: 最低盈利目标
        """
        super().__init__(name=f"TimeStop({max_hold_days}d)")
        self.entry_period = entry_period
        self.max_hold_days = max_hold_days
        self.min_profit = min_profit
    
    def prepare_data(self):
        high = self.data["high"]
        close = self.data["close"]
        
        self.data["entry_high"] = high.rolling(self.entry_period).max().shift(1)
        self.data["ma20"] = close.rolling(20).mean()
    
    def generate_signals(self) -> pd.Series:
        signals = pd.Series(0, index=self.data.index)
        
        close = self.data["close"]
        entry_high = self.data["entry_high"]
        ma20 = self.data["ma20"]
        
        in_position = False
        entry_price = 0
        hold_days = 0
        
        for i in range(1, len(close)):
            if not in_position:
                if close.iloc[i] > entry_high.iloc[i] and close.iloc[i] > ma20.iloc[i]:
                    signals.iloc[i] = 1
                    in_position = True
                    entry_price = close.iloc[i]
                    hold_days = 0
            else:
                hold_days += 1
                pnl_pct = (close.iloc[i] - entry_price) / entry_price
                
                # 达到目标止盈
                if pnl_pct >= self.min_profit:
                    signals.iloc[i] = -1
                    in_position = False
                # 超时且未盈利就平仓
                elif hold_days >= self.max_hold_days and pnl_pct < self.min_profit:
                    signals.iloc[i] = -1
                    in_position = False
                # 亏损超过8%止损
                elif pnl_pct < -0.08:
                    signals.iloc[i] = -1
                    in_position = False
        
        return signals
