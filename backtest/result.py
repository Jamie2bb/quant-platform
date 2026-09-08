"""
回测结果分析
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class Trade:
    """单笔交易记录"""
    entry_date: pd.Timestamp
    entry_price: float
    exit_date: pd.Timestamp
    exit_price: float
    shares: int
    pnl: float
    pnl_pct: float
    hold_days: int


class BacktestResult:
    """回测结果"""
    
    def __init__(self, data: pd.DataFrame, trades: List[Trade], 
                 initial_capital: float, strategy_name: str):
        self.data = data
        self.trades = trades
        self.initial_capital = initial_capital
        self.strategy_name = strategy_name
        
        # 计算各项指标
        self._calculate_metrics()
    
    def _calculate_metrics(self):
        """计算绩效指标"""
        equity = self.data["equity"]
        returns = self.data["returns"]
        
        # 基本指标
        self.final_capital = equity.iloc[-1]
        self.total_return = (self.final_capital - self.initial_capital) / self.initial_capital
        self.total_trades = len(self.trades)
        
        if self.total_trades > 0:
            winning_trades = [t for t in self.trades if t.pnl > 0]
            self.win_rate = len(winning_trades) / self.total_trades
            self.avg_pnl = np.mean([t.pnl for t in self.trades])
            self.avg_pnl_pct = np.mean([t.pnl_pct for t in self.trades])
            self.avg_hold_days = np.mean([t.hold_days for t in self.trades])
            
            # 盈亏比
            avg_win = np.mean([t.pnl for t in winning_trades]) if winning_trades else 0
            losing_trades = [t for t in self.trades if t.pnl <= 0]
            avg_loss = abs(np.mean([t.pnl for t in losing_trades])) if losing_trades else 1
            self.profit_factor = avg_win / avg_loss if avg_loss > 0 else 0
        else:
            self.win_rate = 0
            self.avg_pnl = 0
            self.avg_pnl_pct = 0
            self.avg_hold_days = 0
            self.profit_factor = 0
        
        # 最大回撤
        cummax = equity.cummax()
        drawdown = (equity - cummax) / cummax
        self.max_drawdown = drawdown.min()
        self.max_drawdown_date = drawdown.idxmin()
        
        # 年化收益率（假设252个交易日）
        days = (self.data.index[-1] - self.data.index[0]).days
        if days > 0:
            self.annual_return = (1 + self.total_return) ** (365 / days) - 1
        else:
            self.annual_return = 0
        
        # 夏普比率（假设无风险利率3%）
        risk_free_rate = 0.03
        if returns.std() > 0:
            excess_return = returns.mean() * 252 - risk_free_rate
            self.sharpe_ratio = excess_return / (returns.std() * np.sqrt(252))
        else:
            self.sharpe_ratio = 0
        
        # 卡玛比率
        if self.max_drawdown < 0:
            self.calmar_ratio = self.annual_return / abs(self.max_drawdown)
        else:
            self.calmar_ratio = 0
    
    def summary(self) -> str:
        """输出绩效摘要"""
        lines = [
            f"\n{'='*50}",
            f"策略: {self.strategy_name}",
            f"{'='*50}",
            f"",
            f"【收益指标】",
            f"  初始资金:     {self.initial_capital:>15,.2f}",
            f"  最终资金:     {self.final_capital:>15,.2f}",
            f"  总收益率:     {self.total_return:>14.2%}",
            f"  年化收益率:   {self.annual_return:>14.2%}",
            f"",
            f"【风险指标】",
            f"  最大回撤:     {self.max_drawdown:>14.2%}",
            f"  夏普比率:     {self.sharpe_ratio:>15.2f}",
            f"  卡玛比率:     {self.calmar_ratio:>15.2f}",
            f"",
            f"【交易统计】",
            f"  交易次数:     {self.total_trades:>15d}",
            f"  胜率:         {self.win_rate:>14.2%}",
            f"  盈亏比:       {self.profit_factor:>15.2f}",
            f"  平均盈亏:     {self.avg_pnl:>15,.2f}",
            f"  平均持仓天数: {self.avg_hold_days:>15.1f}",
            f"{'='*50}",
        ]
        summary_text = "\n".join(lines)
        print(summary_text)
        return summary_text
    
    def plot(self, figsize=(14, 10), save_path: str = None):
        """绘制回测结果图表"""
        # 设置中文字体
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
        plt.rcParams['axes.unicode_minus'] = False
        
        fig, axes = plt.subplots(3, 1, figsize=figsize)
        
        # 1. 资金曲线
        ax1 = axes[0]
        ax1.plot(self.data.index, self.data["equity"], label="策略净值", color="blue")
        ax1.axhline(y=self.initial_capital, color="gray", linestyle="--", alpha=0.5)
        ax1.set_title(f"{self.strategy_name} - 资金曲线")
        ax1.set_ylabel("资金")
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 标记交易点
        for trade in self.trades:
            ax1.scatter(trade.entry_date, self.data.loc[trade.entry_date, "equity"], 
                       marker="^", color="green", s=50, zorder=5)
            ax1.scatter(trade.exit_date, self.data.loc[trade.exit_date, "equity"], 
                       marker="v", color="red", s=50, zorder=5)
        
        # 2. 回撤曲线
        ax2 = axes[1]
        cummax = self.data["equity"].cummax()
        drawdown = (self.data["equity"] - cummax) / cummax * 100
        ax2.fill_between(self.data.index, drawdown, 0, color="red", alpha=0.3)
        ax2.plot(self.data.index, drawdown, color="red", linewidth=0.5)
        ax2.set_title("回撤曲线")
        ax2.set_ylabel("回撤 (%)")
        ax2.grid(True, alpha=0.3)
        
        # 3. 价格与买卖点
        ax3 = axes[2]
        ax3.plot(self.data.index, self.data["close"], label="价格", color="black", alpha=0.7)
        
        for trade in self.trades:
            ax3.scatter(trade.entry_date, trade.entry_price, 
                       marker="^", color="green", s=80, label="买入" if trade == self.trades[0] else "")
            ax3.scatter(trade.exit_date, trade.exit_price, 
                       marker="v", color="red", s=80, label="卖出" if trade == self.trades[0] else "")
        
        ax3.set_title("价格与交易点")
        ax3.set_ylabel("价格")
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches="tight")
        
        plt.show()
        
        return fig
    
    def get_trades_df(self) -> pd.DataFrame:
        """获取交易明细 DataFrame"""
        if not self.trades:
            return pd.DataFrame()
        
        records = []
        for i, t in enumerate(self.trades, 1):
            records.append({
                "序号": i,
                "买入日期": t.entry_date.strftime("%Y-%m-%d"),
                "买入价格": t.entry_price,
                "卖出日期": t.exit_date.strftime("%Y-%m-%d"),
                "卖出价格": t.exit_price,
                "数量": t.shares,
                "盈亏": t.pnl,
                "收益率": f"{t.pnl_pct:.2%}",
                "持仓天数": t.hold_days
            })
        
        return pd.DataFrame(records)
