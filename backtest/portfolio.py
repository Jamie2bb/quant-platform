"""
组合回测引擎
支持多股票同时持仓、资金分配、组合再平衡
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.fetcher import DataFetcher
from strategy.base import BaseStrategy


@dataclass
class Position:
    """持仓"""
    symbol: str
    shares: int = 0
    cost_price: float = 0.0
    current_price: float = 0.0
    entry_date: str = ""
    
    @property
    def market_value(self) -> float:
        return self.shares * self.current_price
    
    @property
    def profit(self) -> float:
        return (self.current_price - self.cost_price) * self.shares
    
    @property
    def profit_pct(self) -> float:
        if self.cost_price == 0:
            return 0
        return (self.current_price - self.cost_price) / self.cost_price


@dataclass
class PortfolioState:
    """组合状态快照"""
    date: str
    cash: float
    positions: Dict[str, Position]
    total_value: float
    daily_return: float = 0.0


class PortfolioBacktest:
    """
    组合回测引擎
    
    支持：
    - 多股票同时回测
    - 等权重/市值加权/自定义权重
    - 定期再平衡
    - 组合绩效分析
    """
    
    def __init__(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str,
        initial_capital: float = 1000000,
        commission: float = 0.0003,
        slippage: float = 0.001
    ):
        self.symbols = symbols
        self.start_date = start_date
        self.end_date = end_date
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        
        # 状态
        self.cash = initial_capital
        self.positions: Dict[str, Position] = {}
        self.data: Dict[str, pd.DataFrame] = {}
        self.strategies: Dict[str, BaseStrategy] = {}
        self.weights: Dict[str, float] = {}
        
        # 记录
        self.history: List[PortfolioState] = []
        self.trades: List[Dict] = []
        self.rebalance_dates: List[str] = []
        
    def load_data(self):
        """加载所有股票数据"""
        print(f"加载 {len(self.symbols)} 只股票数据...")
        
        for symbol in self.symbols:
            try:
                df = DataFetcher.get_stock_daily(symbol, self.start_date, self.end_date)
                if len(df) > 0:
                    self.data[symbol] = df
                    print(f"  {symbol}: {len(df)} 条记录")
                else:
                    print(f"  {symbol}: 无数据")
            except Exception as e:
                print(f"  {symbol}: 获取失败 - {e}")
        
        print(f"成功加载 {len(self.data)} 只股票")
        
    def set_strategy(self, strategy: BaseStrategy, symbols: List[str] = None):
        """设置策略（可为特定股票设置不同策略）"""
        if symbols is None:
            symbols = self.symbols
        for symbol in symbols:
            self.strategies[symbol] = strategy
            
    def set_weights(self, weights: Dict[str, float] = None, method: str = "equal"):
        """
        设置权重
        
        Args:
            weights: 自定义权重 {symbol: weight}
            method: "equal"=等权重, "custom"=自定义
        """
        if weights:
            self.weights = weights
        elif method == "equal":
            n = len(self.symbols)
            self.weights = {s: 1.0/n for s in self.symbols}
        
        # 归一化
        total = sum(self.weights.values())
        self.weights = {k: v/total for k, v in self.weights.items()}
        
    def _get_price(self, symbol: str, date: str, price_type: str = "close") -> float:
        """获取指定日期的价格"""
        if symbol not in self.data:
            return 0
        df = self.data[symbol]
        if date in df.index:
            return df.loc[date, price_type]
        # 找最近的日期
        valid_dates = df.index[df.index <= date]
        if len(valid_dates) > 0:
            return df.loc[valid_dates[-1], price_type]
        return 0
    
    def _calculate_shares(self, symbol: str, amount: float, price: float) -> int:
        """计算可买股数（100股整数倍）"""
        if price <= 0:
            return 0
        shares = int(amount / price / 100) * 100
        return max(0, shares)
    
    def _execute_buy(self, symbol: str, shares: int, price: float, date: str):
        """执行买入"""
        if shares <= 0:
            return
            
        cost = shares * price * (1 + self.commission + self.slippage)
        
        if cost > self.cash:
            shares = self._calculate_shares(symbol, self.cash, price * (1 + self.commission + self.slippage))
            cost = shares * price * (1 + self.commission + self.slippage)
        
        if shares <= 0:
            return
            
        self.cash -= cost
        
        if symbol in self.positions:
            pos = self.positions[symbol]
            total_cost = pos.cost_price * pos.shares + price * shares
            total_shares = pos.shares + shares
            pos.cost_price = total_cost / total_shares
            pos.shares = total_shares
        else:
            self.positions[symbol] = Position(
                symbol=symbol,
                shares=shares,
                cost_price=price,
                current_price=price,
                entry_date=date
            )
        
        self.trades.append({
            "date": date,
            "symbol": symbol,
            "action": "buy",
            "shares": shares,
            "price": price,
            "amount": cost
        })
        
    def _execute_sell(self, symbol: str, shares: int, price: float, date: str):
        """执行卖出"""
        if symbol not in self.positions:
            return
            
        pos = self.positions[symbol]
        shares = min(shares, pos.shares)
        
        if shares <= 0:
            return
            
        revenue = shares * price * (1 - self.commission - self.slippage)
        self.cash += revenue
        
        pos.shares -= shares
        
        if pos.shares <= 0:
            del self.positions[symbol]
        
        self.trades.append({
            "date": date,
            "symbol": symbol,
            "action": "sell",
            "shares": shares,
            "price": price,
            "amount": revenue
        })
    
    def rebalance(self, date: str):
        """再平衡到目标权重"""
        total_value = self._get_total_value(date)
        
        # 计算目标持仓
        target_values = {s: total_value * w for s, w in self.weights.items()}
        
        # 先卖出超配的
        for symbol in list(self.positions.keys()):
            price = self._get_price(symbol, date)
            current_value = self.positions[symbol].shares * price if symbol in self.positions else 0
            target = target_values.get(symbol, 0)
            
            if current_value > target * 1.05:  # 超配5%以上才调整
                sell_value = current_value - target
                sell_shares = int(sell_value / price / 100) * 100
                if sell_shares > 0:
                    self._execute_sell(symbol, sell_shares, price, date)
        
        # 再买入低配的
        for symbol, target in target_values.items():
            price = self._get_price(symbol, date)
            if price <= 0:
                continue
            current_value = self.positions[symbol].shares * price if symbol in self.positions else 0
            
            if current_value < target * 0.95:  # 低配5%以上才调整
                buy_value = target - current_value
                buy_shares = self._calculate_shares(symbol, buy_value, price)
                if buy_shares > 0:
                    self._execute_buy(symbol, buy_shares, price, date)
        
        self.rebalance_dates.append(date)
    
    def _get_total_value(self, date: str) -> float:
        """计算组合总市值"""
        total = self.cash
        for symbol, pos in self.positions.items():
            price = self._get_price(symbol, date)
            pos.current_price = price
            total += pos.shares * price
        return total
    
    def _update_positions(self, date: str):
        """更新持仓价格"""
        for symbol, pos in self.positions.items():
            pos.current_price = self._get_price(symbol, date)
    
    def run(
        self,
        rebalance_freq: str = "monthly",  # "daily", "weekly", "monthly", "quarterly"
        use_strategy: bool = True
    ) -> "PortfolioResult":
        """
        运行组合回测
        
        Args:
            rebalance_freq: 再平衡频率
            use_strategy: 是否使用策略信号（否则只做再平衡）
        """
        if not self.data:
            self.load_data()
        
        if not self.weights:
            self.set_weights(method="equal")
        
        # 获取所有交易日
        all_dates = set()
        for df in self.data.values():
            all_dates.update(df.index.tolist())
        dates = sorted(all_dates)
        
        if len(dates) == 0:
            raise ValueError("无有效交易日数据")
        
        print(f"\n开始组合回测: {dates[0]} ~ {dates[-1]}")
        print(f"股票数量: {len(self.data)}, 初始资金: {self.initial_capital:,.0f}")
        print(f"再平衡频率: {rebalance_freq}")
        
        prev_value = self.initial_capital
        last_rebalance_month = None
        last_rebalance_week = None
        
        for i, date in enumerate(dates):
            # 更新持仓价格
            self._update_positions(date)
            
            # 判断是否需要再平衡
            need_rebalance = False
            dt = pd.to_datetime(date)
            
            if rebalance_freq == "daily":
                need_rebalance = True
            elif rebalance_freq == "weekly":
                week = dt.isocalendar()[1]
                if week != last_rebalance_week:
                    need_rebalance = True
                    last_rebalance_week = week
            elif rebalance_freq == "monthly":
                month = dt.month
                if month != last_rebalance_month:
                    need_rebalance = True
                    last_rebalance_month = month
            elif rebalance_freq == "quarterly":
                quarter = (dt.month - 1) // 3
                if quarter != getattr(self, '_last_quarter', None):
                    need_rebalance = True
                    self._last_quarter = quarter
            
            # 首日必须建仓
            if i == 0:
                need_rebalance = True
            
            # 使用策略信号
            if use_strategy and self.strategies:
                for symbol, strategy in self.strategies.items():
                    if symbol not in self.data:
                        continue
                    df = self.data[symbol]
                    if date not in df.index:
                        continue
                    
                    idx = df.index.get_loc(date)
                    if idx < strategy.min_periods:
                        continue
                    
                    signal = strategy.generate_signal(df, idx)
                    price = df.loc[date, "close"]
                    
                    if signal == 1 and symbol not in self.positions:
                        # 买入信号
                        target_value = self.cash * self.weights.get(symbol, 0.1)
                        shares = self._calculate_shares(symbol, target_value, price)
                        self._execute_buy(symbol, shares, price, date)
                    elif signal == -1 and symbol in self.positions:
                        # 卖出信号
                        self._execute_sell(symbol, self.positions[symbol].shares, price, date)
            
            # 再平衡
            elif need_rebalance:
                self.rebalance(date)
            
            # 记录状态
            total_value = self._get_total_value(date)
            daily_return = (total_value - prev_value) / prev_value if prev_value > 0 else 0
            
            self.history.append(PortfolioState(
                date=date,
                cash=self.cash,
                positions={s: Position(s, p.shares, p.cost_price, p.current_price, p.entry_date) 
                          for s, p in self.positions.items()},
                total_value=total_value,
                daily_return=daily_return
            ))
            
            prev_value = total_value
        
        return PortfolioResult(self)


class PortfolioResult:
    """组合回测结果"""
    
    def __init__(self, engine: PortfolioBacktest):
        self.engine = engine
        self.history = engine.history
        self.trades = engine.trades
        self.symbols = engine.symbols
        
        self._calculate_metrics()
    
    def _calculate_metrics(self):
        """计算绩效指标"""
        if not self.history:
            return
        
        values = [h.total_value for h in self.history]
        returns = [h.daily_return for h in self.history]
        
        self.initial_capital = self.engine.initial_capital
        self.final_value = values[-1]
        self.total_return = (self.final_value - self.initial_capital) / self.initial_capital
        
        # 年化收益
        days = len(values)
        self.annual_return = (1 + self.total_return) ** (252 / days) - 1 if days > 0 else 0
        
        # 最大回撤
        peak = values[0]
        max_dd = 0
        for v in values:
            if v > peak:
                peak = v
            dd = (peak - v) / peak
            max_dd = max(max_dd, dd)
        self.max_drawdown = max_dd
        
        # 夏普比率
        returns_arr = np.array(returns)
        if len(returns_arr) > 1 and returns_arr.std() > 0:
            self.sharpe_ratio = returns_arr.mean() / returns_arr.std() * np.sqrt(252)
        else:
            self.sharpe_ratio = 0
        
        # 卡玛比率
        self.calmar_ratio = self.annual_return / self.max_drawdown if self.max_drawdown > 0 else 0
        
        # 波动率
        self.volatility = returns_arr.std() * np.sqrt(252) if len(returns_arr) > 1 else 0
        
        # 交易统计
        self.total_trades = len(self.trades)
        self.rebalance_count = len(self.engine.rebalance_dates)
    
    def summary(self):
        """输出摘要"""
        print("\n" + "=" * 60)
        print("组合回测结果")
        print("=" * 60)
        
        print(f"\n【组合信息】")
        print(f"  股票数量:       {len(self.symbols)}")
        print(f"  股票列表:       {', '.join(self.symbols[:5])}{'...' if len(self.symbols) > 5 else ''}")
        
        print(f"\n【收益指标】")
        print(f"  初始资金:       {self.initial_capital:>15,.2f}")
        print(f"  最终市值:       {self.final_value:>15,.2f}")
        print(f"  总收益率:       {self.total_return:>14.2%}")
        print(f"  年化收益率:     {self.annual_return:>14.2%}")
        
        print(f"\n【风险指标】")
        print(f"  最大回撤:       {self.max_drawdown:>14.2%}")
        print(f"  夏普比率:       {self.sharpe_ratio:>14.2f}")
        print(f"  卡玛比率:       {self.calmar_ratio:>14.2f}")
        print(f"  年化波动率:     {self.volatility:>14.2%}")
        
        print(f"\n【交易统计】")
        print(f"  交易次数:       {self.total_trades:>14}")
        print(f"  再平衡次数:     {self.rebalance_count:>14}")
        
        print("=" * 60)
    
    def get_equity_curve(self) -> pd.DataFrame:
        """获取净值曲线"""
        data = {
            "date": [h.date for h in self.history],
            "total_value": [h.total_value for h in self.history],
            "cash": [h.cash for h in self.history],
            "daily_return": [h.daily_return for h in self.history]
        }
        df = pd.DataFrame(data)
        df["nav"] = df["total_value"] / self.initial_capital
        df["cumulative_return"] = df["nav"] - 1
        return df
    
    def get_trades_df(self) -> pd.DataFrame:
        """获取交易记录"""
        return pd.DataFrame(self.trades)
    
    def get_position_history(self) -> pd.DataFrame:
        """获取持仓历史"""
        records = []
        for h in self.history:
            for symbol, pos in h.positions.items():
                records.append({
                    "date": h.date,
                    "symbol": symbol,
                    "shares": pos.shares,
                    "cost_price": pos.cost_price,
                    "current_price": pos.current_price,
                    "market_value": pos.market_value,
                    "profit": pos.profit,
                    "profit_pct": pos.profit_pct
                })
        return pd.DataFrame(records)
    
    def plot(self, save_path: str = None):
        """绘制组合净值曲线"""
        import matplotlib.pyplot as plt
        import matplotlib
        matplotlib.use('Agg')
        
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
        plt.rcParams['axes.unicode_minus'] = False
        
        df = self.get_equity_curve()
        
        fig, axes = plt.subplots(2, 1, figsize=(14, 10))
        
        # 净值曲线
        ax1 = axes[0]
        ax1.plot(df["date"], df["nav"], label="组合净值", linewidth=2)
        ax1.axhline(y=1, color='gray', linestyle='--', alpha=0.5)
        ax1.set_title(f"组合回测 - {len(self.symbols)}只股票", fontsize=14)
        ax1.set_ylabel("净值")
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 回撤曲线
        ax2 = axes[1]
        peak = df["nav"].cummax()
        drawdown = (df["nav"] - peak) / peak
        ax2.fill_between(df["date"], drawdown, 0, alpha=0.3, color='red')
        ax2.set_title("回撤", fontsize=14)
        ax2.set_ylabel("回撤幅度")
        ax2.set_xlabel("日期")
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"图表已保存: {save_path}")
        
        plt.close()


# 便捷函数
def run_portfolio_backtest(
    symbols: List[str],
    start_date: str,
    end_date: str,
    initial_capital: float = 1000000,
    weights: Dict[str, float] = None,
    rebalance_freq: str = "monthly"
) -> PortfolioResult:
    """
    快速运行组合回测
    
    Args:
        symbols: 股票代码列表
        start_date: 开始日期
        end_date: 结束日期
        initial_capital: 初始资金
        weights: 权重（None则等权重）
        rebalance_freq: 再平衡频率
    """
    engine = PortfolioBacktest(
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        initial_capital=initial_capital
    )
    
    engine.load_data()
    engine.set_weights(weights)
    
    return engine.run(rebalance_freq=rebalance_freq, use_strategy=False)
