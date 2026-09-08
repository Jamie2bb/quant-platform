"""
实时行情监控
"""
import time
import pandas as pd
from datetime import datetime
from typing import List, Dict, Callable, Optional
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.fetcher import DataFetcher


class RealtimeMonitor:
    """
    实时行情监控器
    
    监控指定股票的实时行情，触发条件时发出提醒
    """
    
    def __init__(self):
        self.watchlist: List[str] = []
        self.alerts: List[Dict] = []
        self.callbacks: List[Callable] = []
        self.last_data: Dict[str, Dict] = {}
    
    def add_stock(self, symbol: str):
        """添加监控股票"""
        if symbol not in self.watchlist:
            self.watchlist.append(symbol)
        return self
    
    def add_stocks(self, symbols: List[str]):
        """批量添加监控股票"""
        for s in symbols:
            self.add_stock(s)
        return self
    
    def remove_stock(self, symbol: str):
        """移除监控股票"""
        if symbol in self.watchlist:
            self.watchlist.remove(symbol)
        return self
    
    def add_alert(self, symbol: str, condition: str, value: float, 
                  message: str = "", callback: Callable = None):
        """
        添加提醒条件
        
        Args:
            symbol: 股票代码
            condition: 条件类型
                - "price_above": 价格高于
                - "price_below": 价格低于
                - "pct_above": 涨幅超过
                - "pct_below": 跌幅超过
                - "volume_above": 成交量超过
            value: 触发值
            message: 提醒消息
            callback: 触发时的回调函数
        """
        self.alerts.append({
            "symbol": symbol,
            "condition": condition,
            "value": value,
            "message": message,
            "callback": callback,
            "triggered": False
        })
        
        if symbol not in self.watchlist:
            self.watchlist.append(symbol)
        
        return self
    
    def price_alert(self, symbol: str, target_price: float, direction: str = "above"):
        """价格提醒快捷方法"""
        condition = f"price_{direction}"
        message = f"{symbol} 价格{'突破' if direction == 'above' else '跌破'} {target_price}"
        return self.add_alert(symbol, condition, target_price, message)
    
    def pct_alert(self, symbol: str, target_pct: float):
        """涨跌幅提醒"""
        direction = "above" if target_pct > 0 else "below"
        condition = f"pct_{direction}"
        message = f"{symbol} 涨跌幅{'超过' if target_pct > 0 else '低于'} {target_pct}%"
        return self.add_alert(symbol, condition, target_pct, message)
    
    def _check_alert(self, alert: Dict, data: Dict) -> bool:
        """检查是否触发提醒"""
        if alert["triggered"]:
            return False
        
        condition = alert["condition"]
        value = alert["value"]
        
        if condition == "price_above":
            return data.get("price", 0) >= value
        elif condition == "price_below":
            return data.get("price", 0) <= value
        elif condition == "pct_above":
            return data.get("pct_change", 0) >= value
        elif condition == "pct_below":
            return data.get("pct_change", 0) <= value
        elif condition == "volume_above":
            return data.get("volume", 0) >= value
        
        return False
    
    def _fetch_realtime(self) -> Dict[str, Dict]:
        """获取监控股票的实时数据"""
        if not self.watchlist:
            return {}
        
        try:
            df = DataFetcher.get_realtime_quotes()
            
            result = {}
            for symbol in self.watchlist:
                row = df[df["symbol"] == symbol]
                if len(row) > 0:
                    result[symbol] = row.iloc[0].to_dict()
            
            return result
        except Exception as e:
            print(f"获取实时行情失败: {e}")
            return {}
    
    def check_once(self) -> List[Dict]:
        """检查一次，返回触发的提醒"""
        data = self._fetch_realtime()
        self.last_data = data
        
        triggered = []
        
        for alert in self.alerts:
            symbol = alert["symbol"]
            if symbol not in data:
                continue
            
            if self._check_alert(alert, data[symbol]):
                alert["triggered"] = True
                triggered.append({
                    "symbol": symbol,
                    "message": alert["message"],
                    "data": data[symbol],
                    "time": datetime.now()
                })
                
                # 执行回调
                if alert["callback"]:
                    alert["callback"](alert, data[symbol])
        
        return triggered
    
    def run(self, interval: int = 10, duration: int = None, 
            on_update: Callable = None, on_alert: Callable = None):
        """
        持续运行监控
        
        Args:
            interval: 刷新间隔（秒）
            duration: 运行时长（秒），None 表示一直运行
            on_update: 每次更新时的回调
            on_alert: 触发提醒时的回调
        """
        print(f"开始监控 {len(self.watchlist)} 只股票")
        print(f"刷新间隔: {interval}秒")
        print("按 Ctrl+C 停止\n")
        
        start_time = time.time()
        
        try:
            while True:
                if duration and time.time() - start_time > duration:
                    print("监控时间到，停止")
                    break
                
                # 检查是否在交易时间
                now = datetime.now()
                if not self._is_trading_time(now):
                    print(f"[{now.strftime('%H:%M:%S')}] 非交易时间，等待...")
                    time.sleep(60)
                    continue
                
                # 获取数据并检查提醒
                triggered = self.check_once()
                
                # 显示更新
                if on_update:
                    on_update(self.last_data)
                else:
                    self._print_status()
                
                # 处理提醒
                for alert in triggered:
                    print(f"\n🔔 提醒: {alert['message']}")
                    if on_alert:
                        on_alert(alert)
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n监控已停止")
    
    def _is_trading_time(self, now: datetime) -> bool:
        """判断是否交易时间"""
        # 周末不交易
        if now.weekday() >= 5:
            return False
        
        # 交易时间：9:30-11:30, 13:00-15:00
        hour, minute = now.hour, now.minute
        time_val = hour * 100 + minute
        
        if 930 <= time_val <= 1130 or 1300 <= time_val <= 1500:
            return True
        
        return False
    
    def _print_status(self):
        """打印当前状态"""
        now = datetime.now().strftime("%H:%M:%S")
        print(f"\n[{now}] 实时行情:")
        print("-" * 60)
        
        for symbol, data in self.last_data.items():
            price = data.get("price", 0)
            pct = data.get("pct_change", 0)
            name = data.get("name", symbol)
            
            arrow = "↑" if pct > 0 else ("↓" if pct < 0 else "-")
            color_pct = f"+{pct:.2f}%" if pct > 0 else f"{pct:.2f}%"
            
            print(f"  {symbol} {name:<8} {price:>8.2f}  {arrow} {color_pct}")
        
        print("-" * 60)
    
    def get_snapshot(self) -> pd.DataFrame:
        """获取当前快照"""
        if not self.last_data:
            self.check_once()
        
        return pd.DataFrame(self.last_data.values())
