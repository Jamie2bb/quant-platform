"""
仓位管理模块 - 参考 Backtrader Sizers
提供多种仓位计算方法
"""
import pandas as pd
import numpy as np
from abc import ABC, abstractmethod
from typing import Optional


class BaseSizer(ABC):
    """仓位管理基类"""
    
    def __init__(self):
        self.broker = None  # 关联的 broker
    
    def set_broker(self, broker):
        """设置 broker 引用"""
        self.broker = broker
    
    @abstractmethod
    def get_size(self, price: float, data: pd.DataFrame = None) -> int:
        """
        计算应该买入的股数
        
        Args:
            price: 当前价格
            data: 行情数据（用于计算波动率等）
        
        Returns:
            买入股数（100的整数倍）
        """
        pass
    
    def _round_to_lot(self, shares: float, lot_size: int = 100) -> int:
        """取整到最小交易单位"""
        return int(shares // lot_size) * lot_size


class FixedSizer(BaseSizer):
    """
    固定股数
    
    每次买入固定数量的股票
    """
    
    def __init__(self, size: int = 100):
        super().__init__()
        self.size = size
    
    def get_size(self, price: float, data: pd.DataFrame = None) -> int:
        return self._round_to_lot(self.size)


class FixedAmountSizer(BaseSizer):
    """
    固定金额
    
    每次买入固定金额的股票
    """
    
    def __init__(self, amount: float = 10000):
        super().__init__()
        self.amount = amount
    
    def get_size(self, price: float, data: pd.DataFrame = None) -> int:
        if price <= 0:
            return 0
        shares = self.amount / price
        return self._round_to_lot(shares)


class PercentSizer(BaseSizer):
    """
    资金百分比
    
    每次使用账户可用资金的固定百分比
    """
    
    def __init__(self, percent: float = 0.1):
        """
        Args:
            percent: 资金占比，如 0.1 表示 10%
        """
        super().__init__()
        self.percent = min(1.0, max(0.01, percent))
    
    def get_size(self, price: float, data: pd.DataFrame = None) -> int:
        if self.broker is None or price <= 0:
            return 0
        
        available = self.broker.get_cash()
        amount = available * self.percent
        shares = amount / price
        return self._round_to_lot(shares)


class AllInSizer(BaseSizer):
    """
    全仓买入
    
    使用所有可用资金
    """
    
    def __init__(self, reserve: float = 0):
        """
        Args:
            reserve: 保留资金
        """
        super().__init__()
        self.reserve = reserve
    
    def get_size(self, price: float, data: pd.DataFrame = None) -> int:
        if self.broker is None or price <= 0:
            return 0
        
        available = self.broker.get_cash() - self.reserve
        if available <= 0:
            return 0
        
        shares = available / price
        return self._round_to_lot(shares)


class RiskPercentSizer(BaseSizer):
    """
    风险百分比仓位
    
    根据止损点和风险承受比例计算仓位
    经典的资金管理方法
    
    仓位 = (账户资金 × 风险百分比) / (买入价 - 止损价)
    """
    
    def __init__(self, risk_percent: float = 0.02, stop_loss_pct: float = 0.05):
        """
        Args:
            risk_percent: 单笔交易最大风险占总资金比例，如 0.02 表示 2%
            stop_loss_pct: 止损百分比，如 0.05 表示 5%
        """
        super().__init__()
        self.risk_percent = risk_percent
        self.stop_loss_pct = stop_loss_pct
    
    def get_size(self, price: float, data: pd.DataFrame = None) -> int:
        if self.broker is None or price <= 0:
            return 0
        
        equity = self.broker.get_value()
        risk_amount = equity * self.risk_percent
        
        # 每股风险 = 买入价 × 止损百分比
        risk_per_share = price * self.stop_loss_pct
        
        if risk_per_share <= 0:
            return 0
        
        shares = risk_amount / risk_per_share
        return self._round_to_lot(shares)


class ATRSizer(BaseSizer):
    """
    ATR 波动率仓位
    
    根据 ATR 动态调整仓位，波动大时减少仓位
    这是海龟交易法的核心仓位管理方法
    
    仓位 = (账户资金 × 风险百分比) / (ATR × ATR倍数)
    """
    
    def __init__(self, risk_percent: float = 0.01, atr_period: int = 14, atr_mult: float = 2.0):
        """
        Args:
            risk_percent: 单笔风险占比
            atr_period: ATR 计算周期
            atr_mult: ATR 倍数（用于计算止损距离）
        """
        super().__init__()
        self.risk_percent = risk_percent
        self.atr_period = atr_period
        self.atr_mult = atr_mult
    
    def get_size(self, price: float, data: pd.DataFrame = None) -> int:
        if self.broker is None or price <= 0 or data is None:
            return 0
        
        # 计算 ATR
        if len(data) < self.atr_period:
            return 0
        
        high = data["high"].iloc[-self.atr_period:]
        low = data["low"].iloc[-self.atr_period:]
        close = data["close"].iloc[-self.atr_period:]
        
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.mean()
        
        if atr <= 0:
            return 0
        
        equity = self.broker.get_value()
        risk_amount = equity * self.risk_percent
        
        # 每股风险 = ATR × 倍数
        risk_per_share = atr * self.atr_mult
        
        shares = risk_amount / risk_per_share
        return self._round_to_lot(shares)


class KellySizer(BaseSizer):
    """
    凯利公式仓位
    
    基于历史胜率和盈亏比计算最优仓位
    
    Kelly% = W - (1-W)/R
    W = 胜率
    R = 盈亏比（平均盈利/平均亏损）
    """
    
    def __init__(self, win_rate: float = 0.5, profit_loss_ratio: float = 1.5, 
                 fraction: float = 0.5, max_position: float = 0.25):
        """
        Args:
            win_rate: 历史胜率
            profit_loss_ratio: 盈亏比
            fraction: 凯利分数（建议用半凯利 0.5）
            max_position: 最大仓位比例
        """
        super().__init__()
        self.win_rate = win_rate
        self.profit_loss_ratio = profit_loss_ratio
        self.fraction = fraction
        self.max_position = max_position
    
    def get_size(self, price: float, data: pd.DataFrame = None) -> int:
        if self.broker is None or price <= 0:
            return 0
        
        # 凯利公式
        kelly = self.win_rate - (1 - self.win_rate) / self.profit_loss_ratio
        
        # 使用分数凯利，并限制最大仓位
        position_pct = min(kelly * self.fraction, self.max_position)
        position_pct = max(0, position_pct)  # 不能为负
        
        equity = self.broker.get_value()
        amount = equity * position_pct
        
        shares = amount / price
        return self._round_to_lot(shares)


class PyramidSizer(BaseSizer):
    """
    金字塔加仓
    
    随着盈利增加逐步加仓，但每次加仓量递减
    """
    
    def __init__(self, base_percent: float = 0.1, scale_factor: float = 0.5, max_positions: int = 4):
        """
        Args:
            base_percent: 首次建仓比例
            scale_factor: 加仓缩减系数
            max_positions: 最大加仓次数
        """
        super().__init__()
        self.base_percent = base_percent
        self.scale_factor = scale_factor
        self.max_positions = max_positions
        self.current_position_count = 0
    
    def get_size(self, price: float, data: pd.DataFrame = None) -> int:
        if self.broker is None or price <= 0:
            return 0
        
        if self.current_position_count >= self.max_positions:
            return 0
        
        # 计算当前仓位比例
        position_pct = self.base_percent * (self.scale_factor ** self.current_position_count)
        
        equity = self.broker.get_value()
        amount = equity * position_pct
        
        shares = amount / price
        return self._round_to_lot(shares)
    
    def add_position(self):
        """记录加仓"""
        self.current_position_count += 1
    
    def reset(self):
        """重置（平仓后调用）"""
        self.current_position_count = 0


class VolatilityTargetSizer(BaseSizer):
    """
    目标波动率仓位
    
    调整仓位使组合波动率保持在目标水平
    """
    
    def __init__(self, target_volatility: float = 0.15, lookback: int = 20):
        """
        Args:
            target_volatility: 目标年化波动率
            lookback: 波动率计算回看周期
        """
        super().__init__()
        self.target_volatility = target_volatility
        self.lookback = lookback
    
    def get_size(self, price: float, data: pd.DataFrame = None) -> int:
        if self.broker is None or price <= 0 or data is None:
            return 0
        
        if len(data) < self.lookback:
            return 0
        
        # 计算历史波动率
        returns = data["close"].pct_change().dropna().iloc[-self.lookback:]
        daily_vol = returns.std()
        annual_vol = daily_vol * np.sqrt(252)
        
        if annual_vol <= 0:
            return 0
        
        # 波动率调整系数
        vol_scalar = self.target_volatility / annual_vol
        vol_scalar = min(2.0, max(0.1, vol_scalar))  # 限制在 0.1-2.0 之间
        
        equity = self.broker.get_value()
        amount = equity * vol_scalar
        
        shares = amount / price
        return self._round_to_lot(shares)


# 仓位管理器工厂
def create_sizer(sizer_type: str, **kwargs) -> BaseSizer:
    """
    创建仓位管理器
    
    Args:
        sizer_type: 类型名称
        **kwargs: 参数
    
    Returns:
        BaseSizer 实例
    """
    sizers = {
        "fixed": FixedSizer,
        "fixed_amount": FixedAmountSizer,
        "percent": PercentSizer,
        "all_in": AllInSizer,
        "risk_percent": RiskPercentSizer,
        "atr": ATRSizer,
        "kelly": KellySizer,
        "pyramid": PyramidSizer,
        "volatility_target": VolatilityTargetSizer,
    }
    
    sizer_class = sizers.get(sizer_type.lower())
    if sizer_class is None:
        raise ValueError(f"Unknown sizer type: {sizer_type}")
    
    return sizer_class(**kwargs)
