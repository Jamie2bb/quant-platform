# -*- coding: utf-8 -*-
"""
持仓监控器 - 监控止损止盈、技术信号
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum

from data.fetcher import DataFetcher
from utils.indicators import SMA, RSI, MACD, KDJ
from .config import load_holdings, StopRules, TechRules


class AlertLevel(Enum):
    INFO = "信息"
    WARNING = "警告"
    DANGER = "危险"
    OPPORTUNITY = "机会"


@dataclass
class Alert:
    """提醒信息"""
    symbol: str
    name: str
    level: AlertLevel
    type: str
    message: str
    current_price: float = 0
    trigger_value: float = 0
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@dataclass
class HoldingStatus:
    """持仓状态"""
    symbol: str
    name: str
    cost_price: float = 0
    current_price: float = 0
    change_pct: float = 0
    profit_pct: float = 0
    highest_price: float = 0  # 持仓期间最高价
    lowest_price: float = 0   # 持仓期间最低价
    alerts: List[Alert] = field(default_factory=list)


class PortfolioMonitor:
    """持仓监控器"""
    
    def __init__(self):
        self.holdings = load_holdings()
        self.status: Dict[str, HoldingStatus] = {}
        self.alerts: List[Alert] = []
        
        # 加载保存的状态（最高价、买入价等）
        self._load_state()
    
    def _get_state_file(self) -> str:
        return os.path.join(os.path.dirname(__file__), "portfolio_state.json")
    
    def _load_state(self):
        """加载保存的状态"""
        state_file = self._get_state_file()
        if os.path.exists(state_file):
            try:
                with open(state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for symbol, state in data.items():
                        self.status[symbol] = HoldingStatus(
                            symbol=symbol,
                            name=state.get("name", ""),
                            cost_price=state.get("cost_price", 0),
                            highest_price=state.get("highest_price", 0),
                            lowest_price=state.get("lowest_price", 0)
                        )
            except Exception as e:
                print(f"加载状态失败: {e}")
    
    def _save_state(self):
        """保存状态"""
        state_file = self._get_state_file()
        data = {}
        for symbol, status in self.status.items():
            data[symbol] = {
                "name": status.name,
                "cost_price": status.cost_price,
                "highest_price": status.highest_price,
                "lowest_price": status.lowest_price
            }
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def set_cost_price(self, symbol: str, cost_price: float):
        """设置买入成本价"""
        if symbol not in self.status:
            holding = next((h for h in self.holdings if h["code"] == symbol), None)
            name = holding["name"] if holding else ""
            self.status[symbol] = HoldingStatus(symbol=symbol, name=name)
        
        self.status[symbol].cost_price = cost_price
        self._save_state()
        print(f"已设置 {symbol} 成本价: {cost_price}")
    
    def refresh_holdings(self):
        """刷新持仓列表"""
        self.holdings = load_holdings()
    
    def check_all(self) -> List[Alert]:
        """检查所有持仓"""
        self.alerts = []
        
        print(f"\n正在检查 {len(self.holdings)} 只持仓股票...")
        
        for holding in self.holdings:
            symbol = holding["code"]
            name = holding.get("name", "")
            
            try:
                alerts = self._check_single(symbol, name)
                self.alerts.extend(alerts)
            except Exception as e:
                print(f"  检查 {symbol} {name} 失败: {e}")
        
        self._save_state()
        return self.alerts
    
    def _check_single(self, symbol: str, name: str) -> List[Alert]:
        """检查单只股票"""
        alerts = []
        
        # 获取历史数据
        start_date = (datetime.now() - timedelta(days=120)).strftime("%Y%m%d")
        df = DataFetcher.get_stock_daily(symbol, start_date)
        
        if len(df) < 60:
            return alerts
        
        current_price = df['close'].iloc[-1]
        change_pct = df['pct_change'].iloc[-1] if 'pct_change' in df.columns else 0
        
        # 更新状态
        if symbol not in self.status:
            self.status[symbol] = HoldingStatus(symbol=symbol, name=name)
        
        status = self.status[symbol]
        status.name = name
        status.current_price = current_price
        status.change_pct = change_pct
        
        # 更新最高价、最低价
        if status.highest_price == 0 or current_price > status.highest_price:
            status.highest_price = current_price
        if status.lowest_price == 0 or current_price < status.lowest_price:
            status.lowest_price = current_price
        
        # 计算盈亏
        if status.cost_price > 0:
            status.profit_pct = (current_price - status.cost_price) / status.cost_price * 100
        
        print(f"  {symbol} {name}: ¥{current_price:.2f} ({change_pct:+.2f}%)", end="")
        if status.cost_price > 0:
            print(f" 盈亏:{status.profit_pct:+.2f}%", end="")
        print()
        
        # ========== 止损止盈检查 ==========
        
        # 固定止损
        if status.cost_price > 0:
            loss_pct = (status.cost_price - current_price) / status.cost_price * 100
            if loss_pct >= StopRules.STOP_LOSS_PCT:
                alerts.append(Alert(
                    symbol=symbol, name=name,
                    level=AlertLevel.DANGER,
                    type="止损",
                    message=f"已亏损 {loss_pct:.1f}%，触发 {StopRules.STOP_LOSS_PCT}% 止损线",
                    current_price=current_price,
                    trigger_value=status.cost_price * (1 - StopRules.STOP_LOSS_PCT / 100)
                ))
            
            # 固定止盈
            if status.profit_pct >= StopRules.TAKE_PROFIT_PCT:
                alerts.append(Alert(
                    symbol=symbol, name=name,
                    level=AlertLevel.OPPORTUNITY,
                    type="止盈",
                    message=f"已盈利 {status.profit_pct:.1f}%，达到 {StopRules.TAKE_PROFIT_PCT}% 止盈线",
                    current_price=current_price,
                    trigger_value=status.cost_price * (1 + StopRules.TAKE_PROFIT_PCT / 100)
                ))
        
        # 移动止盈（从最高点回撤）
        if status.highest_price > 0 and status.profit_pct > 0:
            drawdown = (status.highest_price - current_price) / status.highest_price * 100
            if drawdown >= StopRules.TRAILING_STOP_PCT:
                alerts.append(Alert(
                    symbol=symbol, name=name,
                    level=AlertLevel.WARNING,
                    type="移动止盈",
                    message=f"从最高点 ¥{status.highest_price:.2f} 回撤 {drawdown:.1f}%",
                    current_price=current_price,
                    trigger_value=status.highest_price * (1 - StopRules.TRAILING_STOP_PCT / 100)
                ))
        
        # ========== 均线破位检查 ==========
        
        for period in StopRules.MA_STOP_PERIODS:
            if len(df) >= period:
                ma = df['close'].rolling(period).mean().iloc[-1]
                prev_close = df['close'].iloc[-2]
                prev_ma = df['close'].rolling(period).mean().iloc[-2]
                
                # 今日跌破均线
                if prev_close >= prev_ma and current_price < ma:
                    alerts.append(Alert(
                        symbol=symbol, name=name,
                        level=AlertLevel.WARNING,
                        type="破位",
                        message=f"跌破 {period} 日均线 ¥{ma:.2f}",
                        current_price=current_price,
                        trigger_value=ma
                    ))
                
                # 今日突破均线
                elif prev_close < prev_ma and current_price > ma:
                    alerts.append(Alert(
                        symbol=symbol, name=name,
                        level=AlertLevel.OPPORTUNITY,
                        type="突破",
                        message=f"突破 {period} 日均线 ¥{ma:.2f}",
                        current_price=current_price,
                        trigger_value=ma
                    ))
        
        # ========== 技术指标检查 ==========
        
        # MACD 金叉/死叉
        dif, dea, _ = MACD(df['close'])
        if dif.iloc[-1] > dea.iloc[-1] and dif.iloc[-2] <= dea.iloc[-2]:
            alerts.append(Alert(
                symbol=symbol, name=name,
                level=AlertLevel.OPPORTUNITY,
                type="MACD",
                message="MACD 金叉",
                current_price=current_price
            ))
        elif dif.iloc[-1] < dea.iloc[-1] and dif.iloc[-2] >= dea.iloc[-2]:
            alerts.append(Alert(
                symbol=symbol, name=name,
                level=AlertLevel.WARNING,
                type="MACD",
                message="MACD 死叉",
                current_price=current_price
            ))
        
        # RSI 超买超卖
        rsi = RSI(df['close'], 14).iloc[-1]
        if rsi > TechRules.RSI_OVERBOUGHT:
            alerts.append(Alert(
                symbol=symbol, name=name,
                level=AlertLevel.WARNING,
                type="RSI",
                message=f"RSI 超买 ({rsi:.1f})",
                current_price=current_price,
                trigger_value=rsi
            ))
        elif rsi < TechRules.RSI_OVERSOLD:
            alerts.append(Alert(
                symbol=symbol, name=name,
                level=AlertLevel.OPPORTUNITY,
                type="RSI",
                message=f"RSI 超卖 ({rsi:.1f})",
                current_price=current_price,
                trigger_value=rsi
            ))
        
        # KDJ 超买超卖
        k, d, j = KDJ(df['high'], df['low'], df['close'])
        if k.iloc[-1] > TechRules.KDJ_OVERBOUGHT and d.iloc[-1] > TechRules.KDJ_OVERBOUGHT:
            alerts.append(Alert(
                symbol=symbol, name=name,
                level=AlertLevel.WARNING,
                type="KDJ",
                message=f"KDJ 超买区 (K:{k.iloc[-1]:.0f} D:{d.iloc[-1]:.0f})",
                current_price=current_price
            ))
        elif k.iloc[-1] < TechRules.KDJ_OVERSOLD and d.iloc[-1] < TechRules.KDJ_OVERSOLD:
            alerts.append(Alert(
                symbol=symbol, name=name,
                level=AlertLevel.OPPORTUNITY,
                type="KDJ",
                message=f"KDJ 超卖区 (K:{k.iloc[-1]:.0f} D:{d.iloc[-1]:.0f})",
                current_price=current_price
            ))
        
        status.alerts = alerts
        return alerts
    
    def print_alerts(self):
        """打印提醒信息"""
        if not self.alerts:
            print("\n✅ 当前无需关注的提醒")
            return
        
        print(f"\n{'='*70}")
        print(f"⚠️  持仓提醒 ({len(self.alerts)} 条)  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"{'='*70}")
        
        # 按级别分组
        danger_alerts = [a for a in self.alerts if a.level == AlertLevel.DANGER]
        warning_alerts = [a for a in self.alerts if a.level == AlertLevel.WARNING]
        opportunity_alerts = [a for a in self.alerts if a.level == AlertLevel.OPPORTUNITY]
        
        if danger_alerts:
            print(f"\n🔴 【危险】")
            for alert in danger_alerts:
                print(f"   {alert.symbol} {alert.name}: {alert.message}")
                print(f"      当前价: ¥{alert.current_price:.2f}")
        
        if warning_alerts:
            print(f"\n🟡 【警告】")
            for alert in warning_alerts:
                print(f"   {alert.symbol} {alert.name}: {alert.message}")
                print(f"      当前价: ¥{alert.current_price:.2f}")
        
        if opportunity_alerts:
            print(f"\n🟢 【机会】")
            for alert in opportunity_alerts:
                print(f"   {alert.symbol} {alert.name}: {alert.message}")
                print(f"      当前价: ¥{alert.current_price:.2f}")
        
        print(f"\n{'='*70}")
    
    def print_status(self):
        """打印持仓状态汇总"""
        if not self.status:
            print("\n暂无持仓数据")
            return
        
        print(f"\n{'='*70}")
        print(f"📊 持仓状态汇总  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"{'='*70}")
        print(f"{'代码':<10}{'名称':<10}{'现价':>10}{'涨跌':>8}{'成本':>10}{'盈亏':>10}")
        print(f"{'-'*70}")
        
        total_profit_pct = 0
        count_with_cost = 0
        
        for symbol, status in self.status.items():
            cost_str = f"¥{status.cost_price:.2f}" if status.cost_price > 0 else "-"
            profit_str = f"{status.profit_pct:+.2f}%" if status.cost_price > 0 else "-"
            
            print(f"{status.symbol:<10}{status.name:<10}"
                  f"¥{status.current_price:>8.2f}{status.change_pct:>+7.2f}%"
                  f"{cost_str:>10}{profit_str:>10}")
            
            if status.cost_price > 0:
                total_profit_pct += status.profit_pct
                count_with_cost += 1
        
        if count_with_cost > 0:
            avg_profit = total_profit_pct / count_with_cost
            print(f"{'-'*70}")
            print(f"{'平均盈亏':>50}{avg_profit:>+10.2f}%")
        
        print(f"{'='*70}")


def run_monitor():
    """运行监控（便捷函数）"""
    monitor = PortfolioMonitor()
    monitor.check_all()
    monitor.print_status()
    monitor.print_alerts()
    return monitor
