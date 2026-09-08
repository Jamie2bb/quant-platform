"""
策略信号提醒
"""
import pandas as pd
from datetime import datetime
from typing import List, Dict, Type
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.fetcher import DataFetcher
from strategy.base import BaseStrategy


class SignalAlert:
    """
    策略信号提醒
    
    监控指定股票是否触发策略买卖信号
    """
    
    def __init__(self, strategy: BaseStrategy):
        self.strategy = strategy
        self.watchlist: List[str] = []
    
    def add_stock(self, symbol: str):
        """添加监控股票"""
        if symbol not in self.watchlist:
            self.watchlist.append(symbol)
        return self
    
    def add_stocks(self, symbols: List[str]):
        """批量添加"""
        for s in symbols:
            self.add_stock(s)
        return self
    
    def check_signals(self, lookback_days: int = 60) -> Dict[str, Dict]:
        """
        检查所有股票的策略信号
        
        Args:
            lookback_days: 回看天数（获取足够的历史数据计算指标）
        
        Returns:
            Dict: {symbol: {"signal": 1/-1/0, "data": {...}}}
        """
        from datetime import timedelta
        
        start_date = (datetime.now() - timedelta(days=lookback_days)).strftime("%Y%m%d")
        
        results = {}
        
        for symbol in self.watchlist:
            try:
                # 获取数据
                df = DataFetcher.get_stock_daily(symbol, start_date)
                
                if len(df) < 20:
                    continue
                
                # 应用策略
                self.strategy.set_data(df)
                signals = self.strategy.generate_signals()
                
                # 取最后一个信号
                last_signal = signals.iloc[-1]
                prev_signal = signals.iloc[-2] if len(signals) > 1 else 0
                
                # 判断是否刚触发
                is_new_signal = (last_signal != 0 and prev_signal == 0)
                
                results[symbol] = {
                    "signal": int(last_signal),
                    "is_new": is_new_signal,
                    "price": df["close"].iloc[-1],
                    "date": df.index[-1],
                    "strategy": self.strategy.name
                }
                
            except Exception as e:
                print(f"检查 {symbol} 失败: {e}")
                continue
        
        return results
    
    def get_buy_signals(self, lookback_days: int = 60) -> List[Dict]:
        """获取买入信号的股票"""
        results = self.check_signals(lookback_days)
        
        buy_list = []
        for symbol, data in results.items():
            if data["signal"] == 1:
                buy_list.append({
                    "symbol": symbol,
                    **data
                })
        
        return buy_list
    
    def get_sell_signals(self, lookback_days: int = 60) -> List[Dict]:
        """获取卖出信号的股票"""
        results = self.check_signals(lookback_days)
        
        sell_list = []
        for symbol, data in results.items():
            if data["signal"] == -1:
                sell_list.append({
                    "symbol": symbol,
                    **data
                })
        
        return sell_list
    
    def report(self, lookback_days: int = 60):
        """输出信号报告"""
        results = self.check_signals(lookback_days)
        
        print("\n" + "=" * 60)
        print(f"策略信号报告 - {self.strategy.name}")
        print(f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        buy_signals = []
        sell_signals = []
        
        for symbol, data in results.items():
            if data["signal"] == 1:
                buy_signals.append((symbol, data))
            elif data["signal"] == -1:
                sell_signals.append((symbol, data))
        
        if buy_signals:
            print(f"\n【买入信号】({len(buy_signals)} 只)")
            for symbol, data in buy_signals:
                new_mark = " ★新" if data["is_new"] else ""
                print(f"  {symbol} 价格:{data['price']:.2f}{new_mark}")
        else:
            print("\n【买入信号】无")
        
        if sell_signals:
            print(f"\n【卖出信号】({len(sell_signals)} 只)")
            for symbol, data in sell_signals:
                new_mark = " ★新" if data["is_new"] else ""
                print(f"  {symbol} 价格:{data['price']:.2f}{new_mark}")
        else:
            print("\n【卖出信号】无")
        
        print("\n" + "=" * 60)


def scan_market_signals(strategy: BaseStrategy, 
                        symbols: List[str] = None,
                        max_stocks: int = 100) -> Dict[str, List]:
    """
    全市场扫描策略信号
    
    Args:
        strategy: 策略实例
        symbols: 股票列表，None 则使用热门股票
        max_stocks: 最大扫描数量
    
    Returns:
        {"buy": [...], "sell": [...]}
    """
    if symbols is None:
        # 默认扫描一些热门股票
        symbols = [
            "000001", "000002", "000063", "000333", "000651",
            "000725", "000858", "002230", "002415", "002594",
            "300059", "300124", "300750", "600000", "600009",
            "600019", "600028", "600030", "600036", "600048",
            "600050", "600104", "600276", "600309", "600519",
            "600585", "600690", "600703", "600887", "601012",
            "601088", "601166", "601318", "601398", "601601",
            "601628", "601668", "601688", "601857", "601888",
        ]
    
    symbols = symbols[:max_stocks]
    
    alert = SignalAlert(strategy)
    alert.add_stocks(symbols)
    
    results = alert.check_signals()
    
    buy_list = [{"symbol": s, **d} for s, d in results.items() if d["signal"] == 1]
    sell_list = [{"symbol": s, **d} for s, d in results.items() if d["signal"] == -1]
    
    return {"buy": buy_list, "sell": sell_list}
