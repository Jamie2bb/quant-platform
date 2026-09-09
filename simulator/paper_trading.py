"""
模拟交易系统
支持：下单、撤单、持仓管理、账户管理、交易记录
"""
import json
import os
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional
from enum import Enum
import pandas as pd
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.fetcher import DataFetcher


class OrderStatus(Enum):
    """订单状态"""
    PENDING = "pending"       # 挂单中
    FILLED = "filled"         # 已成交
    PARTIAL = "partial"       # 部分成交
    CANCELLED = "cancelled"   # 已撤销
    REJECTED = "rejected"     # 已拒绝


class OrderType(Enum):
    """订单类型"""
    MARKET = "market"         # 市价单
    LIMIT = "limit"           # 限价单
    STOP = "stop"             # 止损单
    STOP_LIMIT = "stop_limit" # 止损限价单


class OrderSide(Enum):
    """买卖方向"""
    BUY = "buy"
    SELL = "sell"


@dataclass
class Order:
    """订单"""
    order_id: str
    symbol: str
    side: str
    order_type: str
    quantity: int
    price: float = 0.0
    stop_price: float = 0.0
    filled_quantity: int = 0
    filled_price: float = 0.0
    status: str = "pending"
    create_time: str = ""
    update_time: str = ""
    note: str = ""
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "Order":
        return cls(**data)


@dataclass
class Position:
    """持仓"""
    symbol: str
    quantity: int
    cost_price: float
    current_price: float = 0.0
    frozen: int = 0  # 冻结数量（挂单中）
    
    @property
    def available(self) -> int:
        """可卖数量"""
        return self.quantity - self.frozen
    
    @property
    def market_value(self) -> float:
        """市值"""
        return self.quantity * self.current_price
    
    @property
    def profit(self) -> float:
        """浮动盈亏"""
        return (self.current_price - self.cost_price) * self.quantity
    
    @property
    def profit_pct(self) -> float:
        """盈亏比例"""
        if self.cost_price == 0:
            return 0
        return (self.current_price - self.cost_price) / self.cost_price
    
    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "quantity": self.quantity,
            "cost_price": self.cost_price,
            "current_price": self.current_price,
            "frozen": self.frozen,
            "available": self.available,
            "market_value": self.market_value,
            "profit": self.profit,
            "profit_pct": self.profit_pct
        }


@dataclass
class Account:
    """账户"""
    total_cash: float = 0.0
    available_cash: float = 0.0
    frozen_cash: float = 0.0
    total_market_value: float = 0.0
    total_profit: float = 0.0
    
    @property
    def total_assets(self) -> float:
        return self.total_cash + self.total_market_value


class PaperTrader:
    """
    模拟交易器
    
    功能：
    - 模拟下单（市价/限价）
    - 实时更新持仓
    - 账户资金管理
    - 交易记录
    - 持久化存储
    """
    
    def __init__(
        self,
        initial_cash: float = 1000000,
        commission: float = 0.0003,
        min_commission: float = 5.0,
        slippage: float = 0.001,
        data_dir: str = None
    ):
        self.commission = commission
        self.min_commission = min_commission
        self.slippage = slippage
        
        # 数据存储目录
        if data_dir is None:
            data_dir = os.path.join(os.path.dirname(__file__), "data")
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        
        # 账户
        self.account = Account(
            total_cash=initial_cash,
            available_cash=initial_cash
        )
        
        # 持仓
        self.positions: Dict[str, Position] = {}
        
        # 订单
        self.orders: Dict[str, Order] = {}
        self.order_counter = 0
        
        # 交易记录
        self.trade_history: List[Dict] = []
        
        # 尝试加载已有数据
        self._load_state()
    
    def _generate_order_id(self) -> str:
        """生成订单ID"""
        self.order_counter += 1
        return f"ORD{datetime.now().strftime('%Y%m%d%H%M%S')}{self.order_counter:04d}"
    
    def _get_current_price(self, symbol: str) -> float:
        """获取当前价格"""
        # 方法1：实时行情
        try:
            df = DataFetcher.get_realtime_quotes()
            row = df[df["symbol"] == symbol]
            if len(row) > 0:
                price = float(row.iloc[0]["price"])
                if price > 0:
                    return price
        except:
            pass
        
        # 方法2：获取最新收盘价（多次重试）
        for retry in range(3):
            try:
                df = DataFetcher.get_stock_daily(
                    symbol, 
                    (datetime.now() - pd.Timedelta(days=30)).strftime("%Y%m%d"),
                    max_retries=3
                )
                if len(df) > 0:
                    price = float(df.iloc[-1]["close"])
                    if price > 0:
                        return price
            except Exception as e:
                import time
                time.sleep(2)
                continue
        
        return 0
    
    def _calculate_commission(self, amount: float) -> float:
        """计算手续费"""
        fee = amount * self.commission
        return max(fee, self.min_commission)
    
    def update_prices(self):
        """更新所有持仓的当前价格"""
        if not self.positions:
            return
        
        try:
            df = DataFetcher.get_realtime_quotes()
            for symbol, pos in self.positions.items():
                row = df[df["symbol"] == symbol]
                if len(row) > 0:
                    pos.current_price = float(row.iloc[0]["price"])
        except Exception as e:
            print(f"更新价格失败: {e}")
        
        self._update_account()
    
    def _update_account(self):
        """更新账户信息"""
        total_mv = sum(pos.market_value for pos in self.positions.values())
        total_profit = sum(pos.profit for pos in self.positions.values())
        
        self.account.total_market_value = total_mv
        self.account.total_profit = total_profit
    
    def place_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        order_type: str = "market",
        price: float = None,
        stop_price: float = None,
        note: str = ""
    ) -> Order:
        """
        下单
        
        Args:
            symbol: 股票代码
            side: "buy" 或 "sell"
            quantity: 数量（必须是100的倍数）
            order_type: "market" 或 "limit"
            price: 限价单价格
            stop_price: 止损价
            note: 备注
        
        Returns:
            Order: 订单对象
        """
        # 验证
        if quantity <= 0 or quantity % 100 != 0:
            raise ValueError("数量必须是100的正整数倍")
        
        current_price = self._get_current_price(symbol)
        if current_price <= 0:
            raise ValueError(f"无法获取 {symbol} 的价格")
        
        # 市价单用当前价
        if order_type == "market":
            price = current_price
        
        # 创建订单
        order = Order(
            order_id=self._generate_order_id(),
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price or current_price,
            stop_price=stop_price or 0,
            create_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            update_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            note=note
        )
        
        # 检查资金/持仓
        if side == "buy":
            required = quantity * price * (1 + self.slippage) + self._calculate_commission(quantity * price)
            if required > self.account.available_cash:
                order.status = "rejected"
                order.note = f"资金不足：需要 {required:.2f}，可用 {self.account.available_cash:.2f}"
                self.orders[order.order_id] = order
                return order
            
            # 冻结资金
            self.account.available_cash -= required
            self.account.frozen_cash += required
            
        else:  # sell
            if symbol not in self.positions:
                order.status = "rejected"
                order.note = f"没有 {symbol} 的持仓"
                self.orders[order.order_id] = order
                return order
            
            pos = self.positions[symbol]
            if pos.available < quantity:
                order.status = "rejected"
                order.note = f"可卖数量不足：需要 {quantity}，可用 {pos.available}"
                self.orders[order.order_id] = order
                return order
            
            # 冻结持仓
            pos.frozen += quantity
        
        self.orders[order.order_id] = order
        
        # 市价单立即执行
        if order_type == "market":
            self._execute_order(order)
        
        self._save_state()
        return order
    
    def _execute_order(self, order: Order):
        """执行订单"""
        # 模拟滑点
        if order.side == "buy":
            exec_price = order.price * (1 + self.slippage)
        else:
            exec_price = order.price * (1 - self.slippage)
        
        commission = self._calculate_commission(order.quantity * exec_price)
        
        if order.side == "buy":
            # 解冻资金
            frozen = order.quantity * order.price * (1 + self.slippage) + self._calculate_commission(order.quantity * order.price)
            self.account.frozen_cash -= frozen
            
            # 实际扣款
            actual_cost = order.quantity * exec_price + commission
            self.account.total_cash -= actual_cost
            self.account.available_cash = self.account.total_cash - self.account.frozen_cash
            
            # 更新持仓
            if order.symbol in self.positions:
                pos = self.positions[order.symbol]
                total_cost = pos.cost_price * pos.quantity + exec_price * order.quantity
                pos.quantity += order.quantity
                pos.cost_price = total_cost / pos.quantity
            else:
                self.positions[order.symbol] = Position(
                    symbol=order.symbol,
                    quantity=order.quantity,
                    cost_price=exec_price,
                    current_price=exec_price
                )
        
        else:  # sell
            pos = self.positions[order.symbol]
            
            # 解冻持仓
            pos.frozen -= order.quantity
            
            # 卖出收入
            revenue = order.quantity * exec_price - commission
            self.account.total_cash += revenue
            self.account.available_cash = self.account.total_cash - self.account.frozen_cash
            
            # 更新持仓
            pos.quantity -= order.quantity
            if pos.quantity <= 0:
                del self.positions[order.symbol]
        
        # 更新订单
        order.filled_quantity = order.quantity
        order.filled_price = exec_price
        order.status = "filled"
        order.update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 记录交易
        self.trade_history.append({
            "time": order.update_time,
            "order_id": order.order_id,
            "symbol": order.symbol,
            "side": order.side,
            "quantity": order.quantity,
            "price": exec_price,
            "commission": commission,
            "amount": order.quantity * exec_price,
            "note": order.note
        })
        
        self._update_account()
    
    def cancel_order(self, order_id: str) -> bool:
        """撤销订单"""
        if order_id not in self.orders:
            return False
        
        order = self.orders[order_id]
        if order.status != "pending":
            return False
        
        # 解冻
        if order.side == "buy":
            frozen = order.quantity * order.price * (1 + self.slippage) + self._calculate_commission(order.quantity * order.price)
            self.account.frozen_cash -= frozen
            self.account.available_cash += frozen
        else:
            pos = self.positions.get(order.symbol)
            if pos:
                pos.frozen -= order.quantity
        
        order.status = "cancelled"
        order.update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        self._save_state()
        return True
    
    def buy(self, symbol: str, quantity: int, price: float = None, note: str = "") -> Order:
        """买入快捷方法"""
        order_type = "limit" if price else "market"
        return self.place_order(symbol, "buy", quantity, order_type, price, note=note)
    
    def sell(self, symbol: str, quantity: int, price: float = None, note: str = "") -> Order:
        """卖出快捷方法"""
        order_type = "limit" if price else "market"
        return self.place_order(symbol, "sell", quantity, order_type, price, note=note)
    
    def sell_all(self, symbol: str, note: str = "") -> Order:
        """清仓"""
        if symbol not in self.positions:
            raise ValueError(f"没有 {symbol} 的持仓")
        return self.sell(symbol, self.positions[symbol].available, note=note)
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """获取持仓"""
        return self.positions.get(symbol)
    
    def get_all_positions(self) -> List[Dict]:
        """获取所有持仓"""
        self.update_prices()
        return [pos.to_dict() for pos in self.positions.values()]
    
    def get_account(self) -> Dict:
        """获取账户信息"""
        self._update_account()
        return {
            "total_cash": self.account.total_cash,
            "available_cash": self.account.available_cash,
            "frozen_cash": self.account.frozen_cash,
            "total_market_value": self.account.total_market_value,
            "total_assets": self.account.total_assets,
            "total_profit": self.account.total_profit
        }
    
    def get_orders(self, status: str = None) -> List[Dict]:
        """获取订单列表"""
        orders = list(self.orders.values())
        if status:
            orders = [o for o in orders if o.status == status]
        return [o.to_dict() for o in orders]
    
    def get_trade_history(self) -> pd.DataFrame:
        """获取交易记录"""
        return pd.DataFrame(self.trade_history)
    
    def summary(self):
        """输出账户摘要"""
        self.update_prices()
        acc = self.get_account()
        
        print("\n" + "=" * 60)
        print("模拟交易账户")
        print("=" * 60)
        
        print(f"\n【账户资产】")
        print(f"  总资产:         {acc['total_assets']:>15,.2f}")
        print(f"  总现金:         {acc['total_cash']:>15,.2f}")
        print(f"  可用资金:       {acc['available_cash']:>15,.2f}")
        print(f"  冻结资金:       {acc['frozen_cash']:>15,.2f}")
        print(f"  持仓市值:       {acc['total_market_value']:>15,.2f}")
        print(f"  浮动盈亏:       {acc['total_profit']:>15,.2f}")
        
        if self.positions:
            print(f"\n【持仓明细】")
            print("-" * 60)
            print(f"{'代码':<10}{'数量':>8}{'成本':>10}{'现价':>10}{'盈亏':>12}{'收益率':>10}")
            print("-" * 60)
            for pos in self.positions.values():
                print(f"{pos.symbol:<10}{pos.quantity:>8}{pos.cost_price:>10.2f}"
                      f"{pos.current_price:>10.2f}{pos.profit:>12.2f}{pos.profit_pct:>9.2%}")
        
        print("\n" + "=" * 60)
    
    def _save_state(self):
        """保存状态到文件"""
        state = {
            "account": {
                "total_cash": self.account.total_cash,
                "available_cash": self.account.available_cash,
                "frozen_cash": self.account.frozen_cash
            },
            "positions": {s: {"symbol": p.symbol, "quantity": p.quantity, 
                            "cost_price": p.cost_price, "frozen": p.frozen}
                         for s, p in self.positions.items()},
            "orders": {oid: o.to_dict() for oid, o in self.orders.items()},
            "order_counter": self.order_counter,
            "trade_history": self.trade_history
        }
        
        path = os.path.join(self.data_dir, "paper_trading_state.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    
    def _load_state(self):
        """从文件加载状态"""
        path = os.path.join(self.data_dir, "paper_trading_state.json")
        if not os.path.exists(path):
            return
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                state = json.load(f)
            
            acc = state.get("account", {})
            self.account.total_cash = acc.get("total_cash", self.account.total_cash)
            self.account.available_cash = acc.get("available_cash", self.account.available_cash)
            self.account.frozen_cash = acc.get("frozen_cash", 0)
            
            for s, p in state.get("positions", {}).items():
                self.positions[s] = Position(
                    symbol=p["symbol"],
                    quantity=p["quantity"],
                    cost_price=p["cost_price"],
                    frozen=p.get("frozen", 0)
                )
            
            for oid, o in state.get("orders", {}).items():
                self.orders[oid] = Order.from_dict(o)
            
            self.order_counter = state.get("order_counter", 0)
            self.trade_history = state.get("trade_history", [])
            
            print(f"已加载模拟交易状态，持仓 {len(self.positions)} 只股票")
            
        except Exception as e:
            print(f"加载状态失败: {e}")
    
    def reset(self, initial_cash: float = None):
        """重置账户"""
        if initial_cash is None:
            initial_cash = 1000000
        
        self.account = Account(
            total_cash=initial_cash,
            available_cash=initial_cash
        )
        self.positions = {}
        self.orders = {}
        self.order_counter = 0
        self.trade_history = []
        
        self._save_state()
        print(f"账户已重置，初始资金: {initial_cash:,.2f}")
