"""
因子分析报告
包括：
- IC/IR 分析
- 因子收益归因
- 分组回测
- 因子相关性
- 衰减分析
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from scipy import stats
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class FactorAnalyzer:
    """
    因子分析器
    
    提供专业的因子有效性检验和分析
    """
    
    def __init__(self, factor_data: pd.DataFrame, return_data: pd.Series):
        """
        Args:
            factor_data: 因子数据 DataFrame，index=日期，columns=因子名
            return_data: 收益率数据 Series，index=日期
        """
        self.factor_data = factor_data
        self.return_data = return_data
        self.aligned_data = self._align_data()
        
    def _align_data(self) -> pd.DataFrame:
        """对齐因子和收益数据"""
        common_index = self.factor_data.index.intersection(self.return_data.index)
        df = self.factor_data.loc[common_index].copy()
        df["return"] = self.return_data.loc[common_index]
        return df.dropna()
    
    def calculate_ic(self, factor_name: str, method: str = "spearman") -> pd.Series:
        """
        计算 IC (Information Coefficient)
        
        IC = corr(factor, next_period_return)
        
        Args:
            factor_name: 因子名称
            method: "spearman"(秩相关) 或 "pearson"(线性相关)
        
        Returns:
            每期 IC 值的 Series
        """
        if factor_name not in self.factor_data.columns:
            raise ValueError(f"因子 {factor_name} 不存在")
        
        factor = self.aligned_data[factor_name]
        returns = self.aligned_data["return"].shift(-1)  # 下期收益
        
        # 按日期计算相关性
        df = pd.DataFrame({"factor": factor, "return": returns}).dropna()
        
        if method == "spearman":
            ic = df["factor"].corr(df["return"], method="spearman")
        else:
            ic = df["factor"].corr(df["return"], method="pearson")
        
        return ic
    
    def calculate_ic_series(self, factor_name: str, window: int = 20, method: str = "spearman") -> pd.Series:
        """
        计算滚动 IC 序列
        
        Args:
            factor_name: 因子名称
            window: 滚动窗口
            method: 相关性方法
        
        Returns:
            IC 时间序列
        """
        factor = self.aligned_data[factor_name]
        returns = self.aligned_data["return"].shift(-1)
        
        ic_list = []
        dates = []
        
        for i in range(window, len(factor)):
            f = factor.iloc[i-window:i]
            r = returns.iloc[i-window:i]
            
            valid = ~(f.isna() | r.isna())
            if valid.sum() >= window // 2:
                if method == "spearman":
                    ic, _ = stats.spearmanr(f[valid], r[valid])
                else:
                    ic, _ = stats.pearsonr(f[valid], r[valid])
                ic_list.append(ic)
                dates.append(factor.index[i])
        
        return pd.Series(ic_list, index=dates)
    
    def calculate_ir(self, factor_name: str, window: int = 60) -> float:
        """
        计算 IR (Information Ratio)
        
        IR = mean(IC) / std(IC)
        
        Args:
            factor_name: 因子名称
            window: 计算窗口
        
        Returns:
            IR 值
        """
        ic_series = self.calculate_ic_series(factor_name, window)
        
        if len(ic_series) == 0 or ic_series.std() == 0:
            return 0
        
        return ic_series.mean() / ic_series.std()
    
    def factor_group_return(self, factor_name: str, n_groups: int = 5) -> pd.DataFrame:
        """
        因子分组收益分析
        
        按因子值分成 n 组，计算每组的平均收益
        
        Args:
            factor_name: 因子名称
            n_groups: 分组数量
        
        Returns:
            各组收益统计
        """
        df = self.aligned_data[[factor_name, "return"]].dropna()
        
        # 分组
        df["group"] = pd.qcut(df[factor_name], n_groups, labels=False, duplicates="drop")
        
        # 计算各组统计
        group_stats = df.groupby("group")["return"].agg([
            ("mean_return", "mean"),
            ("std_return", "std"),
            ("count", "count"),
            ("sharpe", lambda x: x.mean() / x.std() * np.sqrt(252) if x.std() > 0 else 0)
        ])
        
        group_stats.index = [f"Q{i+1}" for i in range(len(group_stats))]
        
        # 计算多空收益
        if len(group_stats) >= 2:
            long_short = group_stats.iloc[-1]["mean_return"] - group_stats.iloc[0]["mean_return"]
            group_stats.loc["Long-Short", "mean_return"] = long_short
        
        return group_stats
    
    def factor_decay(self, factor_name: str, max_lag: int = 20) -> pd.DataFrame:
        """
        因子衰减分析
        
        分析因子预测能力随时间的衰减
        
        Args:
            factor_name: 因子名称
            max_lag: 最大滞后期数
        
        Returns:
            各滞后期的 IC
        """
        factor = self.aligned_data[factor_name]
        returns = self.aligned_data["return"]
        
        results = []
        for lag in range(1, max_lag + 1):
            future_return = returns.shift(-lag)
            valid = ~(factor.isna() | future_return.isna())
            
            if valid.sum() > 30:
                ic, pvalue = stats.spearmanr(factor[valid], future_return[valid])
                results.append({
                    "lag": lag,
                    "ic": ic,
                    "pvalue": pvalue,
                    "significant": pvalue < 0.05
                })
        
        return pd.DataFrame(results)
    
    def factor_correlation(self) -> pd.DataFrame:
        """
        因子相关性矩阵
        
        Returns:
            因子间相关性矩阵
        """
        factor_cols = [c for c in self.factor_data.columns if c != "return"]
        return self.factor_data[factor_cols].corr()
    
    def factor_turnover(self, factor_name: str, top_pct: float = 0.2) -> pd.Series:
        """
        因子换手率分析
        
        计算每期 top 组合的换手率
        
        Args:
            factor_name: 因子名称
            top_pct: 头部比例
        
        Returns:
            换手率时间序列
        """
        factor = self.factor_data[factor_name]
        
        turnover_list = []
        dates = []
        prev_top = set()
        
        for date in factor.index:
            values = factor.loc[date]
            if isinstance(values, pd.Series):
                threshold = values.quantile(1 - top_pct)
                current_top = set(values[values >= threshold].index)
            else:
                current_top = set()
            
            if prev_top:
                if len(prev_top) > 0:
                    turnover = 1 - len(prev_top & current_top) / len(prev_top)
                else:
                    turnover = 1
                turnover_list.append(turnover)
                dates.append(date)
            
            prev_top = current_top
        
        return pd.Series(turnover_list, index=dates)
    
    def full_report(self, factor_name: str) -> Dict:
        """
        生成完整因子分析报告
        
        Args:
            factor_name: 因子名称
        
        Returns:
            分析报告字典
        """
        report = {
            "factor_name": factor_name,
            "data_points": len(self.aligned_data),
            "date_range": f"{self.aligned_data.index[0]} ~ {self.aligned_data.index[-1]}"
        }
        
        # IC 分析
        ic = self.calculate_ic(factor_name)
        ic_series = self.calculate_ic_series(factor_name)
        
        report["ic_analysis"] = {
            "ic": ic,
            "ic_mean": float(ic_series.mean()) if len(ic_series) > 0 else 0,
            "ic_std": float(ic_series.std()) if len(ic_series) > 0 else 0,
            "ir": self.calculate_ir(factor_name),
            "ic_positive_ratio": float((ic_series > 0).mean()) if len(ic_series) > 0 else 0
        }
        
        # 分组收益
        group_return = self.factor_group_return(factor_name)
        report["group_return"] = group_return.to_dict()
        
        # 衰减分析
        decay = self.factor_decay(factor_name, 10)
        report["decay"] = decay.to_dict("records")
        
        return report
    
    def print_report(self, factor_name: str):
        """打印因子分析报告"""
        report = self.full_report(factor_name)
        
        print("\n" + "=" * 60)
        print(f"因子分析报告: {factor_name}")
        print("=" * 60)
        
        print(f"\n【基本信息】")
        print(f"  数据点数: {report['data_points']}")
        print(f"  日期范围: {report['date_range']}")
        
        ic_info = report["ic_analysis"]
        print(f"\n【IC 分析】")
        print(f"  IC:             {ic_info['ic']:>10.4f}")
        print(f"  IC 均值:        {ic_info['ic_mean']:>10.4f}")
        print(f"  IC 标准差:      {ic_info['ic_std']:>10.4f}")
        print(f"  IR:             {ic_info['ir']:>10.4f}")
        print(f"  IC 正值比例:    {ic_info['ic_positive_ratio']:>10.2%}")
        
        print(f"\n【分组收益】")
        group_df = pd.DataFrame(report["group_return"])
        print(group_df.to_string())
        
        print(f"\n【衰减分析】")
        decay_df = pd.DataFrame(report["decay"])
        for _, row in decay_df.head(5).iterrows():
            sig = "***" if row["pvalue"] < 0.01 else ("**" if row["pvalue"] < 0.05 else "")
            print(f"  Lag {row['lag']:>2}: IC = {row['ic']:>7.4f} {sig}")
        
        print("\n" + "=" * 60)


def analyze_factor(
    prices: pd.DataFrame,
    factor_func,
    periods: int = 1
) -> FactorAnalyzer:
    """
    快速分析因子
    
    Args:
        prices: 价格数据（需含 close 列）
        factor_func: 因子计算函数，接受 DataFrame 返回 Series
        periods: 收益计算周期
    
    Returns:
        FactorAnalyzer 实例
    """
    # 计算因子
    factor_values = factor_func(prices)
    factor_df = pd.DataFrame({"factor": factor_values})
    
    # 计算收益
    returns = prices["close"].pct_change(periods).shift(-periods)
    
    return FactorAnalyzer(factor_df, returns)


# 常用因子函数
def momentum_factor(data: pd.DataFrame, period: int = 20) -> pd.Series:
    """动量因子"""
    return data["close"].pct_change(period)


def volatility_factor(data: pd.DataFrame, period: int = 20) -> pd.Series:
    """波动率因子"""
    return data["close"].pct_change().rolling(period).std()


def volume_factor(data: pd.DataFrame, period: int = 20) -> pd.Series:
    """量比因子"""
    return data["volume"] / data["volume"].rolling(period).mean()


def reversal_factor(data: pd.DataFrame, period: int = 5) -> pd.Series:
    """反转因子"""
    return -data["close"].pct_change(period)


def rsi_factor(data: pd.DataFrame, period: int = 14) -> pd.Series:
    """RSI因子"""
    delta = data["close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))
