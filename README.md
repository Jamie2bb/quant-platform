# A股量化回测平台 v2.0

基于 AKShare 的完整量化交易回测框架，参考 **Backtrader**、**VnPy**、**Qlib** 三大顶级开源项目设计。

## 功能模块

```
quant/
├── data/           # 数据获取（AKShare）
├── strategy/       # 策略库（36种策略）
├── backtest/       # 回测引擎
│   ├── engine.py       # 基础回测引擎
│   ├── cerebro.py      # Cerebro 高级引擎（参考 Backtrader）
│   ├── analyzers.py    # 分析器（夏普、索提诺、回撤等）
│   └── sizers.py       # 仓位管理（固定、百分比、凯利、ATR等）
├── alpha/          # AI 因子库（参考 Qlib）
│   ├── factors.py      # 20+ Alpha 因子
│   └── ml_model.py     # 机器学习模型（Ridge、RF、XGB、LightGBM）
├── risk/           # 风险管理（参考 VnPy）
│   └── risk_manager.py # 风控模块（仓位、回撤、日内限制）
├── optimizer/      # 参数优化（网格搜索/遗传算法）
├── screener/       # 选股筛选器
├── monitor/        # 实盘监控与信号提醒
├── utils/          # 技术指标工具
├── web/            # Web可视化界面（Streamlit）
└── examples/       # 示例脚本
```

## 快速安装

```bash
pip install -r requirements.txt
```

## 使用方式

### 1. 基础回测

```python
from backtest import BacktestEngine
from strategy import MACrossStrategy

engine = BacktestEngine(
    symbol="000001",
    start_date="20230101",
    end_date="20231231",
    initial_capital=100000
)

engine.set_strategy(MACrossStrategy(5, 20))
result = engine.run()
result.summary()
result.plot()
```

### 2. Cerebro 高级回测（类 Backtrader 风格）

```python
from backtest import Cerebro
from strategy import MACDStrategy

# 创建引擎
cerebro = Cerebro(cash=100000, commission=0.0003)

# 添加数据
cerebro.add_data(data)

# 添加策略
cerebro.add_strategy(MACDStrategy(12, 26, 9))

# 设置仓位管理
cerebro.set_sizer("risk_percent", risk_percent=0.02, stop_loss_pct=0.05)

# 运行回测
result = cerebro.run()
result.summary()

# 查看详细指标
print(result.metrics)
```

### 3. 仓位管理器

```python
from backtest import create_sizer

# 固定股数
sizer = create_sizer("fixed", size=1000)

# 固定金额
sizer = create_sizer("fixed_amount", amount=10000)

# 资金百分比
sizer = create_sizer("percent", percent=0.2)

# 风险百分比（基于止损）
sizer = create_sizer("risk_percent", risk_percent=0.02, stop_loss_pct=0.05)

# ATR 波动率仓位（海龟交易法）
sizer = create_sizer("atr", risk_percent=0.01, atr_period=14, atr_mult=2.0)

# 凯利公式
sizer = create_sizer("kelly", win_rate=0.55, profit_loss_ratio=1.5, fraction=0.5)

# 目标波动率
sizer = create_sizer("volatility_target", target_volatility=0.15)
```

### 4. Alpha 因子计算

```python
from alpha import FactorCalculator, MomentumFactor, VolatilityFactor

# 创建因子计算器
calc = FactorCalculator()
calc.add_all_basic_factors()  # 添加 20+ 基础因子

# 计算因子
factors = calc.calculate(data)
print(factors.head())

# 单个因子
momentum = MomentumFactor(20).calculate(data)
```

### 5. 机器学习选股

```python
from alpha import RandomForestModel, FactorCalculator, FactorSelector

# 计算因子
calc = FactorCalculator()
calc.add_all_basic_factors()
factors = calc.calculate(data)

# 构建目标变量（下期收益）
returns = data["close"].pct_change().shift(-1)

# 因子选择
selector = FactorSelector(top_k=10)
best_factors = selector.select_by_ic(factors, returns)
print(selector.get_report())

# 训练模型
model = RandomForestModel(n_estimators=100)
model.fit(factors[best_factors], returns)

# 预测
predictions = model.predict(factors[best_factors])
```

### 6. 风险管理

```python
from risk import RiskManager, RiskLimits

# 配置风险限制
limits = RiskLimits(
    max_order_value=100000,      # 单笔最大金额
    max_position_pct=0.25,       # 单只股票最大仓位
    max_daily_trades=50,         # 日最大交易次数
    max_daily_loss=0.05,         # 日最大亏损
    max_drawdown=0.20,           # 最大回撤限制
)

# 创建风险管理器
risk_mgr = RiskManager(limits)
risk_mgr.initialize(equity=100000)

# 检查订单
is_allowed, reason, adjusted_size = risk_mgr.check_order(
    symbol="000001", 
    price=10.5, 
    size=1000
)

if is_allowed:
    # 执行交易...
    risk_mgr.record_trade("000001", 10.5, adjusted_size, "buy")

# 查看风险摘要
print(risk_mgr.get_risk_summary())
```

### 7. Web 界面

```bash
streamlit run web/app.py
```

浏览器打开 http://localhost:8501

---

## 内置策略（36种）

### 📊 均线类（4种）
- 双均线交叉、三均线、均值回归、自适应趋势

### 📈 技术指标（6种）
- MACD、MACD背离、KDJ、KDJ金叉、RSI动量、布林带突破

### 🎯 动量因子（5种）
- 动量策略、价值动量、质量动量、多因子、轮动策略

### 📉 趋势跟踪（4种）
- 通道突破、趋势跟踪、DualThrust、突破回踩

### 🔊 量价策略（5种）
- 量价突破、放量突破、OBV能量潮、量能剖面、缩量企稳

### 🔄 形态识别（4种）
- K线形态、双底形态、网格策略、动态网格

### 🛡️ 止损管理（4种）
- 移动止损、固定比例止损、ATR止损、时间止损

### 🔗 组合策略（4种）
- 多策略投票、确认策略、趋势过滤、轮动策略

---

## Alpha 因子库（20+）

### 动量因子
- Momentum（动量）、Reversal（反转）、RS（相对强弱）

### 波动率因子
- Volatility（波动率）、ATR、VolatilityRatio（波动率比）

### 成交量因子
- Volume（量比）、VolumeMA、Amount（成交额）、OBV

### 价格形态因子
- HighLow（价格位置）、Gap（跳空）、Body（实体）、Shadow（影线）

### 趋势因子
- Trend、TrendStrength（ADX）、MACD

### 组合因子
- Quality（质量）、CompositeMomentum（复合动量）

---

## 仓位管理器（9种）

| 类型 | 说明 |
|------|------|
| `fixed` | 固定股数 |
| `fixed_amount` | 固定金额 |
| `percent` | 资金百分比 |
| `all_in` | 全仓 |
| `risk_percent` | 风险百分比（基于止损） |
| `atr` | ATR 波动率仓位（海龟法） |
| `kelly` | 凯利公式 |
| `pyramid` | 金字塔加仓 |
| `volatility_target` | 目标波动率 |

---

## 分析器（7种）

| 分析器 | 指标 |
|--------|------|
| SharpeRatio | 夏普比率、年化收益、年化波动 |
| SortinoRatio | 索提诺比率、下行波动率 |
| CalmarRatio | 卡玛比率 |
| DrawDown | 最大回撤、回撤持续时间、平均回撤 |
| Trade | 胜率、盈亏比、期望值、最大连胜/连亏 |
| TimeReturn | 月度统计、最佳/最差月份 |
| Risk | VaR、CVaR、偏度、峰度 |

---

## 绩效指标说明

| 指标 | 说明 | 好的标准 |
|------|------|----------|
| 夏普比率 | 风险调整后收益 | >1.0 (>2.0 优秀) |
| 索提诺比率 | 只考虑下行风险 | >1.5 |
| 卡玛比率 | 年化收益/最大回撤 | >1.0 |
| 最大回撤 | 峰值到谷底最大跌幅 | <20% |
| VaR(95%) | 95%置信度下最大日损失 | <3% |
| 胜率 | 盈利交易占比 | >50% |
| 盈亏比 | 平均盈利/平均亏损 | >1.5 |

---

## 参考项目

本平台参考了以下顶级开源项目：

- **[Backtrader](https://github.com/mementum/backtrader)** - Cerebro 引擎、Analyzer、Sizer 设计
- **[VnPy](https://github.com/vnpy/vnpy)** - 风控模块、事件驱动架构
- **[Qlib](https://github.com/microsoft/qlib)** - Alpha 因子库、机器学习模型

---

## 数据来源

- **AKShare** - 免费开源的 A股数据接口
- 支持：日K线、分钟K线、实时行情、财务数据

## 注意事项

1. 本平台仅供学习研究，不构成投资建议
2. 历史回测表现不代表未来收益
3. 网络不稳定时数据获取可能失败，会自动重试
4. 机器学习模块需要额外安装 `scikit-learn`、`lightgbm`、`xgboost`
