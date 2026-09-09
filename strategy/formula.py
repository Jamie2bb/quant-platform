# -*- coding: utf-8 -*-
"""
公式策略系统 - 类似通达信/同花顺的公式编写
支持用简单的表达式定义买卖条件
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, Callable, List
import re

from .base import BaseStrategy

# 导入所有指标函数到全局命名空间
from utils.indicators_pro import *


class FormulaStrategy(BaseStrategy):
    """
    公式策略
    
    使用类似通达信的公式语法定义买卖条件
    
    示例:
        # 双均线金叉
        strategy = FormulaStrategy(
            buy_formula="CROSS(MA(C,5), MA(C,20))",
            sell_formula="CROSS(MA(C,20), MA(C,5))",
            name="双均线金叉"
        )
        
        # MACD金叉+RSI超卖
        strategy = FormulaStrategy(
            buy_formula="CROSS(DIF, DEA) AND RSI(C,14) < 40",
            sell_formula="CROSS(DEA, DIF)",
            name="MACD+RSI"
        )
    """
    
    # 变量别名（兼容通达信语法）
    ALIASES = {
        'C': 'close',
        'O': 'open', 
        'H': 'high',
        'L': 'low',
        'V': 'volume',
        'VOL': 'volume',
        'CLOSE': 'close',
        'OPEN': 'open',
        'HIGH': 'high',
        'LOW': 'low',
    }
    
    def __init__(self, buy_formula: str, sell_formula: str, name: str = "公式策略"):
        super().__init__(name)
        self.buy_formula = buy_formula
        self.sell_formula = sell_formula
        self._compiled_buy = None
        self._compiled_sell = None
    
    def _preprocess_formula(self, formula: str) -> str:
        """预处理公式，替换别名"""
        result = formula
        
        # 替换逻辑运算符
        result = result.replace(' AND ', ' & ')
        result = result.replace(' and ', ' & ')
        result = result.replace(' OR ', ' | ')
        result = result.replace(' or ', ' | ')
        result = result.replace(' NOT ', ' ~ ')
        result = result.replace(' not ', ' ~ ')
        
        # 替换变量别名（只替换独立的变量名，不替换函数内的）
        for alias, real in self.ALIASES.items():
            # 使用正则确保只替换独立的变量名
            result = re.sub(rf'\b{alias}\b', f"df['{real}']", result)
        
        return result
    
    def _create_context(self, df: pd.DataFrame) -> Dict[str, Any]:
        """创建公式执行上下文"""
        context = {
            'df': df,
            'pd': pd,
            'np': np,
            # 基础函数
            'MA': MA,
            'EMA': EMA,
            'SMA': SMA,
            'WMA': WMA,
            'DEMA': DEMA,
            'TEMA': TEMA,
            'KAMA': KAMA,
            # 引用函数
            'REF': REF,
            'HHV': HHV,
            'LLV': LLV,
            'SUM': SUM,
            'STD': STD,
            'AVEDEV': AVEDEV,
            # 逻辑函数
            'CROSS': CROSS,
            'LONGCROSS': LONGCROSS,
            'BARSLAST': BARSLAST,
            'COUNT': COUNT,
            'EVERY': EVERY,
            'EXIST': EXIST,
            'FILTER': FILTER,
            # 指标函数
            'MACD': lambda c, f=12, s=26, sig=9: MACD(c, f, s, sig),
            'RSI': RSI,
            'KDJ': lambda h, l, c, n=9: KDJ(h, l, c, n),
            'BOLL': BOLL,
            'ATR': ATR,
            'CCI': CCI,
            'WILLR': WILLR,
            'ROC': ROC,
            'MOMENTUM': MOMENTUM,
            'OBV': OBV,
            'MFI': MFI,
            'DMI': DMI,
            'ADX': ADX,
            'SAR': SAR,
            'SUPERTREND': SUPERTREND,
            # 预计算的指标
            'DIF': None,
            'DEA': None,
            'MACD_HIST': None,
            'K': None,
            'D': None,
            'J': None,
        }
        
        # 预计算常用指标
        if len(df) > 30:
            dif, dea, macd_hist = MACD(df['close'])
            context['DIF'] = dif
            context['DEA'] = dea
            context['MACD_HIST'] = macd_hist
            
            k, d, j = KDJ(df['high'], df['low'], df['close'])
            context['K'] = k
            context['D'] = d
            context['J'] = j
        
        return context
    
    def _eval_formula(self, formula: str, context: Dict) -> pd.Series:
        """执行公式"""
        processed = self._preprocess_formula(formula)
        try:
            result = eval(processed, {"__builtins__": {}}, context)
            if isinstance(result, tuple):
                result = result[0]  # 有些函数返回多值，取第一个
            return result
        except Exception as e:
            raise ValueError(f"公式执行错误: {formula}\n处理后: {processed}\n错误: {e}")
    
    def generate_signals(self) -> pd.Series:
        """生成交易信号"""
        df = self.data
        context = self._create_context(df)
        
        # 计算买卖条件
        buy_cond = self._eval_formula(self.buy_formula, context)
        sell_cond = self._eval_formula(self.sell_formula, context)
        
        # 生成信号
        signals = pd.Series(0, index=df.index)
        signals[buy_cond == True] = 1
        signals[sell_cond == True] = -1
        
        return signals


class CustomIndicator:
    """
    自定义指标类
    
    示例:
        # 定义自己的指标
        my_ma = CustomIndicator(
            name="MyMA",
            formula="(MA(C,5) + MA(C,10)) / 2",
            description="5日和10日均线的平均"
        )
        
        # 使用
        result = my_ma.calculate(df)
    """
    
    def __init__(self, name: str, formula: str, description: str = ""):
        self.name = name
        self.formula = formula
        self.description = description
    
    def calculate(self, df: pd.DataFrame) -> pd.Series:
        """计算指标值"""
        strategy = FormulaStrategy("True", "True")
        context = strategy._create_context(df)
        return strategy._eval_formula(self.formula, context)


# =============================================================================
# 预设公式策略库（类似通达信选股公式）
# =============================================================================

FORMULA_LIBRARY = {
    # ===== 均线策略 =====
    "双均线金叉": {
        "buy": "CROSS(MA(df['close'],5), MA(df['close'],20))",
        "sell": "CROSS(MA(df['close'],20), MA(df['close'],5))",
        "description": "5日均线上穿20日均线买入，下穿卖出"
    },
    "三均线多头": {
        "buy": "(MA(df['close'],5) > MA(df['close'],10)) & (MA(df['close'],10) > MA(df['close'],20)) & (REF(MA(df['close'],5),1) <= REF(MA(df['close'],10),1))",
        "sell": "(MA(df['close'],5) < MA(df['close'],10)) & (MA(df['close'],10) < MA(df['close'],20))",
        "description": "均线多头排列时买入"
    },
    "均线支撑": {
        "buy": "(df['close'] > MA(df['close'],20)) & (df['low'] <= MA(df['close'],20) * 1.01) & (df['close'] > df['open'])",
        "sell": "df['close'] < MA(df['close'],20) * 0.97",
        "description": "价格回踩20日均线获得支撑"
    },
    
    # ===== MACD策略 =====
    "MACD金叉": {
        "buy": "CROSS(DIF, DEA)",
        "sell": "CROSS(DEA, DIF)",
        "description": "MACD金叉买入，死叉卖出"
    },
    "MACD零轴上金叉": {
        "buy": "CROSS(DIF, DEA) & (DIF > 0)",
        "sell": "CROSS(DEA, DIF) | (DIF < -0.5)",
        "description": "零轴上方MACD金叉（强势信号）"
    },
    "MACD底背离": {
        "buy": "(df['close'] < REF(LLV(df['close'],20),1)) & (DIF > REF(LLV(DIF,20),1))",
        "sell": "CROSS(DEA, DIF)",
        "description": "价格新低但MACD不创新低"
    },
    
    # ===== KDJ策略 =====
    "KDJ金叉": {
        "buy": "CROSS(K, D) & (K < 30)",
        "sell": "CROSS(D, K) & (K > 70)",
        "description": "超卖区KDJ金叉买入，超买区死叉卖出"
    },
    "KDJ超卖反弹": {
        "buy": "(K < 20) & (D < 20) & (J < 0) & (K > REF(K,1))",
        "sell": "(K > 80) | CROSS(D, K)",
        "description": "KDJ深度超卖后反弹"
    },
    
    # ===== RSI策略 =====
    "RSI超卖": {
        "buy": "(RSI(df['close'],14) < 30) & (RSI(df['close'],14) > REF(RSI(df['close'],14),1))",
        "sell": "RSI(df['close'],14) > 70",
        "description": "RSI超卖后拐头向上"
    },
    "RSI背离": {
        "buy": "(df['close'] < REF(LLV(df['close'],14),1)) & (RSI(df['close'],14) > REF(LLV(RSI(df['close'],14),14),1))",
        "sell": "RSI(df['close'],14) > 75",
        "description": "RSI底背离"
    },
    
    # ===== 布林带策略 =====
    "布林带下轨支撑": {
        "buy": "(df['close'] <= BOLL(df['close'])[2]) & (df['close'] > df['open'])",
        "sell": "df['close'] >= BOLL(df['close'])[0]",
        "description": "触及布林带下轨后收阳"
    },
    "布林带收口突破": {
        "buy": "(BOLL(df['close'])[0] - BOLL(df['close'])[2]) / BOLL(df['close'])[1] < 0.1",
        "sell": "df['close'] < MA(df['close'],20)",
        "description": "布林带收口后突破"
    },
    
    # ===== 突破策略 =====
    "N日新高": {
        "buy": "df['close'] >= HHV(df['high'],20)",
        "sell": "df['close'] <= LLV(df['low'],10)",
        "description": "创20日新高买入，破10日新低卖出"
    },
    "放量突破": {
        "buy": "(df['close'] > HHV(df['high'].shift(1),20)) & (df['volume'] > MA(df['volume'],5) * 1.5)",
        "sell": "df['close'] < MA(df['close'],10)",
        "description": "放量突破前20日高点"
    },
    "跳空高开": {
        "buy": "(df['open'] > REF(df['high'],1)) & (df['close'] > df['open']) & (df['volume'] > MA(df['volume'],5) * 1.2)",
        "sell": "df['close'] < REF(df['open'],1)",
        "description": "跳空高开且收阳"
    },
    
    # ===== 量价策略 =====
    "量价齐升": {
        "buy": "(df['close'] > REF(df['close'],1)) & (df['volume'] > REF(df['volume'],1)) & COUNT((df['close'] > REF(df['close'],1)) & (df['volume'] > REF(df['volume'],1)), 3) >= 2",
        "sell": "(df['close'] < MA(df['close'],10)) | (df['volume'] < MA(df['volume'],10) * 0.5)",
        "description": "连续量价齐升"
    },
    "缩量调整后放量": {
        "buy": "(df['volume'] > MA(df['volume'],5) * 1.5) & (REF(df['volume'],1) < MA(df['volume'],5) * 0.7) & (df['close'] > df['open'])",
        "sell": "df['close'] < MA(df['close'],10)",
        "description": "缩量整理后放量上攻"
    },
    
    # ===== 形态策略 =====
    "锤子线": {
        "buy": "(df['close'] > df['open']) & ((df['open'] - df['low']) > 2 * (df['close'] - df['open'])) & ((df['high'] - df['close']) < (df['close'] - df['open']) * 0.3)",
        "sell": "df['close'] < REF(df['low'],1)",
        "description": "底部锤子线"
    },
    "吞没形态": {
        "buy": "(REF(df['close'],1) < REF(df['open'],1)) & (df['close'] > df['open']) & (df['close'] > REF(df['open'],1)) & (df['open'] < REF(df['close'],1))",
        "sell": "df['close'] < MA(df['close'],5)",
        "description": "看涨吞没形态"
    },
    "启明星": {
        "buy": "(REF(df['close'],2) < REF(df['open'],2)) & (abs(REF(df['close'],1) - REF(df['open'],1)) < ATR(df['high'],df['low'],df['close'],14).shift(1) * 0.3) & (df['close'] > df['open']) & (df['close'] > (REF(df['open'],2) + REF(df['close'],2)) / 2)",
        "sell": "df['close'] < MA(df['close'],5)",
        "description": "启明星反转形态"
    },
    
    # ===== 趋势策略 =====
    "海龟突破": {
        "buy": "df['close'] > HHV(df['high'].shift(1), 20)",
        "sell": "df['close'] < LLV(df['low'].shift(1), 10)",
        "description": "经典海龟交易法则"
    },
    "ATR突破": {
        "buy": "df['close'] > REF(df['close'],1) + ATR(df['high'],df['low'],df['close'],14) * 2",
        "sell": "df['close'] < REF(df['close'],1) - ATR(df['high'],df['low'],df['close'],14) * 2",
        "description": "价格突破2倍ATR"
    },
}


def create_formula_strategy(name: str) -> FormulaStrategy:
    """
    根据名称创建预设公式策略
    
    Args:
        name: 策略名称（在 FORMULA_LIBRARY 中定义的）
    
    Returns:
        FormulaStrategy 实例
    """
    if name not in FORMULA_LIBRARY:
        raise ValueError(f"未找到策略: {name}\n可用策略: {list(FORMULA_LIBRARY.keys())}")
    
    config = FORMULA_LIBRARY[name]
    return FormulaStrategy(
        buy_formula=config["buy"],
        sell_formula=config["sell"],
        name=name
    )


def list_formula_strategies() -> List[Dict]:
    """列出所有预设公式策略"""
    return [
        {"name": name, "description": config["description"]}
        for name, config in FORMULA_LIBRARY.items()
    ]


# =============================================================================
# 选股公式（用于扫描全市场）
# =============================================================================

class StockScanner:
    """
    选股扫描器
    
    使用公式筛选符合条件的股票
    
    示例:
        scanner = StockScanner()
        
        # 添加条件
        scanner.add_condition("站上所有均线", 
            "(C > MA(C,5)) & (C > MA(C,10)) & (C > MA(C,20)) & (C > MA(C,60))")
        scanner.add_condition("MACD金叉", "CROSS(DIF, DEA)")
        scanner.add_condition("RSI不超买", "RSI(C,14) < 70")
        
        # 扫描
        results = scanner.scan(stock_list)
    """
    
    def __init__(self):
        self.conditions = []
    
    def add_condition(self, name: str, formula: str):
        """添加筛选条件"""
        self.conditions.append({"name": name, "formula": formula})
        return self
    
    def clear_conditions(self):
        """清空条件"""
        self.conditions = []
        return self
    
    def check_stock(self, df: pd.DataFrame) -> Dict[str, bool]:
        """检查单只股票是否满足所有条件"""
        if len(df) < 60:
            return {c["name"]: False for c in self.conditions}
        
        strategy = FormulaStrategy("True", "True")
        context = strategy._create_context(df)
        
        results = {}
        for cond in self.conditions:
            try:
                result = strategy._eval_formula(cond["formula"], context)
                # 取最后一个值
                if isinstance(result, pd.Series):
                    results[cond["name"]] = bool(result.iloc[-1])
                else:
                    results[cond["name"]] = bool(result)
            except:
                results[cond["name"]] = False
        
        return results
    
    def scan(self, stocks: List[Dict], data_fetcher: Callable = None) -> List[Dict]:
        """
        扫描股票列表
        
        Args:
            stocks: 股票列表 [{"code": "000001", "name": "平安银行"}, ...]
            data_fetcher: 数据获取函数，接收 code 返回 DataFrame
        
        Returns:
            符合所有条件的股票列表
        """
        if data_fetcher is None:
            from data.fetcher import DataFetcher
            from datetime import datetime, timedelta
            start = (datetime.now() - timedelta(days=180)).strftime("%Y%m%d")
            data_fetcher = lambda code: DataFetcher.get_stock_daily(code, start)
        
        results = []
        
        for stock in stocks:
            code = stock.get("code", stock.get("symbol", ""))
            name = stock.get("name", "")
            
            try:
                df = data_fetcher(code)
                check_result = self.check_stock(df)
                
                # 所有条件都满足
                if all(check_result.values()):
                    results.append({
                        "code": code,
                        "name": name,
                        "conditions": check_result
                    })
            except:
                continue
        
        return results


# 预设选股条件
SCAN_PRESETS = {
    "强势股": [
        ("站上所有均线", "(df['close'] > MA(df['close'],5)) & (df['close'] > MA(df['close'],20)) & (df['close'] > MA(df['close'],60))"),
        ("MACD多头", "DIF > DEA"),
        ("量比大于1", "df['volume'] > MA(df['volume'],5)"),
    ],
    "超跌反弹": [
        ("RSI超卖", "RSI(df['close'],14) < 35"),
        ("KDJ超卖", "K < 30"),
        ("底部企稳", "df['close'] > REF(df['close'],1)"),
    ],
    "突破形态": [
        ("突破20日高点", "df['close'] > HHV(df['high'].shift(1), 20)"),
        ("放量", "df['volume'] > MA(df['volume'],5) * 1.3"),
        ("收阳", "df['close'] > df['open']"),
    ],
    "MACD底背离": [
        ("价格创新低", "df['close'] < LLV(df['close'].shift(1), 20)"),
        ("MACD不创新低", "DIF > LLV(DIF.shift(1), 20)"),
    ],
}


def create_scanner_from_preset(preset_name: str) -> StockScanner:
    """根据预设创建选股扫描器"""
    if preset_name not in SCAN_PRESETS:
        raise ValueError(f"未找到预设: {preset_name}\n可用预设: {list(SCAN_PRESETS.keys())}")
    
    scanner = StockScanner()
    for name, formula in SCAN_PRESETS[preset_name]:
        scanner.add_condition(name, formula)
    
    return scanner
