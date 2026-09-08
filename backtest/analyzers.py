"""
回测分析器模块 - 参考 Backtrader Analyzers
提供专业的绩效分析指标
"""
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime


@dataclass
class TradeRecord:
    """单笔交易记录"""
    entry_date: datetime
    entry_price: float
    exit_date: Optional[datetime] = None
    exit_price: Optional[float] = None
    size: int = 0
    direction: str = "long"  # long / short
    pnl: float = 0.0
    pnl_pct: float = 0.0
    bars_held: int = 0
    mae: float = 0.0  # Maximum Adverse Excursion 最大不利偏移
    mfe: float = 0.0  # Maximum Favorable Excursion 最大有利偏移


class BaseAnalyzer:
    """分析器基类"""
    
    def __init__(self):
        self.data = None
        self.trades: List[TradeRecord] = []
    
    def set_data(self, data: pd.DataFrame, trades: List[TradeRecord]):
        self.data = data
        self.trades = trades
    
    def analyze(self) -> dict:
        raise NotImplementedError


class SharpeRatioAnalyzer(BaseAnalyzer):
    """
    夏普比率分析器
    
    Sharpe = (Return - RiskFreeRate) / Std(Return)
    """
    
    def __init__(self, risk_free_rate: float = 0.03, periods: int = 252):
        super().__init__()
        self.risk_free_rate = risk_free_rate
        self.periods = periods  # 年化周期数
    
    def analyze(self) -> dict:
        if self.data is None or "equity" not in self.data.columns:
            return {"sharpe_ratio": 0.0}
        
        # 计算日收益率
        returns = self.data["equity"].pct_change().dropna()
        
        if len(returns) < 2 or returns.std() == 0:
            return {"sharpe_ratio": 0.0}
        
        # 年化收益率
        annual_return = returns.mean() * self.periods
        # 年化波动率
        annual_std = returns.std() * np.sqrt(self.periods)
        
        # 夏普比率
        sharpe = (annual_return - self.risk_free_rate) / annual_std if annual_std > 0 else 0
        
        return {
            "sharpe_ratio": round(sharpe, 4),
            "annual_return": round(annual_return, 4),
            "annual_volatility": round(annual_std, 4)
        }


class SortinoRatioAnalyzer(BaseAnalyzer):
    """
    索提诺比率分析器
    
    只考虑下行波动率，比夏普更合理
    Sortino = (Return - RiskFreeRate) / DownsideStd
    """
    
    def __init__(self, risk_free_rate: float = 0.03, periods: int = 252):
        super().__init__()
        self.risk_free_rate = risk_free_rate
        self.periods = periods
    
    def analyze(self) -> dict:
        if self.data is None or "equity" not in self.data.columns:
            return {"sortino_ratio": 0.0}
        
        returns = self.data["equity"].pct_change().dropna()
        
        if len(returns) < 2:
            return {"sortino_ratio": 0.0}
        
        # 只计算负收益的标准差
        negative_returns = returns[returns < 0]
        downside_std = negative_returns.std() * np.sqrt(self.periods) if len(negative_returns) > 0 else 0
        
        annual_return = returns.mean() * self.periods
        
        sortino = (annual_return - self.risk_free_rate) / downside_std if downside_std > 0 else 0
        
        return {
            "sortino_ratio": round(sortino, 4),
            "downside_volatility": round(downside_std, 4)
        }


class DrawDownAnalyzer(BaseAnalyzer):
    """
    回撤分析器
    
    计算各种回撤指标
    """
    
    def analyze(self) -> dict:
        if self.data is None or "equity" not in self.data.columns:
            return {}
        
        equity = self.data["equity"]
        
        # 计算回撤序列
        rolling_max = equity.cummax()
        drawdown = (equity - rolling_max) / rolling_max
        
        # 最大回撤
        max_dd = drawdown.min()
        max_dd_idx = drawdown.idxmin()
        
        # 找到最大回撤的起点
        peak_idx = equity[:max_dd_idx].idxmax()
        
        # 回撤持续时间
        dd_duration = (max_dd_idx - peak_idx).days if hasattr(max_dd_idx - peak_idx, 'days') else 0
        
        # 平均回撤
        avg_dd = drawdown[drawdown < 0].mean() if len(drawdown[drawdown < 0]) > 0 else 0
        
        # 回撤次数（从峰值下跌超过5%的次数）
        dd_count = (drawdown < -0.05).sum()
        
        return {
            "max_drawdown": round(abs(max_dd), 4),
            "max_drawdown_date": str(max_dd_idx),
            "drawdown_peak_date": str(peak_idx),
            "drawdown_duration_days": dd_duration,
            "average_drawdown": round(abs(avg_dd), 4),
            "drawdown_count_5pct": int(dd_count)
        }


class TradeAnalyzer(BaseAnalyzer):
    """
    交易分析器
    
    详细分析每笔交易的统计数据
    """
    
    def analyze(self) -> dict:
        if not self.trades:
            return {
                "total_trades": 0,
                "win_rate": 0.0,
                "profit_factor": 0.0
            }
        
        # 基础统计
        total = len(self.trades)
        winners = [t for t in self.trades if t.pnl > 0]
        losers = [t for t in self.trades if t.pnl < 0]
        
        win_count = len(winners)
        loss_count = len(losers)
        
        # 盈亏统计
        total_profit = sum(t.pnl for t in winners) if winners else 0
        total_loss = abs(sum(t.pnl for t in losers)) if losers else 0
        
        # 胜率
        win_rate = win_count / total if total > 0 else 0
        
        # 盈亏比
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
        
        # 平均盈利/亏损
        avg_win = total_profit / win_count if win_count > 0 else 0
        avg_loss = total_loss / loss_count if loss_count > 0 else 0
        
        # 最大单笔盈利/亏损
        max_win = max((t.pnl for t in winners), default=0)
        max_loss = min((t.pnl for t in losers), default=0)
        
        # 连续盈亏
        max_consecutive_wins = self._max_consecutive(self.trades, True)
        max_consecutive_losses = self._max_consecutive(self.trades, False)
        
        # 平均持仓时间
        avg_bars = sum(t.bars_held for t in self.trades) / total if total > 0 else 0
        
        # 期望值
        expectancy = (win_rate * avg_win - (1 - win_rate) * avg_loss) if total > 0 else 0
        
        return {
            "total_trades": total,
            "winning_trades": win_count,
            "losing_trades": loss_count,
            "win_rate": round(win_rate, 4),
            "profit_factor": round(profit_factor, 4),
            "total_profit": round(total_profit, 2),
            "total_loss": round(total_loss, 2),
            "net_profit": round(total_profit - total_loss, 2),
            "average_win": round(avg_win, 2),
            "average_loss": round(avg_loss, 2),
            "max_win": round(max_win, 2),
            "max_loss": round(max_loss, 2),
            "max_consecutive_wins": max_consecutive_wins,
            "max_consecutive_losses": max_consecutive_losses,
            "average_bars_held": round(avg_bars, 1),
            "expectancy": round(expectancy, 2)
        }
    
    def _max_consecutive(self, trades: List[TradeRecord], is_win: bool) -> int:
        max_count = 0
        current_count = 0
        
        for t in trades:
            if (is_win and t.pnl > 0) or (not is_win and t.pnl < 0):
                current_count += 1
                max_count = max(max_count, current_count)
            else:
                current_count = 0
        
        return max_count


class CalmarRatioAnalyzer(BaseAnalyzer):
    """
    卡玛比率分析器
    
    Calmar = AnnualReturn / MaxDrawdown
    """
    
    def __init__(self, periods: int = 252):
        super().__init__()
        self.periods = periods
    
    def analyze(self) -> dict:
        if self.data is None or "equity" not in self.data.columns:
            return {"calmar_ratio": 0.0}
        
        equity = self.data["equity"]
        returns = equity.pct_change().dropna()
        
        # 年化收益率
        annual_return = returns.mean() * self.periods
        
        # 最大回撤
        rolling_max = equity.cummax()
        drawdown = (equity - rolling_max) / rolling_max
        max_dd = abs(drawdown.min())
        
        calmar = annual_return / max_dd if max_dd > 0 else 0
        
        return {
            "calmar_ratio": round(calmar, 4)
        }


class TimeReturnAnalyzer(BaseAnalyzer):
    """
    时间周期收益分析器
    
    按月/季/年统计收益
    """
    
    def analyze(self) -> dict:
        if self.data is None or "equity" not in self.data.columns:
            return {}
        
        equity = self.data["equity"].copy()
        equity.index = pd.to_datetime(self.data.index)
        
        # 月度收益
        monthly = equity.resample('ME').last().pct_change().dropna()
        
        # 统计正收益月份
        positive_months = (monthly > 0).sum()
        total_months = len(monthly)
        
        # 最好/最差月份
        best_month = monthly.max() if len(monthly) > 0 else 0
        worst_month = monthly.min() if len(monthly) > 0 else 0
        
        # 年度收益
        yearly = equity.resample('YE').last().pct_change().dropna()
        
        return {
            "total_months": int(total_months),
            "positive_months": int(positive_months),
            "negative_months": int(total_months - positive_months),
            "best_month_return": round(best_month, 4),
            "worst_month_return": round(worst_month, 4),
            "monthly_win_rate": round(positive_months / total_months, 4) if total_months > 0 else 0,
            "average_monthly_return": round(monthly.mean(), 4) if len(monthly) > 0 else 0
        }


class RiskAnalyzer(BaseAnalyzer):
    """
    综合风险分析器
    
    VaR, CVaR, 波动率等
    """
    
    def __init__(self, confidence: float = 0.95):
        super().__init__()
        self.confidence = confidence
    
    def analyze(self) -> dict:
        if self.data is None or "equity" not in self.data.columns:
            return {}
        
        returns = self.data["equity"].pct_change().dropna()
        
        if len(returns) < 10:
            return {}
        
        # VaR (Value at Risk)
        var = returns.quantile(1 - self.confidence)
        
        # CVaR (Conditional VaR / Expected Shortfall)
        cvar = returns[returns <= var].mean()
        
        # 波动率
        daily_vol = returns.std()
        annual_vol = daily_vol * np.sqrt(252)
        
        # 偏度和峰度
        skewness = returns.skew()
        kurtosis = returns.kurtosis()
        
        # 最大单日涨跌
        max_daily_gain = returns.max()
        max_daily_loss = returns.min()
        
        return {
            f"var_{int(self.confidence*100)}": round(var, 4),
            f"cvar_{int(self.confidence*100)}": round(cvar, 4),
            "daily_volatility": round(daily_vol, 4),
            "annual_volatility": round(annual_vol, 4),
            "skewness": round(skewness, 4),
            "kurtosis": round(kurtosis, 4),
            "max_daily_gain": round(max_daily_gain, 4),
            "max_daily_loss": round(max_daily_loss, 4)
        }


class AnalyzerSuite:
    """
    分析器套件
    
    一次性运行所有分析器
    """
    
    def __init__(self):
        self.analyzers = [
            SharpeRatioAnalyzer(),
            SortinoRatioAnalyzer(),
            CalmarRatioAnalyzer(),
            DrawDownAnalyzer(),
            TradeAnalyzer(),
            TimeReturnAnalyzer(),
            RiskAnalyzer()
        ]
    
    def analyze(self, data: pd.DataFrame, trades: List[TradeRecord] = None) -> dict:
        """运行所有分析器，返回综合报告"""
        trades = trades or []
        results = {}
        
        for analyzer in self.analyzers:
            analyzer.set_data(data, trades)
            result = analyzer.analyze()
            results.update(result)
        
        return results
    
    def report(self, results: dict) -> str:
        """生成文本报告"""
        lines = []
        lines.append("=" * 60)
        lines.append("                    回测绩效报告")
        lines.append("=" * 60)
        
        # 收益指标
        lines.append("\n【收益指标】")
        lines.append(f"  年化收益率:     {results.get('annual_return', 0):.2%}")
        lines.append(f"  总收益率:       {results.get('net_profit', 0):,.2f}")
        
        # 风险指标
        lines.append("\n【风险指标】")
        lines.append(f"  最大回撤:       {results.get('max_drawdown', 0):.2%}")
        lines.append(f"  年化波动率:     {results.get('annual_volatility', 0):.2%}")
        lines.append(f"  VaR(95%):       {results.get('var_95', 0):.2%}")
        
        # 风险调整收益
        lines.append("\n【风险调整收益】")
        lines.append(f"  夏普比率:       {results.get('sharpe_ratio', 0):.2f}")
        lines.append(f"  索提诺比率:     {results.get('sortino_ratio', 0):.2f}")
        lines.append(f"  卡玛比率:       {results.get('calmar_ratio', 0):.2f}")
        
        # 交易统计
        lines.append("\n【交易统计】")
        lines.append(f"  交易次数:       {results.get('total_trades', 0)}")
        lines.append(f"  胜率:           {results.get('win_rate', 0):.2%}")
        lines.append(f"  盈亏比:         {results.get('profit_factor', 0):.2f}")
        lines.append(f"  期望值:         {results.get('expectancy', 0):.2f}")
        lines.append(f"  最大连胜:       {results.get('max_consecutive_wins', 0)}")
        lines.append(f"  最大连亏:       {results.get('max_consecutive_losses', 0)}")
        
        # 月度统计
        lines.append("\n【月度统计】")
        lines.append(f"  盈利月份:       {results.get('positive_months', 0)}/{results.get('total_months', 0)}")
        lines.append(f"  月胜率:         {results.get('monthly_win_rate', 0):.2%}")
        lines.append(f"  最佳月份:       {results.get('best_month_return', 0):.2%}")
        lines.append(f"  最差月份:       {results.get('worst_month_return', 0):.2%}")
        
        lines.append("\n" + "=" * 60)
        
        return "\n".join(lines)
