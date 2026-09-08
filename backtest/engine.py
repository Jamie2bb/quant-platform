"""
回测引擎
"""
import pandas as pd
import numpy as np
from typing import Optional, List
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.fetcher import DataFetcher
from strategy.base import BaseStrategy
from backtest.result import BacktestResult, Trade


class BacktestEngine:
    """
    回测引擎
    
    支持：
    - 单股票回测
    - 手续费和滑点
    - 仓位管理
    """
    
    def __init__(self, symbol: str, start_date: str, end_date: str = None,
                 initial_capital: float = 100000,
                 commission: float = 0.0003,  # 手续费率 0.03%
                 slippage: float = 0.001,     # 滑点 0.1%
                 stamp_duty: float = 0.001):  # 印花税 0.1%（卖出时收取）
        """
        初始化回测引擎
        
        Args:
            symbol: 股票代码
            start_date: 开始日期 "YYYYMMDD"
            end_date: 结束日期，默认今天
            initial_capital: 初始资金
            commission: 手续费率（买卖都收）
            slippage: 滑点
            stamp_duty: 印花税（仅卖出时收）
        """
        self.symbol = symbol
        self.start_date = start_date
        self.end_date = end_date or datetime.now().strftime("%Y%m%d")
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        self.stamp_duty = stamp_duty
        
        self.strategy: Optional[BaseStrategy] = None
        self.data: Optional[pd.DataFrame] = None
        
    def set_strategy(self, strategy: BaseStrategy):
        """设置策略"""
        self.strategy = strategy
    
    def load_data(self):
        """加载数据"""
        print(f"正在加载 {self.symbol} 数据...")
        self.data = DataFetcher.get_stock_daily(
            self.symbol, self.start_date, self.end_date
        )
        print(f"加载完成，共 {len(self.data)} 条记录")
        print(f"时间范围: {self.data.index[0].strftime('%Y-%m-%d')} ~ {self.data.index[-1].strftime('%Y-%m-%d')}")
    
    def run(self) -> BacktestResult:
        """
        运行回测
        
        Returns:
            BacktestResult: 回测结果
        """
        if self.strategy is None:
            raise ValueError("请先设置策略: engine.set_strategy(strategy)")
        
        # 加载数据
        if self.data is None:
            self.load_data()
        
        # 将数据传给策略
        self.strategy.set_data(self.data)
        
        # 生成信号
        signals = self.strategy.generate_signals()
        
        # 模拟交易
        result = self._simulate(signals)
        
        return result
    
    def _simulate(self, signals: pd.Series) -> BacktestResult:
        """模拟交易"""
        data = self.data.copy()
        data["signal"] = signals
        
        # 初始化
        cash = self.initial_capital
        position = 0
        shares = 0
        entry_price = 0
        entry_date = None
        
        trades: List[Trade] = []
        equity_list = []
        returns_list = []
        
        prev_equity = self.initial_capital
        
        for date, row in data.iterrows():
            signal = row["signal"]
            close = row["close"]
            
            # 买入信号
            if signal == 1 and position == 0:
                # 计算可买股数（按手，1手=100股）
                buy_price = close * (1 + self.slippage)
                cost_per_share = buy_price * (1 + self.commission)
                max_shares = int(cash / cost_per_share / 100) * 100
                
                if max_shares >= 100:
                    shares = max_shares
                    total_cost = shares * buy_price * (1 + self.commission)
                    cash -= total_cost
                    position = 1
                    entry_price = buy_price
                    entry_date = date
            
            # 卖出信号
            elif signal == -1 and position == 1:
                sell_price = close * (1 - self.slippage)
                # 扣除手续费和印花税
                proceeds = shares * sell_price * (1 - self.commission - self.stamp_duty)
                cash += proceeds
                
                # 记录交易
                pnl = proceeds - shares * entry_price * (1 + self.commission)
                pnl_pct = (sell_price / entry_price - 1) - self.commission * 2 - self.stamp_duty
                hold_days = (date - entry_date).days
                
                trades.append(Trade(
                    entry_date=entry_date,
                    entry_price=entry_price,
                    exit_date=date,
                    exit_price=sell_price,
                    shares=shares,
                    pnl=pnl,
                    pnl_pct=pnl_pct,
                    hold_days=hold_days
                ))
                
                position = 0
                shares = 0
            
            # 计算当日净值
            if position == 1:
                equity = cash + shares * close
            else:
                equity = cash
            
            equity_list.append(equity)
            
            # 计算日收益率
            daily_return = (equity - prev_equity) / prev_equity if prev_equity > 0 else 0
            returns_list.append(daily_return)
            prev_equity = equity
        
        # 如果最后还有持仓，强制平仓
        if position == 1:
            last_date = data.index[-1]
            last_close = data.iloc[-1]["close"]
            sell_price = last_close * (1 - self.slippage)
            proceeds = shares * sell_price * (1 - self.commission - self.stamp_duty)
            
            pnl = proceeds - shares * entry_price * (1 + self.commission)
            pnl_pct = (sell_price / entry_price - 1) - self.commission * 2 - self.stamp_duty
            hold_days = (last_date - entry_date).days
            
            trades.append(Trade(
                entry_date=entry_date,
                entry_price=entry_price,
                exit_date=last_date,
                exit_price=sell_price,
                shares=shares,
                pnl=pnl,
                pnl_pct=pnl_pct,
                hold_days=hold_days
            ))
            
            cash += proceeds
            equity_list[-1] = cash
        
        data["equity"] = equity_list
        data["returns"] = returns_list
        
        return BacktestResult(
            data=data,
            trades=trades,
            initial_capital=self.initial_capital,
            strategy_name=f"{self.symbol} - {self.strategy.name}"
        )


class MultiStockBacktest:
    """
    多股票回测（组合回测）
    """
    
    def __init__(self, symbols: List[str], start_date: str, end_date: str = None,
                 initial_capital: float = 1000000):
        self.symbols = symbols
        self.start_date = start_date
        self.end_date = end_date
        self.initial_capital = initial_capital
        self.capital_per_stock = initial_capital / len(symbols)
        
        self.strategy: Optional[BaseStrategy] = None
        self.results: dict = {}
    
    def set_strategy(self, strategy_class, **kwargs):
        """设置策略类（所有股票使用相同策略）"""
        self.strategy_class = strategy_class
        self.strategy_kwargs = kwargs
    
    def run(self) -> dict:
        """运行回测"""
        for symbol in self.symbols:
            print(f"\n回测 {symbol}...")
            
            engine = BacktestEngine(
                symbol=symbol,
                start_date=self.start_date,
                end_date=self.end_date,
                initial_capital=self.capital_per_stock
            )
            
            strategy = self.strategy_class(**self.strategy_kwargs)
            engine.set_strategy(strategy)
            
            result = engine.run()
            self.results[symbol] = result
        
        return self.results
    
    def summary(self):
        """汇总所有股票的回测结果"""
        print("\n" + "="*60)
        print("多股票回测汇总")
        print("="*60)
        
        total_pnl = 0
        for symbol, result in self.results.items():
            pnl = result.final_capital - self.capital_per_stock
            total_pnl += pnl
            print(f"{symbol}: 收益率 {result.total_return:>8.2%}, "
                  f"最大回撤 {result.max_drawdown:>8.2%}, "
                  f"夏普 {result.sharpe_ratio:>6.2f}")
        
        total_return = total_pnl / self.initial_capital
        print("-"*60)
        print(f"组合总收益率: {total_return:.2%}")
        print(f"组合总盈亏: {total_pnl:,.2f}")
