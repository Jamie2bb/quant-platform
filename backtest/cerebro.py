"""
Cerebro 回测引擎 - 参考 Backtrader
整合策略、分析器、仓位管理、风控的完整回测系统
"""
import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Dict, Optional, Type
from dataclasses import dataclass, field

from .analyzers import AnalyzerSuite, TradeRecord
from .sizers import BaseSizer, PercentSizer, create_sizer


@dataclass
class BrokerConfig:
    """券商配置"""
    initial_cash: float = 100000
    commission: float = 0.0003  # 手续费率
    stamp_tax: float = 0.001   # 印花税（卖出）
    slippage: float = 0.001    # 滑点
    min_commission: float = 5   # 最低手续费


class Broker:
    """
    模拟券商
    
    管理账户资金、持仓、订单执行
    """
    
    def __init__(self, config: BrokerConfig = None):
        self.config = config or BrokerConfig()
        self.cash = self.config.initial_cash
        self.position = 0  # 持仓股数
        self.position_avg_price = 0  # 持仓均价
        self.trades: List[TradeRecord] = []
        self.current_trade: Optional[TradeRecord] = None
        
        # 历史记录
        self.equity_history: List[float] = []
        self.cash_history: List[float] = []
    
    def get_cash(self) -> float:
        """获取可用现金"""
        return self.cash
    
    def get_value(self, current_price: float = 0) -> float:
        """获取账户总价值"""
        return self.cash + self.position * current_price
    
    def get_position(self) -> int:
        """获取持仓"""
        return self.position
    
    def buy(self, price: float, size: int, date: datetime = None) -> bool:
        """
        买入
        
        Returns:
            是否成功
        """
        if size <= 0:
            return False
        
        # 考虑滑点
        exec_price = price * (1 + self.config.slippage)
        
        # 计算成本
        cost = exec_price * size
        commission = max(cost * self.config.commission, self.config.min_commission)
        total_cost = cost + commission
        
        # 检查资金
        if total_cost > self.cash:
            return False
        
        # 执行买入
        self.cash -= total_cost
        
        # 更新持仓均价
        if self.position > 0:
            total_value = self.position_avg_price * self.position + exec_price * size
            self.position += size
            self.position_avg_price = total_value / self.position
        else:
            self.position = size
            self.position_avg_price = exec_price
        
        # 记录交易
        self.current_trade = TradeRecord(
            entry_date=date or datetime.now(),
            entry_price=exec_price,
            size=size,
            direction="long"
        )
        
        return True
    
    def sell(self, price: float, size: int = None, date: datetime = None) -> bool:
        """
        卖出
        
        Args:
            size: 卖出股数，None 表示全部卖出
        """
        if self.position <= 0:
            return False
        
        size = size or self.position
        size = min(size, self.position)
        
        if size <= 0:
            return False
        
        # 考虑滑点
        exec_price = price * (1 - self.config.slippage)
        
        # 计算收入
        revenue = exec_price * size
        commission = max(revenue * self.config.commission, self.config.min_commission)
        stamp_tax = revenue * self.config.stamp_tax
        net_revenue = revenue - commission - stamp_tax
        
        # 执行卖出
        self.cash += net_revenue
        self.position -= size
        
        if self.position == 0:
            self.position_avg_price = 0
        
        # 完成交易记录
        if self.current_trade:
            self.current_trade.exit_date = date or datetime.now()
            self.current_trade.exit_price = exec_price
            self.current_trade.pnl = (exec_price - self.current_trade.entry_price) * size - commission - stamp_tax
            self.current_trade.pnl_pct = self.current_trade.pnl / (self.current_trade.entry_price * size)
            self.trades.append(self.current_trade)
            self.current_trade = None
        
        return True
    
    def update_history(self, current_price: float):
        """更新历史记录"""
        self.equity_history.append(self.get_value(current_price))
        self.cash_history.append(self.cash)
    
    def reset(self):
        """重置账户"""
        self.cash = self.config.initial_cash
        self.position = 0
        self.position_avg_price = 0
        self.trades.clear()
        self.current_trade = None
        self.equity_history.clear()
        self.cash_history.clear()


@dataclass
class CerebroResult:
    """回测结果"""
    data: pd.DataFrame
    trades: List[TradeRecord]
    metrics: dict
    
    # 基础指标
    initial_capital: float = 0
    final_capital: float = 0
    total_return: float = 0
    annual_return: float = 0
    max_drawdown: float = 0
    sharpe_ratio: float = 0
    calmar_ratio: float = 0
    win_rate: float = 0
    profit_factor: float = 0
    total_trades: int = 0
    avg_hold_days: float = 0
    
    def summary(self):
        """打印摘要"""
        print("\n" + "=" * 60)
        print("                   回测结果摘要")
        print("=" * 60)
        print(f"  初始资金:       ¥{self.initial_capital:,.2f}")
        print(f"  最终资金:       ¥{self.final_capital:,.2f}")
        print(f"  总收益率:       {self.total_return:.2%}")
        print(f"  年化收益率:     {self.annual_return:.2%}")
        print("-" * 60)
        print(f"  最大回撤:       {self.max_drawdown:.2%}")
        print(f"  夏普比率:       {self.sharpe_ratio:.2f}")
        print(f"  卡玛比率:       {self.calmar_ratio:.2f}")
        print("-" * 60)
        print(f"  交易次数:       {self.total_trades}")
        print(f"  胜率:           {self.win_rate:.2%}")
        print(f"  盈亏比:         {self.profit_factor:.2f}")
        print(f"  平均持仓:       {self.avg_hold_days:.1f} 天")
        print("=" * 60)
    
    def get_trades_df(self) -> pd.DataFrame:
        """获取交易明细 DataFrame"""
        if not self.trades:
            return pd.DataFrame()
        
        records = []
        for t in self.trades:
            records.append({
                "入场日期": t.entry_date,
                "入场价格": round(t.entry_price, 2),
                "出场日期": t.exit_date,
                "出场价格": round(t.exit_price, 2) if t.exit_price else None,
                "数量": t.size,
                "盈亏": round(t.pnl, 2),
                "收益率": f"{t.pnl_pct:.2%}",
                "持仓天数": t.bars_held
            })
        
        return pd.DataFrame(records)
    
    def plot(self):
        """绘制资金曲线"""
        try:
            import matplotlib.pyplot as plt
            
            fig, axes = plt.subplots(2, 1, figsize=(12, 8))
            
            # 资金曲线
            ax1 = axes[0]
            ax1.plot(self.data.index, self.data["equity"], label="策略资金")
            ax1.axhline(y=self.initial_capital, color='gray', linestyle='--', 
                       label=f'初始资金 ¥{self.initial_capital:,.0f}')
            ax1.set_title("资金曲线")
            ax1.set_ylabel("资金 (¥)")
            ax1.legend()
            ax1.grid(True, alpha=0.3)
            
            # 回撤曲线
            ax2 = axes[1]
            equity = self.data["equity"]
            rolling_max = equity.cummax()
            drawdown = (equity - rolling_max) / rolling_max
            ax2.fill_between(self.data.index, drawdown, 0, alpha=0.3, color='red')
            ax2.plot(self.data.index, drawdown, color='red', linewidth=0.5)
            ax2.set_title("回撤曲线")
            ax2.set_ylabel("回撤")
            ax2.grid(True, alpha=0.3)
            
            plt.tight_layout()
            plt.show()
            
        except ImportError:
            print("需要安装 matplotlib: pip install matplotlib")


class Cerebro:
    """
    Cerebro 回测大脑
    
    整合所有组件的核心引擎
    
    使用方式:
        cerebro = Cerebro()
        cerebro.add_data(data)
        cerebro.add_strategy(MyStrategy)
        cerebro.set_sizer("percent", percent=0.1)
        result = cerebro.run()
        result.summary()
    """
    
    def __init__(self, cash: float = 100000, commission: float = 0.0003):
        self.broker_config = BrokerConfig(
            initial_cash=cash,
            commission=commission
        )
        self.broker = Broker(self.broker_config)
        
        self.data: Optional[pd.DataFrame] = None
        self.strategy = None
        self.sizer: BaseSizer = PercentSizer(0.95)  # 默认 95% 仓位
        
        self.analyzers = AnalyzerSuite()
    
    def add_data(self, data: pd.DataFrame):
        """添加数据"""
        self.data = data.copy()
        return self
    
    def add_strategy(self, strategy):
        """添加策略"""
        self.strategy = strategy
        return self
    
    def set_sizer(self, sizer_type: str = "percent", **kwargs):
        """
        设置仓位管理器
        
        Args:
            sizer_type: fixed, fixed_amount, percent, all_in, risk_percent, atr, kelly
            **kwargs: 仓位管理器参数
        """
        self.sizer = create_sizer(sizer_type, **kwargs)
        return self
    
    def set_cash(self, cash: float):
        """设置初始资金"""
        self.broker_config.initial_cash = cash
        self.broker.cash = cash
        return self
    
    def set_commission(self, commission: float):
        """设置手续费率"""
        self.broker_config.commission = commission
        return self
    
    def run(self) -> CerebroResult:
        """
        运行回测
        
        Returns:
            CerebroResult: 回测结果
        """
        if self.data is None:
            raise ValueError("请先添加数据: cerebro.add_data(data)")
        
        if self.strategy is None:
            raise ValueError("请先添加策略: cerebro.add_strategy(strategy)")
        
        # 重置
        self.broker.reset()
        self.sizer.set_broker(self.broker)
        
        # 设置策略数据
        self.strategy.set_data(self.data)
        
        # 生成信号
        signals = self.strategy.generate_signals()
        
        # 执行回测
        self.data["signal"] = signals
        self.data["equity"] = float(self.broker_config.initial_cash)
        
        prev_signal = 0
        entry_idx = None
        
        for i, (idx, row) in enumerate(self.data.iterrows()):
            current_price = row["close"]
            signal = signals.iloc[i] if i < len(signals) else 0
            
            # 买入信号
            if signal == 1 and prev_signal != 1 and self.broker.position == 0:
                size = self.sizer.get_size(current_price, self.data.iloc[:i+1])
                if size > 0:
                    self.broker.buy(current_price, size, idx)
                    entry_idx = i
            
            # 卖出信号
            elif signal == -1 and self.broker.position > 0:
                self.broker.sell(current_price, date=idx)
                
                # 更新交易持仓天数
                if self.broker.trades and entry_idx is not None:
                    self.broker.trades[-1].bars_held = i - entry_idx
                    entry_idx = None
            
            # 更新资金曲线
            self.broker.update_history(current_price)
            self.data.loc[idx, "equity"] = self.broker.get_value(current_price)
            
            prev_signal = signal
        
        # 强制平仓
        if self.broker.position > 0:
            final_price = self.data["close"].iloc[-1]
            final_date = self.data.index[-1]
            self.broker.sell(final_price, date=final_date)
            if self.broker.trades and entry_idx is not None:
                self.broker.trades[-1].bars_held = len(self.data) - 1 - entry_idx
        
        # 运行分析器
        metrics = self.analyzers.analyze(self.data, self.broker.trades)
        
        # 构建结果
        result = CerebroResult(
            data=self.data,
            trades=self.broker.trades,
            metrics=metrics,
            initial_capital=self.broker_config.initial_cash,
            final_capital=self.broker.get_value(self.data["close"].iloc[-1]),
        )
        
        # 填充指标
        result.total_return = (result.final_capital - result.initial_capital) / result.initial_capital
        result.annual_return = metrics.get("annual_return", 0)
        result.max_drawdown = metrics.get("max_drawdown", 0)
        result.sharpe_ratio = metrics.get("sharpe_ratio", 0)
        result.calmar_ratio = metrics.get("calmar_ratio", 0)
        result.win_rate = metrics.get("win_rate", 0)
        result.profit_factor = metrics.get("profit_factor", 0)
        result.total_trades = metrics.get("total_trades", 0)
        result.avg_hold_days = metrics.get("average_bars_held", 0)
        
        return result
    
    def optimize(self, strategy_class, param_grid: dict, 
                 metric: str = "sharpe_ratio") -> pd.DataFrame:
        """
        参数优化
        
        Args:
            strategy_class: 策略类
            param_grid: 参数网格 {"param1": [v1, v2], "param2": [v1, v2]}
            metric: 优化目标指标
        
        Returns:
            优化结果 DataFrame
        """
        from itertools import product
        
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        
        results = []
        
        for values in product(*param_values):
            params = dict(zip(param_names, values))
            
            # 创建策略
            strategy = strategy_class(**params)
            self.add_strategy(strategy)
            
            # 运行回测
            result = self.run()
            
            # 记录结果
            record = params.copy()
            record["total_return"] = result.total_return
            record["sharpe_ratio"] = result.sharpe_ratio
            record["max_drawdown"] = result.max_drawdown
            record["win_rate"] = result.win_rate
            record["total_trades"] = result.total_trades
            results.append(record)
        
        # 按目标指标排序
        df = pd.DataFrame(results)
        df = df.sort_values(metric, ascending=False)
        
        return df
