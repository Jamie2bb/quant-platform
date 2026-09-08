"""
网格交易策略
"""
import pandas as pd
import numpy as np
from .base import BaseStrategy


class GridStrategy(BaseStrategy):
    """
    网格交易策略
    
    在价格区间内设置多个网格，价格每下跌一格买入，每上涨一格卖出
    适合震荡行情
    """
    
    def __init__(self, grid_num: int = 10, grid_pct: float = 0.02):
        """
        Args:
            grid_num: 网格数量
            grid_pct: 每格涨跌幅（如 0.02 表示 2%）
        """
        super().__init__(name=f"Grid({grid_num},{grid_pct:.1%})")
        self.grid_num = grid_num
        self.grid_pct = grid_pct
        self.grids = []  # 网格价位
        self.holdings = []  # 各网格持仓状态
    
    def prepare_data(self):
        # 以第一天收盘价为基准设置网格
        base_price = self.data["close"].iloc[0]
        
        self.grids = []
        for i in range(-self.grid_num // 2, self.grid_num // 2 + 1):
            price = base_price * (1 + i * self.grid_pct)
            self.grids.append(price)
        
        self.grids.sort()
        self.holdings = [0] * len(self.grids)
        
        # 记录当前所在网格
        self.data["grid_level"] = 0
        for i, row in enumerate(self.data.itertuples()):
            close = row.close
            level = self._get_grid_level(close)
            self.data.iloc[i, self.data.columns.get_loc("grid_level")] = level
    
    def _get_grid_level(self, price: float) -> int:
        """获取价格所在的网格层级"""
        for i, grid_price in enumerate(self.grids):
            if price < grid_price:
                return i
        return len(self.grids)
    
    def generate_signals(self) -> pd.Series:
        signals = pd.Series(0, index=self.data.index)
        
        # 网格策略需要逐K线判断
        prev_level = self.data["grid_level"].iloc[0]
        
        for i in range(1, len(self.data)):
            curr_level = self.data["grid_level"].iloc[i]
            
            if curr_level < prev_level:
                # 价格下跌穿过网格，买入
                signals.iloc[i] = 1
            elif curr_level > prev_level:
                # 价格上涨穿过网格，卖出
                signals.iloc[i] = -1
            
            prev_level = curr_level
        
        return signals


class DynamicGridStrategy(BaseStrategy):
    """
    动态网格策略
    
    根据 ATR 动态调整网格间距
    """
    
    def __init__(self, atr_period: int = 14, atr_mult: float = 1.0):
        super().__init__(name=f"DynamicGrid(ATR{atr_period})")
        self.atr_period = atr_period
        self.atr_mult = atr_mult
    
    def prepare_data(self):
        high = self.data["high"]
        low = self.data["low"]
        close = self.data["close"]
        
        # 计算 ATR
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        self.data["atr"] = tr.rolling(window=self.atr_period).mean()
        
        # 计算动态网格线
        self.data["upper_grid"] = close + self.data["atr"] * self.atr_mult
        self.data["lower_grid"] = close - self.data["atr"] * self.atr_mult
    
    def generate_signals(self) -> pd.Series:
        signals = pd.Series(0, index=self.data.index)
        
        close = self.data["close"]
        
        # 价格触及下网格线买入
        buy_signal = close <= self.data["lower_grid"].shift(1)
        
        # 价格触及上网格线卖出
        sell_signal = close >= self.data["upper_grid"].shift(1)
        
        signals[buy_signal] = 1
        signals[sell_signal] = -1
        
        return signals


class MeanReversionStrategy(BaseStrategy):
    """
    均值回归策略
    
    价格偏离均线过多时反向操作
    """
    
    def __init__(self, ma_period: int = 20, deviation: float = 0.05):
        """
        Args:
            ma_period: 均线周期
            deviation: 偏离阈值（如 0.05 表示偏离 5%）
        """
        super().__init__(name=f"MeanReversion({ma_period},{deviation:.0%})")
        self.ma_period = ma_period
        self.deviation = deviation
    
    def prepare_data(self):
        self.data["ma"] = self.data["close"].rolling(self.ma_period).mean()
        self.data["deviation"] = (self.data["close"] - self.data["ma"]) / self.data["ma"]
    
    def generate_signals(self) -> pd.Series:
        signals = pd.Series(0, index=self.data.index)
        
        dev = self.data["deviation"]
        
        # 价格低于均线超过阈值，买入
        buy_signal = dev < -self.deviation
        
        # 价格高于均线超过阈值，卖出
        sell_signal = dev > self.deviation
        
        signals[buy_signal] = 1
        signals[sell_signal] = -1
        
        return signals
