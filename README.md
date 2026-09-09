# A股量化回测平台 v2.1

基于 AKShare 的完整量化交易回测框架，参考 **Backtrader**、**VnPy**、**Qlib** 三大顶级开源项目设计。

## 功能模块

```
quant/
├── data/           # 数据获取（AKShare）
├── strategy/       # 策略库（36种策略）
├── backtest/       # 回测引擎
│   ├── engine.py       # 基础回测引擎
│   ├── cerebro.py      # Cerebro 高级引擎（参考 Backtrader）
│   ├── portfolio.py    # 🆕 组合回测引擎（多股票持仓）
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
├── simulator/      # 🆕 模拟交易系统
│   └── paper_trading.py # 模拟下单、持仓管理
├── report/         # 🆕 报告生成
│   ├── daily_review.py  # 每日复盘（文本+HTML）
│   └── factor_report.py # 因子分析（IC/IR/分组收益）
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

### 2. 🆕 组合回测（多股票持仓）

```python
from backtest import PortfolioBacktest, run_portfolio_backtest

# 快速运行（等权重，月度再平衡）
result = run_portfolio_backtest(
    symbols=["600519", "000858", "000333", "600036", "601318"],
    start_date="20230101",
    end_date="20240101",
    initial_capital=1000000,
    rebalance_freq="monthly"
)
result.summary()
result.plot(save_path="portfolio.png")

# 自定义权重
engine = PortfolioBacktest(
    symbols=["600519", "000858", "000333"],
    start_date="20230101",
    end_date="20240101",
    initial_capital=1000000
)
engine.load_data()
engine.set_weights({"600519": 0.5, "000858": 0.3, "000333": 0.2})
result = engine.run(rebalance_freq="quarterly")
```

### 3. 🆕 模拟交易

```python
from simulator import PaperTrader

# 创建模拟交易器
trader = PaperTrader(initial_cash=1000000)

# 买入
order = trader.buy("000001", 1000)  # 市价买入1000股
order = trader.buy("600519", 100, price=1800)  # 限价买入

# 卖出
trader.sell("000001", 500)  # 卖出500股
trader.sell_all("600519")   # 清仓

# 查看账户
trader.summary()

# 查看持仓
positions = trader.get_all_positions()

# 查看交易记录
trades = trader.get_trade_history()

# 状态会自动保存，下次运行自动恢复
trader.reset()  # 重置账户
```

### 4. 🆕 每日复盘

```python
from report import DailyReview

# 生成今日复盘
review = DailyReview()

# 文本报告
print(review.generate_report())

# HTML报告（可视化）
review.generate_html_report("daily_review.html")

# 获取各项数据
top_gainers = review.get_top_gainers(20)    # 涨幅榜
top_losers = review.get_top_losers(20)      # 跌幅榜
hot_industries = review.get_hot_industries() # 热门行业
unusual = review.find_unusual_stocks()       # 异动股
```

### 5. 🆕 因子分析

```python
from report import FactorAnalyzer
import pandas as pd

# 准备数据
factor_df = pd.DataFrame({
    "momentum": momentum_values,
    "volatility": volatility_values
}, index=dates)
returns = price_series.pct_change()

# 创建分析器
analyzer = FactorAnalyzer(factor_df, returns)

# IC 分析
ic = analyzer.calculate_ic("momentum")
ir = analyzer.calculate_ir("momentum")

# 分组收益
group_return = analyzer.factor_group_return("momentum", n_groups=5)

# 因子衰减
decay = analyzer.factor_decay("momentum", max_lag=20)

# 因子相关性
corr = analyzer.factor_correlation()

# 完整报告
analyzer.print_report("momentum")
```

### 6. Cerebro 高级回测（类 Backtrader 风格）

```python
from backtest import Cerebro
from strategy import MACDStrategy

cerebro = Cerebro(cash=100000, commission=0.0003)
cerebro.add_data(data)
cerebro.add_strategy(MACDStrategy(12, 26, 9))
cerebro.set_sizer("risk_percent", risk_percent=0.02, stop_loss_pct=0.05)

result = cerebro.run()
result.summary()
```

### 7. 仓位管理器

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

### 8. Alpha 因子计算

```python
from alpha import FactorCalculator, MomentumFactor, VolatilityFactor

calc = FactorCalculator()
calc.add_all_basic_factors()
factors = calc.calculate(data)
```

### 9. 机器学习选股

```python
from alpha import RandomForestModel, FactorCalculator, FactorSelector

calc = FactorCalculator()
calc.add_all_basic_factors()
factors = calc.calculate(data)

returns = data["close"].pct_change().shift(-1)

selector = FactorSelector(top_k=10)
best_factors = selector.select_by_ic(factors, returns)

model = RandomForestModel(n_estimators=100)
model.fit(factors[best_factors], returns)
predictions = model.predict(factors[best_factors])
```

### 10. 风险管理

```python
from risk import RiskManager, RiskLimits

limits = RiskLimits(
    max_order_value=100000,
    max_position_pct=0.25,
    max_daily_trades=50,
    max_daily_loss=0.05,
    max_drawdown=0.20,
)

risk_mgr = RiskManager(limits)
risk_mgr.initialize(equity=100000)

is_allowed, reason, adjusted_size = risk_mgr.check_order("000001", 10.5, 1000)
```

### 11. Web 界面

```bash
streamlit run web/app.py --server.headless true
```

浏览器打开 http://localhost:8501

---

## 示例脚本

| 脚本 | 说明 |
|------|------|
| `examples/quick_start.py` | 快速入门 |
| `examples/portfolio_demo.py` | 🆕 组合回测示例 |
| `examples/paper_trading_demo.py` | 🆕 模拟交易示例 |
| `examples/daily_review_demo.py` | 🆕 每日复盘示例 |
| `examples/factor_analysis_demo.py` | 🆕 因子分析示例 |
| `examples/optimizer_demo.py` | 参数优化示例 |
| `examples/screener_demo.py` | 选股筛选示例 |
| `examples/realtime_demo.py` | 实时行情示例 |

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

## 新增功能 v2.1 🆕

### 1. 组合回测 (Portfolio Backtest)
- 多股票同时持仓
- 等权重/自定义权重
- 定期再平衡（日/周/月/季）
- 组合绩效分析
- 持仓历史追踪

### 2. 模拟交易 (Paper Trading)
- 市价单/限价单
- 实时价格获取
- 持仓管理
- 账户资金管理
- 交易记录
- 状态持久化（自动保存/恢复）

### 3. 每日复盘 (Daily Review)
- 大盘概况分析
- 涨跌分布统计
- 涨跌幅排行榜
- 热门行业/概念
- 异动股票识别
- HTML 可视化报告

### 4. 因子分析 (Factor Analysis)
- IC (Information Coefficient) 计算
- IR (Information Ratio) 计算
- 分组收益分析
- 因子衰减分析
- 因子相关性矩阵
- 专业分析报告

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
| IC | 因子与收益的相关性 | >0.03 |
| IR | IC均值/IC标准差 | >0.5 |

---

## 参考项目

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
5. 模拟交易状态保存在 `simulator/data/` 目录
