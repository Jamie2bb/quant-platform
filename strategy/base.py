"""
策略基类
"""
from abc import ABC, abstractmethod
import pandas as pd
from typing import Optional


class BaseStrategy(ABC):
    """策略基类，所有策略必须继承此类"""
    
    def __init__(self, name: str = "BaseStrategy"):
        self.name = name
        self.data: Optional[pd.DataFrame] = None
        self.position = 0  # 当前持仓：0=空仓, 1=持仓
        
    def set_data(self, data: pd.DataFrame):
        """设置行情数据"""
        self.data = data.copy()
        self.prepare_data()
    
    def prepare_data(self):
        """
        数据预处理，计算策略需要的指标
        子类可重写此方法添加技术指标
        """
        pass
    
    @abstractmethod
    def generate_signals(self) -> pd.Series:
        """
        生成交易信号
        
        Returns:
            pd.Series: 信号序列
                1 = 买入信号
                -1 = 卖出信号
                0 = 无信号
        """
        pass
    
    def on_bar(self, idx: int, row: pd.Series) -> int:
        """
        逐K线处理（可选重写）
        
        Args:
            idx: 当前K线索引
            row: 当前K线数据
        
        Returns:
            int: 交易信号 (1=买入, -1=卖出, 0=持有)
        """
        return 0
    
    def __repr__(self):
        return f"{self.name}"
