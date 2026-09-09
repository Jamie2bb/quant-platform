# -*- coding: utf-8 -*-
"""
仓位计算器 - 根据风险控制计算建仓数量
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dataclasses import dataclass
from typing import Optional
from .config import PositionRules


@dataclass
class PositionResult:
    """仓位计算结果"""
    symbol: str
    current_price: float
    stop_loss_price: float
    
    # 计算结果
    shares: int              # 建议买入股数
    amount: float            # 建议买入金额
    position_pct: float      # 占总资金比例
    max_loss: float          # 最大亏损金额
    max_loss_pct: float      # 最大亏损占总资金比例
    
    # 限制信息
    limit_reason: str = ""   # 如果有限制，说明原因


class PositionCalculator:
    """仓位计算器"""
    
    def __init__(self, total_capital: float = None):
        self.total_capital = total_capital or PositionRules.TOTAL_CAPITAL
        self.max_single_pct = PositionRules.MAX_SINGLE_PCT
        self.max_loss_per_trade = PositionRules.MAX_LOSS_PER_TRADE
    
    def calculate(self, 
                  current_price: float, 
                  stop_loss_price: float,
                  symbol: str = "") -> PositionResult:
        """
        根据止损价计算建仓数量
        
        核心逻辑：
        - 单笔交易最大亏损 = 总资金 × max_loss_per_trade
        - 每股亏损 = 买入价 - 止损价
        - 最大买入股数 = 单笔最大亏损 / 每股亏损
        - 同时受单只股票最大仓位限制
        
        Args:
            current_price: 当前价格（计划买入价）
            stop_loss_price: 止损价
            symbol: 股票代码（可选）
        
        Returns:
            PositionResult: 计算结果
        """
        if stop_loss_price >= current_price:
            raise ValueError("止损价必须低于当前价格")
        
        # 每股风险
        risk_per_share = current_price - stop_loss_price
        
        # 方法1：按风险控制计算
        max_risk = self.total_capital * self.max_loss_per_trade
        shares_by_risk = int(max_risk / risk_per_share / 100) * 100  # 取整到手
        
        # 方法2：按最大仓位限制计算
        max_position = self.total_capital * self.max_single_pct
        shares_by_position = int(max_position / current_price / 100) * 100
        
        # 取较小值
        shares = min(shares_by_risk, shares_by_position)
        
        # 确定限制原因
        limit_reason = ""
        if shares_by_risk < shares_by_position:
            limit_reason = f"受风险控制限制（单笔最大亏损 {self.max_loss_per_trade*100:.0f}%）"
        elif shares_by_position < shares_by_risk:
            limit_reason = f"受仓位限制（单只最大 {self.max_single_pct*100:.0f}%）"
        
        # 计算结果
        amount = shares * current_price
        position_pct = amount / self.total_capital
        max_loss = shares * risk_per_share
        max_loss_pct = max_loss / self.total_capital
        
        return PositionResult(
            symbol=symbol,
            current_price=current_price,
            stop_loss_price=stop_loss_price,
            shares=shares,
            amount=amount,
            position_pct=position_pct,
            max_loss=max_loss,
            max_loss_pct=max_loss_pct,
            limit_reason=limit_reason
        )
    
    def calculate_by_pct(self, 
                         current_price: float, 
                         stop_loss_pct: float,
                         symbol: str = "") -> PositionResult:
        """
        根据止损比例计算建仓数量
        
        Args:
            current_price: 当前价格
            stop_loss_pct: 止损比例，如 0.08 表示下跌 8% 止损
            symbol: 股票代码
        """
        stop_loss_price = current_price * (1 - stop_loss_pct)
        return self.calculate(current_price, stop_loss_price, symbol)
    
    def print_result(self, result: PositionResult):
        """打印计算结果"""
        print(f"\n{'='*50}")
        print(f"仓位计算结果" + (f" - {result.symbol}" if result.symbol else ""))
        print(f"{'='*50}")
        
        print(f"\n【输入参数】")
        print(f"  总资金:       ¥{self.total_capital:,.0f}")
        print(f"  买入价:       ¥{result.current_price:.2f}")
        print(f"  止损价:       ¥{result.stop_loss_price:.2f}")
        stop_pct = (result.current_price - result.stop_loss_price) / result.current_price * 100
        print(f"  止损幅度:     {stop_pct:.1f}%")
        
        print(f"\n【计算结果】")
        print(f"  建议买入:     {result.shares} 股 ({result.shares // 100} 手)")
        print(f"  买入金额:     ¥{result.amount:,.0f}")
        print(f"  仓位比例:     {result.position_pct * 100:.1f}%")
        print(f"  最大亏损:     ¥{result.max_loss:,.0f} ({result.max_loss_pct * 100:.2f}%)")
        
        if result.limit_reason:
            print(f"\n【限制说明】")
            print(f"  {result.limit_reason}")
        
        print(f"{'='*50}")


def calc_position(current_price: float, stop_loss_price: float, 
                  total_capital: float = None, symbol: str = "") -> PositionResult:
    """
    计算建仓数量（便捷函数）
    
    示例：
        result = calc_position(10.5, 9.5)  # 10.5元买入，9.5元止损
        print(f"建议买入: {result.shares} 股")
    """
    calc = PositionCalculator(total_capital)
    result = calc.calculate(current_price, stop_loss_price, symbol)
    calc.print_result(result)
    return result


def calc_position_by_pct(current_price: float, stop_loss_pct: float,
                         total_capital: float = None, symbol: str = "") -> PositionResult:
    """
    根据止损比例计算建仓数量（便捷函数）
    
    示例：
        result = calc_position_by_pct(10.5, 0.08)  # 10.5元买入，下跌8%止损
    """
    calc = PositionCalculator(total_capital)
    result = calc.calculate_by_pct(current_price, stop_loss_pct, symbol)
    calc.print_result(result)
    return result


if __name__ == "__main__":
    # 示例
    print("【示例1：指定止损价】")
    calc_position(10.5, 9.5, 100000, "000001")
    
    print("\n【示例2：指定止损比例 8%】")
    calc_position_by_pct(50.0, 0.08, 100000, "600519")
