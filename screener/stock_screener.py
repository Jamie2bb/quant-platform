"""
选股器 - 从全市场筛选符合条件的股票
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Callable, Any
from datetime import datetime
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.fetcher import DataFetcher
from utils.indicators import SMA, EMA, RSI, MACD, KDJ, ATR


class StockScreener:
    """
    股票筛选器
    
    支持多种筛选条件组合
    """
    
    def __init__(self):
        self.conditions = []
        self._realtime_data = None
    
    def add_condition(self, condition: Callable[[pd.Series], bool], name: str = ""):
        """添加筛选条件"""
        self.conditions.append({"func": condition, "name": name})
        return self
    
    def clear_conditions(self):
        """清空条件"""
        self.conditions = []
        return self
    
    # ===== 预设条件 =====
    
    def price_range(self, min_price: float = 0, max_price: float = 9999):
        """价格区间"""
        def condition(row):
            return min_price <= row.get("price", 0) <= max_price
        self.add_condition(condition, f"价格 {min_price}-{max_price}")
        return self
    
    def pct_change_range(self, min_pct: float = -100, max_pct: float = 100):
        """涨跌幅区间（百分比）"""
        def condition(row):
            pct = row.get("pct_change", 0)
            return min_pct <= pct <= max_pct
        self.add_condition(condition, f"涨跌幅 {min_pct}%-{max_pct}%")
        return self
    
    def turnover_min(self, min_turnover: float):
        """最小换手率"""
        def condition(row):
            return row.get("turnover", 0) >= min_turnover
        self.add_condition(condition, f"换手率 >= {min_turnover}%")
        return self
    
    def volume_min(self, min_volume: float):
        """最小成交量（手）"""
        def condition(row):
            return row.get("volume", 0) >= min_volume
        self.add_condition(condition, f"成交量 >= {min_volume}")
        return self
    
    def amount_min(self, min_amount: float):
        """最小成交额（元）"""
        def condition(row):
            return row.get("amount", 0) >= min_amount
        self.add_condition(condition, f"成交额 >= {min_amount/10000:.0f}万")
        return self
    
    def pe_range(self, min_pe: float = 0, max_pe: float = 9999):
        """市盈率区间"""
        def condition(row):
            pe = row.get("pe", 0)
            if pd.isna(pe) or pe <= 0:
                return False
            return min_pe <= pe <= max_pe
        self.add_condition(condition, f"PE {min_pe}-{max_pe}")
        return self
    
    def pb_range(self, min_pb: float = 0, max_pb: float = 9999):
        """市净率区间"""
        def condition(row):
            pb = row.get("pb", 0)
            if pd.isna(pb) or pb <= 0:
                return False
            return min_pb <= pb <= max_pb
        self.add_condition(condition, f"PB {min_pb}-{max_pb}")
        return self
    
    def exclude_st(self):
        """排除 ST 股票"""
        def condition(row):
            name = row.get("name", "")
            return "ST" not in name and "st" not in name
        self.add_condition(condition, "排除ST")
        return self
    
    def exclude_new(self, days: int = 60):
        """排除次新股（上市不足N天）"""
        # 这个需要额外数据，暂时用名称简单过滤
        def condition(row):
            name = row.get("name", "")
            return "N" not in name and "C" not in name
        self.add_condition(condition, f"排除次新股")
        return self
    
    def main_board_only(self):
        """仅主板（排除创业板、科创板、北交所）"""
        def condition(row):
            symbol = str(row.get("symbol", ""))
            # 创业板 300xxx，科创板 688xxx，北交所 8xxxxx/4xxxxx
            if symbol.startswith("300") or symbol.startswith("688"):
                return False
            if symbol.startswith("8") or symbol.startswith("4"):
                return False
            return True
        self.add_condition(condition, "仅主板")
        return self
    
    # ===== 技术指标条件（需要历史数据）=====
    
    def ma_bullish(self, symbol: str, periods: List[int] = [5, 10, 20]) -> bool:
        """判断是否多头排列"""
        try:
            df = DataFetcher.get_stock_daily(symbol, 
                datetime.now().strftime("%Y%m%d")[:4] + "0101")
            if len(df) < max(periods):
                return False
            
            mas = [df["close"].rolling(p).mean().iloc[-1] for p in periods]
            # 检查是否递减排列
            return all(mas[i] >= mas[i+1] for i in range(len(mas)-1))
        except:
            return False
    
    def rsi_oversold(self, symbol: str, period: int = 14, threshold: int = 30) -> bool:
        """判断 RSI 是否超卖"""
        try:
            df = DataFetcher.get_stock_daily(symbol,
                datetime.now().strftime("%Y%m%d")[:4] + "0101")
            if len(df) < period + 5:
                return False
            
            rsi = RSI(df["close"], period)
            return rsi.iloc[-1] < threshold
        except:
            return False
    
    def macd_golden(self, symbol: str) -> bool:
        """判断 MACD 是否金叉"""
        try:
            df = DataFetcher.get_stock_daily(symbol,
                datetime.now().strftime("%Y%m%d")[:4] + "0101")
            if len(df) < 35:
                return False
            
            dif, dea, macd = MACD(df["close"])
            # 今日 DIF > DEA 且 昨日 DIF <= DEA
            return dif.iloc[-1] > dea.iloc[-1] and dif.iloc[-2] <= dea.iloc[-2]
        except:
            return False
    
    # ===== 执行筛选 =====
    
    def screen(self, use_cache: bool = True) -> pd.DataFrame:
        """
        执行筛选
        
        Returns:
            DataFrame: 符合条件的股票列表
        """
        print("获取全市场实时行情...")
        
        try:
            df = DataFetcher.get_realtime_quotes()
        except Exception as e:
            print(f"获取实时行情失败: {e}")
            print("尝试使用股票列表...")
            df = DataFetcher.get_stock_list()
            df["price"] = 0
            df["pct_change"] = 0
        
        print(f"共 {len(df)} 只股票")
        
        if len(self.conditions) == 0:
            print("未设置筛选条件，返回全部")
            return df
        
        # 应用筛选条件
        results = []
        
        for _, row in df.iterrows():
            row_dict = row.to_dict()
            
            passed = True
            for cond in self.conditions:
                if not cond["func"](row_dict):
                    passed = False
                    break
            
            if passed:
                results.append(row_dict)
        
        result_df = pd.DataFrame(results)
        print(f"筛选完成，符合条件: {len(result_df)} 只")
        
        return result_df
    
    def screen_with_technical(self, symbols: List[str], 
                               technical_filter: Callable[[str], bool]) -> List[str]:
        """
        对股票列表进行技术指标筛选（需要逐个获取历史数据，较慢）
        
        Args:
            symbols: 股票代码列表
            technical_filter: 技术指标过滤函数，如 self.ma_bullish
        
        Returns:
            符合条件的股票代码列表
        """
        results = []
        total = len(symbols)
        
        for i, symbol in enumerate(symbols):
            if (i + 1) % 10 == 0:
                print(f"技术筛选进度: {i + 1}/{total}")
            
            try:
                if technical_filter(symbol):
                    results.append(symbol)
            except:
                continue
        
        print(f"技术筛选完成，符合条件: {len(results)} 只")
        return results


# ===== 预设筛选器 =====

def create_value_screener() -> StockScreener:
    """价值股筛选器"""
    return (StockScreener()
            .exclude_st()
            .price_range(5, 50)
            .pe_range(0, 30)
            .pb_range(0, 3)
            .amount_min(50000000))  # 5000万成交额


def create_growth_screener() -> StockScreener:
    """成长股筛选器"""
    return (StockScreener()
            .exclude_st()
            .price_range(10, 100)
            .pct_change_range(0, 5)
            .turnover_min(3)
            .amount_min(100000000))  # 1亿成交额


def create_momentum_screener() -> StockScreener:
    """动量股筛选器（强势股）"""
    return (StockScreener()
            .exclude_st()
            .pct_change_range(3, 9.9)
            .turnover_min(5)
            .amount_min(200000000))  # 2亿成交额


def create_oversold_screener() -> StockScreener:
    """超跌股筛选器"""
    return (StockScreener()
            .exclude_st()
            .pct_change_range(-9.9, -3)
            .turnover_min(2)
            .amount_min(50000000))
