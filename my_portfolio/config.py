# -*- coding: utf-8 -*-
"""
我的持仓配置 - 在这里设置你的规则
"""
import json
import os

# ========== 持仓配置文件路径 ==========
HOLDINGS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "持仓配置.json")

def load_holdings():
    """从 JSON 文件加载持仓"""
    if os.path.exists(HOLDINGS_FILE):
        with open(HOLDINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("holdings", [])
    return []

def save_holdings(holdings):
    """保存持仓到 JSON 文件"""
    with open(HOLDINGS_FILE, "w", encoding="utf-8") as f:
        json.dump({"holdings": holdings}, f, ensure_ascii=False, indent=2)

# ========== 止损止盈规则 ==========
class StopRules:
    # 固定止损：跌破买入价 X% 提醒
    STOP_LOSS_PCT = 8
    
    # 固定止盈：盈利 X% 提醒
    TAKE_PROFIT_PCT = 20
    
    # 移动止盈：从最高点回撤 X% 提醒（适用于浮盈状态）
    TRAILING_STOP_PCT = 5
    
    # 破位止损：跌破 N 日均线提醒
    MA_STOP_PERIODS = [20, 60]  # 跌破20日线、60日线提醒

# ========== 技术指标阈值 ==========
class TechRules:
    # RSI
    RSI_OVERBOUGHT = 70   # 超买
    RSI_OVERSOLD = 30     # 超卖
    
    # KDJ
    KDJ_OVERBOUGHT = 80
    KDJ_OVERSOLD = 20
    
    # 布林带
    BOLL_UPPER_WARN = 0.9  # 接近上轨（0-1，1=在上轨）
    BOLL_LOWER_WARN = 0.1  # 接近下轨

# ========== 仓位管理 ==========
class PositionRules:
    TOTAL_CAPITAL = 100000     # 总资金（元），请修改为你的实际资金
    MAX_SINGLE_PCT = 0.3       # 单只股票最大仓位 30%
    MAX_LOSS_PER_TRADE = 0.02  # 单笔最大亏损 2%（用于计算建仓数量）

# ========== 提醒方式 ==========
class AlertConfig:
    # 邮件提醒（可选）
    EMAIL_ENABLED = False
    EMAIL_SENDER = ""
    EMAIL_PASSWORD = ""
    EMAIL_RECEIVER = ""
    SMTP_SERVER = "smtp.qq.com"
    SMTP_PORT = 465
    
    # 控制台提醒颜色
    USE_COLOR = True
