# -*- coding: utf-8 -*-
"""
持仓分析器 - 分析单只股票的技术面和风险状态
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

from data.fetcher import DataFetcher
from utils.indicators import SMA, EMA, RSI, MACD, KDJ, BOLL
from .config import StopRules, TechRules


@dataclass
class StockAnalysis:
    """股票分析结果"""
    symbol: str
    name: str
    
    # 基本行情
    price: float = 0
    change_pct: float = 0
    turnover: float = 0
    
    # 均线位置
    ma5: float = 0
    ma10: float = 0
    ma20: float = 0
    ma60: float = 0
    above_ma5: bool = False
    above_ma10: bool = False
    above_ma20: bool = False
    above_ma60: bool = False
    ma_trend: str = ""  # 多头排列/空头排列/纠缠
    
    # MACD
    macd_dif: float = 0
    macd_dea: float = 0
    macd_hist: float = 0
    macd_status: str = ""  # 金叉/死叉/多头/空头
    macd_divergence: str = ""  # 顶背离/底背离/无
    
    # RSI
    rsi: float = 0
    rsi_status: str = ""  # 超买/超卖/中性
    
    # KDJ
    k: float = 0
    d: float = 0
    j: float = 0
    kdj_status: str = ""
    
    # 布林带
    boll_upper: float = 0
    boll_mid: float = 0
    boll_lower: float = 0
    boll_position: float = 0  # 0-100，位置百分比
    boll_status: str = ""
    
    # 成交量
    volume_ratio: float = 0  # 量比
    volume_trend: str = ""   # 放量/缩量/平量
    
    # 综合信号
    bullish_signals: List[str] = field(default_factory=list)
    bearish_signals: List[str] = field(default_factory=list)
    score: int = 0  # -100 到 100
    suggestion: str = ""


class StockAnalyzer:
    """股票分析器"""
    
    def __init__(self, symbol: str, name: str = ""):
        self.symbol = symbol
        self.name = name
        self.df: Optional[pd.DataFrame] = None
    
    def load_data(self, days: int = 120) -> bool:
        """加载历史数据"""
        try:
            start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
            self.df = DataFetcher.get_stock_daily(self.symbol, start_date)
            return len(self.df) >= 60
        except Exception as e:
            print(f"加载 {self.symbol} 数据失败: {e}")
            return False
    
    def analyze(self) -> StockAnalysis:
        """执行全面分析"""
        if self.df is None or len(self.df) < 60:
            if not self.load_data():
                return StockAnalysis(symbol=self.symbol, name=self.name)
        
        df = self.df
        result = StockAnalysis(symbol=self.symbol, name=self.name)
        
        # 基本行情
        result.price = df['close'].iloc[-1]
        result.change_pct = df['pct_change'].iloc[-1] if 'pct_change' in df.columns else 0
        result.turnover = df['turnover'].iloc[-1] if 'turnover' in df.columns else 0
        
        # 计算均线
        result.ma5 = df['close'].rolling(5).mean().iloc[-1]
        result.ma10 = df['close'].rolling(10).mean().iloc[-1]
        result.ma20 = df['close'].rolling(20).mean().iloc[-1]
        result.ma60 = df['close'].rolling(60).mean().iloc[-1]
        
        result.above_ma5 = result.price > result.ma5
        result.above_ma10 = result.price > result.ma10
        result.above_ma20 = result.price > result.ma20
        result.above_ma60 = result.price > result.ma60
        
        # 均线趋势判断
        if result.ma5 > result.ma10 > result.ma20 > result.ma60:
            result.ma_trend = "多头排列"
            result.bullish_signals.append("均线多头排列")
        elif result.ma5 < result.ma10 < result.ma20 < result.ma60:
            result.ma_trend = "空头排列"
            result.bearish_signals.append("均线空头排列")
        else:
            result.ma_trend = "均线纠缠"
        
        # MACD
        dif, dea, hist = MACD(df['close'])
        result.macd_dif = dif.iloc[-1]
        result.macd_dea = dea.iloc[-1]
        result.macd_hist = hist.iloc[-1]
        
        prev_dif, prev_dea = dif.iloc[-2], dea.iloc[-2]
        if result.macd_dif > result.macd_dea:
            if prev_dif <= prev_dea:
                result.macd_status = "刚金叉"
                result.bullish_signals.append("MACD金叉")
            else:
                result.macd_status = "多头"
        else:
            if prev_dif >= prev_dea:
                result.macd_status = "刚死叉"
                result.bearish_signals.append("MACD死叉")
            else:
                result.macd_status = "空头"
        
        # MACD 背离检测
        result.macd_divergence = self._detect_macd_divergence(df, dif)
        if result.macd_divergence == "底背离":
            result.bullish_signals.append("MACD底背离")
        elif result.macd_divergence == "顶背离":
            result.bearish_signals.append("MACD顶背离")
        
        # RSI
        result.rsi = RSI(df['close'], 14).iloc[-1]
        if result.rsi > TechRules.RSI_OVERBOUGHT:
            result.rsi_status = "超买"
            result.bearish_signals.append(f"RSI超买({result.rsi:.1f})")
        elif result.rsi < TechRules.RSI_OVERSOLD:
            result.rsi_status = "超卖"
            result.bullish_signals.append(f"RSI超卖({result.rsi:.1f})")
        else:
            result.rsi_status = "中性"
        
        # KDJ
        k, d, j = KDJ(df['high'], df['low'], df['close'])
        result.k = k.iloc[-1]
        result.d = d.iloc[-1]
        result.j = j.iloc[-1]
        
        prev_k, prev_d = k.iloc[-2], d.iloc[-2]
        if result.k > TechRules.KDJ_OVERBOUGHT and result.d > TechRules.KDJ_OVERBOUGHT:
            result.kdj_status = "超买区"
            result.bearish_signals.append("KDJ超买")
        elif result.k < TechRules.KDJ_OVERSOLD and result.d < TechRules.KDJ_OVERSOLD:
            result.kdj_status = "超卖区"
            result.bullish_signals.append("KDJ超卖")
        elif result.k > result.d and prev_k <= prev_d:
            result.kdj_status = "金叉"
            result.bullish_signals.append("KDJ金叉")
        elif result.k < result.d and prev_k >= prev_d:
            result.kdj_status = "死叉"
            result.bearish_signals.append("KDJ死叉")
        else:
            result.kdj_status = "观望"
        
        # 布林带
        upper, mid, lower = BOLL(df['close'])
        result.boll_upper = upper.iloc[-1]
        result.boll_mid = mid.iloc[-1]
        result.boll_lower = lower.iloc[-1]
        
        boll_width = result.boll_upper - result.boll_lower
        if boll_width > 0:
            result.boll_position = (result.price - result.boll_lower) / boll_width * 100
        
        if result.boll_position > 90:
            result.boll_status = "触及上轨"
            result.bearish_signals.append("触及布林上轨")
        elif result.boll_position < 10:
            result.boll_status = "触及下轨"
            result.bullish_signals.append("触及布林下轨")
        elif result.boll_position > 70:
            result.boll_status = "偏强"
        elif result.boll_position < 30:
            result.boll_status = "偏弱"
        else:
            result.boll_status = "中轨附近"
        
        # 成交量分析
        vol_ma5 = df['volume'].rolling(5).mean().iloc[-1]
        vol_ma20 = df['volume'].rolling(20).mean().iloc[-1]
        current_vol = df['volume'].iloc[-1]
        
        if vol_ma20 > 0:
            result.volume_ratio = current_vol / vol_ma20
        
        if result.volume_ratio > 1.5:
            result.volume_trend = "放量"
        elif result.volume_ratio < 0.7:
            result.volume_trend = "缩量"
        else:
            result.volume_trend = "平量"
        
        # 综合评分
        result.score = len(result.bullish_signals) * 15 - len(result.bearish_signals) * 15
        result.score = max(-100, min(100, result.score))
        
        # 综合建议
        if result.score >= 30:
            result.suggestion = "偏多，可持有"
        elif result.score <= -30:
            result.suggestion = "偏空，注意风险"
        else:
            result.suggestion = "中性，观望为主"
        
        return result
    
    def _detect_macd_divergence(self, df: pd.DataFrame, dif: pd.Series, lookback: int = 30) -> str:
        """检测 MACD 背离"""
        if len(df) < lookback:
            return "无"
        
        recent = df.tail(lookback)
        recent_dif = dif.tail(lookback)
        
        # 简化的背离检测：比较最近两个低点/高点
        try:
            # 找价格的局部低点
            price_lows = []
            for i in range(2, len(recent) - 2):
                if recent['low'].iloc[i] <= recent['low'].iloc[i-1] and \
                   recent['low'].iloc[i] <= recent['low'].iloc[i-2] and \
                   recent['low'].iloc[i] <= recent['low'].iloc[i+1] and \
                   recent['low'].iloc[i] <= recent['low'].iloc[i+2]:
                    price_lows.append((i, recent['low'].iloc[i], recent_dif.iloc[i]))
            
            # 底背离：价格新低，DIF 不创新低
            if len(price_lows) >= 2:
                last_low = price_lows[-1]
                prev_low = price_lows[-2]
                if last_low[1] < prev_low[1] and last_low[2] > prev_low[2]:
                    return "底背离"
            
            # 找价格的局部高点
            price_highs = []
            for i in range(2, len(recent) - 2):
                if recent['high'].iloc[i] >= recent['high'].iloc[i-1] and \
                   recent['high'].iloc[i] >= recent['high'].iloc[i-2] and \
                   recent['high'].iloc[i] >= recent['high'].iloc[i+1] and \
                   recent['high'].iloc[i] >= recent['high'].iloc[i+2]:
                    price_highs.append((i, recent['high'].iloc[i], recent_dif.iloc[i]))
            
            # 顶背离：价格新高，DIF 不创新高
            if len(price_highs) >= 2:
                last_high = price_highs[-1]
                prev_high = price_highs[-2]
                if last_high[1] > prev_high[1] and last_high[2] < prev_high[2]:
                    return "顶背离"
        except:
            pass
        
        return "无"
    
    def get_support_resistance(self) -> Tuple[float, float]:
        """获取支撑位和压力位"""
        if self.df is None or len(self.df) < 20:
            return (0, 0)
        
        df = self.df.tail(60)
        
        # 简单方法：用最近的低点作为支撑，高点作为压力
        recent_low = df['low'].min()
        recent_high = df['high'].max()
        
        # 也可以用布林带
        _, mid, lower = BOLL(df['close'])
        
        support = max(recent_low, lower.iloc[-1])
        resistance = recent_high
        
        return (round(support, 2), round(resistance, 2))


def analyze_stock(symbol: str, name: str = "") -> StockAnalysis:
    """分析单只股票（便捷函数）"""
    analyzer = StockAnalyzer(symbol, name)
    return analyzer.analyze()


def print_analysis(result: StockAnalysis):
    """打印分析结果"""
    print(f"\n{'='*60}")
    print(f"【{result.symbol} {result.name}】 ¥{result.price:.2f} ({result.change_pct:+.2f}%)")
    print(f"{'='*60}")
    
    print(f"\n【均线位置】")
    print(f"  MA5:  {result.ma5:.2f}  {'▲' if result.above_ma5 else '▼'}")
    print(f"  MA10: {result.ma10:.2f}  {'▲' if result.above_ma10 else '▼'}")
    print(f"  MA20: {result.ma20:.2f}  {'▲' if result.above_ma20 else '▼'}")
    print(f"  MA60: {result.ma60:.2f}  {'▲' if result.above_ma60 else '▼'}")
    print(f"  趋势: {result.ma_trend}")
    
    print(f"\n【技术指标】")
    print(f"  MACD: {result.macd_status} (DIF:{result.macd_dif:.3f} DEA:{result.macd_dea:.3f})")
    if result.macd_divergence != "无":
        print(f"        ⚠️ {result.macd_divergence}")
    print(f"  RSI:  {result.rsi:.1f} - {result.rsi_status}")
    print(f"  KDJ:  K:{result.k:.1f} D:{result.d:.1f} J:{result.j:.1f} - {result.kdj_status}")
    print(f"  BOLL: {result.boll_status} (位置:{result.boll_position:.0f}%)")
    print(f"  成交量: {result.volume_trend} (量比:{result.volume_ratio:.2f})")
    
    if result.bullish_signals:
        print(f"\n【多头信号】")
        for sig in result.bullish_signals:
            print(f"  ✅ {sig}")
    
    if result.bearish_signals:
        print(f"\n【空头信号】")
        for sig in result.bearish_signals:
            print(f"  ⚠️ {sig}")
    
    print(f"\n【综合评分】{result.score:+d} 分")
    print(f"【操作建议】{result.suggestion}")
    print(f"{'='*60}")
