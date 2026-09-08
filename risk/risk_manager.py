"""
风险管理模块 - 参考 VnPy 风控系统
提供完整的风险控制功能
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable
from enum import Enum


class RiskLevel(Enum):
    """风险等级"""
    LOW = "低风险"
    MEDIUM = "中风险"
    HIGH = "高风险"
    CRITICAL = "极高风险"


@dataclass
class RiskEvent:
    """风险事件"""
    timestamp: datetime
    level: RiskLevel
    type: str
    message: str
    value: float = 0.0
    threshold: float = 0.0


@dataclass
class RiskLimits:
    """风险限制参数"""
    # 单笔交易限制
    max_order_value: float = 100000  # 单笔最大金额
    max_position_pct: float = 0.25   # 单只股票最大仓位比例
    
    # 日内限制
    max_daily_trades: int = 50       # 日最大交易次数
    max_daily_loss: float = 0.05     # 日最大亏损比例
    max_daily_turnover: float = 2.0  # 日最大换手率
    
    # 总体限制
    max_total_positions: int = 10    # 最大持仓股票数
    max_drawdown: float = 0.20       # 最大回撤限制
    max_leverage: float = 1.0        # 最大杠杆
    
    # 时间限制
    no_trade_before: str = "09:30"   # 开盘后禁止交易时间
    no_trade_after: str = "14:55"    # 收盘前禁止交易时间
    
    # 价格限制
    max_slippage: float = 0.02       # 最大滑点容忍
    min_price: float = 1.0           # 最低股价限制
    max_price: float = 500.0         # 最高股价限制


class RiskManager:
    """
    风险管理器
    
    监控和控制交易风险
    """
    
    def __init__(self, limits: RiskLimits = None):
        self.limits = limits or RiskLimits()
        self.risk_events: List[RiskEvent] = []
        
        # 日内统计
        self.daily_trades = 0
        self.daily_pnl = 0.0
        self.daily_turnover = 0.0
        self.last_reset_date = None
        
        # 账户状态
        self.initial_equity = 0.0
        self.peak_equity = 0.0
        self.current_equity = 0.0
        
        # 持仓信息
        self.positions: Dict[str, float] = {}  # symbol -> value
        
        # 风险状态
        self.is_trading_allowed = True
        self.risk_level = RiskLevel.LOW
        
        # 回调函数
        self.on_risk_event: Optional[Callable[[RiskEvent], None]] = None
    
    def initialize(self, equity: float):
        """初始化账户"""
        self.initial_equity = equity
        self.peak_equity = equity
        self.current_equity = equity
    
    def update_equity(self, equity: float):
        """更新账户权益"""
        self.current_equity = equity
        self.peak_equity = max(self.peak_equity, equity)
        self._check_drawdown()
    
    def _reset_daily_stats(self):
        """重置日内统计"""
        today = datetime.now().date()
        if self.last_reset_date != today:
            self.daily_trades = 0
            self.daily_pnl = 0.0
            self.daily_turnover = 0.0
            self.last_reset_date = today
    
    def _add_risk_event(self, level: RiskLevel, event_type: str, 
                        message: str, value: float = 0, threshold: float = 0):
        """添加风险事件"""
        event = RiskEvent(
            timestamp=datetime.now(),
            level=level,
            type=event_type,
            message=message,
            value=value,
            threshold=threshold
        )
        self.risk_events.append(event)
        
        # 更新风险等级
        if level.value > self.risk_level.value:
            self.risk_level = level
        
        # 回调通知
        if self.on_risk_event:
            self.on_risk_event(event)
        
        return event
    
    def check_order(self, symbol: str, price: float, size: int, 
                    direction: str = "buy") -> tuple:
        """
        检查订单是否符合风控规则
        
        Returns:
            (is_allowed: bool, reason: str, adjusted_size: int)
        """
        self._reset_daily_stats()
        
        order_value = price * size
        
        # 1. 检查单笔金额
        if order_value > self.limits.max_order_value:
            self._add_risk_event(
                RiskLevel.MEDIUM, "ORDER_VALUE",
                f"单笔金额 {order_value:.0f} 超过限制 {self.limits.max_order_value:.0f}",
                order_value, self.limits.max_order_value
            )
            # 调整数量
            adjusted_size = int(self.limits.max_order_value / price / 100) * 100
            if adjusted_size <= 0:
                return False, "单笔金额超限，无法调整", 0
            return True, f"调整数量为 {adjusted_size}", adjusted_size
        
        # 2. 检查价格范围
        if price < self.limits.min_price:
            return False, f"股价 {price:.2f} 低于最低限制 {self.limits.min_price:.2f}", 0
        
        if price > self.limits.max_price:
            return False, f"股价 {price:.2f} 高于最高限制 {self.limits.max_price:.2f}", 0
        
        # 3. 检查日交易次数
        if self.daily_trades >= self.limits.max_daily_trades:
            self._add_risk_event(
                RiskLevel.HIGH, "DAILY_TRADES",
                f"日交易次数 {self.daily_trades} 达到上限",
                self.daily_trades, self.limits.max_daily_trades
            )
            return False, "日交易次数达到上限", 0
        
        # 4. 检查日亏损
        if self.current_equity > 0:
            daily_loss_pct = -self.daily_pnl / self.initial_equity
            if daily_loss_pct >= self.limits.max_daily_loss:
                self._add_risk_event(
                    RiskLevel.CRITICAL, "DAILY_LOSS",
                    f"日亏损 {daily_loss_pct:.2%} 超过限制",
                    daily_loss_pct, self.limits.max_daily_loss
                )
                self.is_trading_allowed = False
                return False, f"日亏损已达 {daily_loss_pct:.2%}，停止交易", 0
        
        # 5. 检查单只股票仓位
        if direction == "buy" and self.current_equity > 0:
            current_position = self.positions.get(symbol, 0)
            new_position = current_position + order_value
            position_pct = new_position / self.current_equity
            
            if position_pct > self.limits.max_position_pct:
                self._add_risk_event(
                    RiskLevel.MEDIUM, "POSITION_LIMIT",
                    f"{symbol} 仓位 {position_pct:.2%} 超过限制",
                    position_pct, self.limits.max_position_pct
                )
                # 调整数量
                allowed_value = self.current_equity * self.limits.max_position_pct - current_position
                adjusted_size = int(allowed_value / price / 100) * 100
                if adjusted_size <= 0:
                    return False, "仓位已满", 0
                return True, f"调整数量为 {adjusted_size}", adjusted_size
        
        # 6. 检查持仓数量
        if direction == "buy" and symbol not in self.positions:
            if len(self.positions) >= self.limits.max_total_positions:
                return False, f"持仓数量已达上限 {self.limits.max_total_positions}", 0
        
        return True, "通过风控检查", size
    
    def _check_drawdown(self):
        """检查回撤"""
        if self.peak_equity <= 0:
            return
        
        drawdown = (self.peak_equity - self.current_equity) / self.peak_equity
        
        if drawdown >= self.limits.max_drawdown:
            self._add_risk_event(
                RiskLevel.CRITICAL, "MAX_DRAWDOWN",
                f"回撤 {drawdown:.2%} 达到极限",
                drawdown, self.limits.max_drawdown
            )
            self.is_trading_allowed = False
        elif drawdown >= self.limits.max_drawdown * 0.8:
            self._add_risk_event(
                RiskLevel.HIGH, "DRAWDOWN_WARNING",
                f"回撤 {drawdown:.2%} 接近极限",
                drawdown, self.limits.max_drawdown
            )
    
    def record_trade(self, symbol: str, price: float, size: int, 
                     direction: str, pnl: float = 0):
        """记录交易"""
        self._reset_daily_stats()
        
        trade_value = price * size
        
        self.daily_trades += 1
        self.daily_pnl += pnl
        self.daily_turnover += trade_value / self.current_equity if self.current_equity > 0 else 0
        
        # 更新持仓
        if direction == "buy":
            self.positions[symbol] = self.positions.get(symbol, 0) + trade_value
        else:
            current = self.positions.get(symbol, 0)
            self.positions[symbol] = max(0, current - trade_value)
            if self.positions[symbol] == 0:
                del self.positions[symbol]
    
    def get_position_value(self, symbol: str) -> float:
        """获取持仓市值"""
        return self.positions.get(symbol, 0)
    
    def get_total_position_value(self) -> float:
        """获取总持仓市值"""
        return sum(self.positions.values())
    
    def get_available_capital(self) -> float:
        """获取可用资金"""
        return self.current_equity - self.get_total_position_value()
    
    def get_current_drawdown(self) -> float:
        """获取当前回撤"""
        if self.peak_equity <= 0:
            return 0
        return (self.peak_equity - self.current_equity) / self.peak_equity
    
    def get_risk_summary(self) -> dict:
        """获取风险摘要"""
        return {
            "risk_level": self.risk_level.value,
            "is_trading_allowed": self.is_trading_allowed,
            "current_drawdown": round(self.get_current_drawdown(), 4),
            "daily_trades": self.daily_trades,
            "daily_pnl": round(self.daily_pnl, 2),
            "daily_turnover": round(self.daily_turnover, 4),
            "total_positions": len(self.positions),
            "total_position_value": round(self.get_total_position_value(), 2),
            "available_capital": round(self.get_available_capital(), 2),
            "risk_events_count": len(self.risk_events)
        }
    
    def get_recent_events(self, count: int = 10) -> List[RiskEvent]:
        """获取最近的风险事件"""
        return self.risk_events[-count:]
    
    def reset_daily(self):
        """手动重置日内统计"""
        self.daily_trades = 0
        self.daily_pnl = 0.0
        self.daily_turnover = 0.0
        self.is_trading_allowed = True
    
    def reset_all(self):
        """重置所有状态"""
        self.reset_daily()
        self.risk_events.clear()
        self.positions.clear()
        self.risk_level = RiskLevel.LOW
        self.peak_equity = self.current_equity


class PositionRiskMonitor:
    """
    持仓风险监控
    
    监控单个持仓的风险指标
    """
    
    def __init__(self, symbol: str, entry_price: float, size: int):
        self.symbol = symbol
        self.entry_price = entry_price
        self.size = size
        self.entry_time = datetime.now()
        
        self.highest_price = entry_price
        self.lowest_price = entry_price
        self.current_price = entry_price
        
        # 止损止盈价
        self.stop_loss_price: Optional[float] = None
        self.take_profit_price: Optional[float] = None
        self.trailing_stop_pct: Optional[float] = None
    
    def update_price(self, price: float):
        """更新价格"""
        self.current_price = price
        self.highest_price = max(self.highest_price, price)
        self.lowest_price = min(self.lowest_price, price)
    
    def set_stop_loss(self, price: float = None, pct: float = None):
        """设置止损"""
        if price:
            self.stop_loss_price = price
        elif pct:
            self.stop_loss_price = self.entry_price * (1 - pct)
    
    def set_take_profit(self, price: float = None, pct: float = None):
        """设置止盈"""
        if price:
            self.take_profit_price = price
        elif pct:
            self.take_profit_price = self.entry_price * (1 + pct)
    
    def set_trailing_stop(self, pct: float):
        """设置移动止损"""
        self.trailing_stop_pct = pct
    
    def get_trailing_stop_price(self) -> Optional[float]:
        """获取移动止损价"""
        if self.trailing_stop_pct is None:
            return None
        return self.highest_price * (1 - self.trailing_stop_pct)
    
    def check_exit_signal(self) -> tuple:
        """
        检查是否触发退出信号
        
        Returns:
            (should_exit: bool, reason: str)
        """
        # 检查止损
        if self.stop_loss_price and self.current_price <= self.stop_loss_price:
            return True, "触发止损"
        
        # 检查移动止损
        trailing_stop = self.get_trailing_stop_price()
        if trailing_stop and self.current_price <= trailing_stop:
            return True, "触发移动止损"
        
        # 检查止盈
        if self.take_profit_price and self.current_price >= self.take_profit_price:
            return True, "触发止盈"
        
        return False, ""
    
    @property
    def unrealized_pnl(self) -> float:
        """未实现盈亏"""
        return (self.current_price - self.entry_price) * self.size
    
    @property
    def unrealized_pnl_pct(self) -> float:
        """未实现盈亏比例"""
        return (self.current_price - self.entry_price) / self.entry_price
    
    @property
    def max_favorable_excursion(self) -> float:
        """最大有利偏移 (MFE)"""
        return (self.highest_price - self.entry_price) / self.entry_price
    
    @property
    def max_adverse_excursion(self) -> float:
        """最大不利偏移 (MAE)"""
        return (self.entry_price - self.lowest_price) / self.entry_price
    
    @property
    def holding_days(self) -> int:
        """持仓天数"""
        return (datetime.now() - self.entry_time).days
    
    def get_status(self) -> dict:
        """获取持仓状态"""
        return {
            "symbol": self.symbol,
            "entry_price": self.entry_price,
            "current_price": self.current_price,
            "size": self.size,
            "unrealized_pnl": round(self.unrealized_pnl, 2),
            "unrealized_pnl_pct": round(self.unrealized_pnl_pct, 4),
            "mfe": round(self.max_favorable_excursion, 4),
            "mae": round(self.max_adverse_excursion, 4),
            "holding_days": self.holding_days,
            "stop_loss_price": self.stop_loss_price,
            "take_profit_price": self.take_profit_price,
            "trailing_stop_price": self.get_trailing_stop_price()
        }
