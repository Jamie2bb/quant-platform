"""
量化平台 Web 界面
使用 Streamlit 构建

运行方式: streamlit run web/app.py
"""
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.fetcher import DataFetcher
from backtest.engine import BacktestEngine
from strategy import (
    # 基础策略
    MACrossStrategy, TripleMAStrategy,
    MACDStrategy, MACDDivergenceStrategy,
    KDJStrategy, KDJGoldenStrategy,
    RSIMomentumStrategy, MomentumStrategy,
    BreakoutStrategy, BollingerBreakoutStrategy, VolumeBreakoutStrategy,
    MeanReversionStrategy, GridStrategy, DynamicGridStrategy,
    # 高级策略 - 因子
    MultiFactorStrategy, ValueMomentumStrategy, QualityMomentumStrategy,
    # 高级策略 - 趋势
    TrendFollowingStrategy, DualThrustStrategy, AdaptiveTrendStrategy,
    # 高级策略 - 止损
    TrailingStopStrategy, ATRStopStrategy,
    # 高级策略 - 量价
    VolumeBreakthroughStrategy, OBVStrategy, ShrinkingVolumeStrategy,
    # 高级策略 - 形态
    CandlePatternStrategy, DoubleBottomStrategy, BreakoutRetestStrategy,
    # 高级策略 - 组合
    CompositeStrategy, FilteredStrategy, RotationStrategy,
)

# 页面配置
st.set_page_config(
    page_title="A股量化回测平台",
    page_icon="📈",
    layout="wide"
)

# 标题
st.title("📈 A股量化回测平台")

# 侧边栏 - 参数设置
st.sidebar.header("参数设置")

# 股票代码
symbol = st.sidebar.text_input("股票代码", value="000001")

# 日期范围
col1, col2 = st.sidebar.columns(2)
with col1:
    start_date = st.date_input(
        "开始日期",
        value=datetime.now() - timedelta(days=365)
    )
with col2:
    end_date = st.date_input(
        "结束日期",
        value=datetime.now()
    )

# 初始资金
initial_capital = st.sidebar.number_input(
    "初始资金",
    min_value=10000,
    max_value=10000000,
    value=100000,
    step=10000
)

# 策略选择
strategy_category = st.sidebar.selectbox(
    "策略分类",
    [
        "📊 均线类",
        "📈 指标类", 
        "🎯 动量类",
        "📉 趋势类",
        "🔊 量价类",
        "🔄 形态类",
        "🛡️ 组合类",
    ]
)

# 根据分类显示策略
if strategy_category == "📊 均线类":
    strategy_name = st.sidebar.selectbox(
        "选择策略",
        ["双均线交叉", "三均线策略", "均值回归", "自适应趋势"]
    )
elif strategy_category == "📈 指标类":
    strategy_name = st.sidebar.selectbox(
        "选择策略",
        ["MACD金叉死叉", "MACD背离", "KDJ超买超卖", "KDJ金叉", "RSI动量", "布林带突破"]
    )
elif strategy_category == "🎯 动量类":
    strategy_name = st.sidebar.selectbox(
        "选择策略",
        ["动量策略", "价值动量", "质量动量", "多因子策略", "轮动策略"]
    )
elif strategy_category == "📉 趋势类":
    strategy_name = st.sidebar.selectbox(
        "选择策略",
        ["通道突破", "趋势跟踪", "DualThrust", "突破回踩"]
    )
elif strategy_category == "🔊 量价类":
    strategy_name = st.sidebar.selectbox(
        "选择策略",
        ["量价突破", "OBV能量潮", "缩量企稳", "放量突破"]
    )
elif strategy_category == "🔄 形态类":
    strategy_name = st.sidebar.selectbox(
        "选择策略",
        ["K线形态", "双底形态", "网格策略", "动态网格"]
    )
else:  # 组合类
    strategy_name = st.sidebar.selectbox(
        "选择策略",
        ["趋势过滤策略", "移动止损策略", "ATR止损策略"]
    )

# 策略参数
st.sidebar.subheader("策略参数")

# ===== 均线类 =====
if strategy_name == "双均线交叉":
    short_period = st.sidebar.slider("短期均线", 3, 30, 5)
    long_period = st.sidebar.slider("长期均线", 10, 120, 20)
    strategy = MACrossStrategy(short_period, long_period)

elif strategy_name == "三均线策略":
    short = st.sidebar.slider("短期", 3, 20, 5)
    mid = st.sidebar.slider("中期", 5, 30, 10)
    long = st.sidebar.slider("长期", 10, 60, 20)
    strategy = TripleMAStrategy(short, mid, long)

elif strategy_name == "均值回归":
    ma_period = st.sidebar.slider("均线周期", 10, 60, 20)
    deviation = st.sidebar.slider("偏离阈值(%)", 1, 20, 5) / 100
    strategy = MeanReversionStrategy(ma_period, deviation)

elif strategy_name == "自适应趋势":
    fast_period = st.sidebar.slider("快速周期", 5, 20, 10)
    slow_period = st.sidebar.slider("慢速周期", 20, 60, 30)
    strategy = AdaptiveTrendStrategy(fast_period, slow_period)

# ===== 指标类 =====
elif strategy_name == "MACD金叉死叉":
    fast = st.sidebar.slider("快线", 5, 20, 12)
    slow = st.sidebar.slider("慢线", 15, 40, 26)
    signal = st.sidebar.slider("信号线", 5, 15, 9)
    strategy = MACDStrategy(fast, slow, signal)

elif strategy_name == "MACD背离":
    fast = st.sidebar.slider("快线", 5, 20, 12)
    slow = st.sidebar.slider("慢线", 15, 40, 26)
    signal = st.sidebar.slider("信号线", 5, 15, 9)
    strategy = MACDDivergenceStrategy(fast, slow, signal)

elif strategy_name == "KDJ超买超卖":
    n = st.sidebar.slider("KDJ周期", 5, 20, 9)
    oversold = st.sidebar.slider("超卖线", 10, 40, 20)
    overbought = st.sidebar.slider("超买线", 60, 90, 80)
    strategy = KDJStrategy(n, oversold=oversold, overbought=overbought)

elif strategy_name == "KDJ金叉":
    n = st.sidebar.slider("KDJ周期", 5, 20, 9)
    strategy = KDJGoldenStrategy(n)

elif strategy_name == "RSI动量":
    period = st.sidebar.slider("RSI周期", 5, 30, 14)
    oversold = st.sidebar.slider("超卖阈值", 10, 40, 30)
    overbought = st.sidebar.slider("超买阈值", 60, 90, 70)
    strategy = RSIMomentumStrategy(period, oversold, overbought)

elif strategy_name == "布林带突破":
    period = st.sidebar.slider("周期", 10, 30, 20)
    std_dev = st.sidebar.slider("标准差倍数", 1.0, 3.0, 2.0, 0.1)
    strategy = BollingerBreakoutStrategy(period, std_dev)

# ===== 动量类 =====
elif strategy_name == "动量策略":
    period = st.sidebar.slider("动量周期", 5, 30, 10)
    strategy = MomentumStrategy(period)

elif strategy_name == "价值动量":
    momentum_period = st.sidebar.slider("动量周期", 10, 40, 20)
    strategy = ValueMomentumStrategy(momentum_period)

elif strategy_name == "质量动量":
    lookback = st.sidebar.slider("回看周期", 20, 120, 60)
    strategy = QualityMomentumStrategy(lookback)

elif strategy_name == "多因子策略":
    score_threshold = st.sidebar.slider("评分阈值", 0.3, 0.8, 0.6, 0.05)
    strategy = MultiFactorStrategy(score_threshold)

elif strategy_name == "轮动策略":
    momentum_period = st.sidebar.slider("动量周期", 10, 40, 20)
    hold_period = st.sidebar.slider("持仓周期", 5, 40, 20)
    strategy = RotationStrategy(momentum_period, hold_period)

# ===== 趋势类 =====
elif strategy_name == "通道突破":
    entry_period = st.sidebar.slider("入场周期", 10, 60, 20)
    exit_period = st.sidebar.slider("出场周期", 5, 30, 10)
    strategy = BreakoutStrategy(entry_period, exit_period)

elif strategy_name == "趋势跟踪":
    fast_period = st.sidebar.slider("快速周期", 5, 30, 10)
    slow_period = st.sidebar.slider("慢速周期", 20, 60, 30)
    atr_period = st.sidebar.slider("ATR周期", 10, 30, 14)
    strategy = TrendFollowingStrategy(fast_period, slow_period, atr_period)

elif strategy_name == "DualThrust":
    n = st.sidebar.slider("回看周期", 2, 10, 4)
    k1 = st.sidebar.slider("上轨系数", 0.3, 1.0, 0.5, 0.05)
    k2 = st.sidebar.slider("下轨系数", 0.3, 1.0, 0.5, 0.05)
    strategy = DualThrustStrategy(n, k1, k2)

elif strategy_name == "突破回踩":
    breakout_period = st.sidebar.slider("突破周期", 10, 40, 20)
    confirm_period = st.sidebar.slider("确认周期", 3, 10, 5)
    strategy = BreakoutRetestStrategy(breakout_period, confirm_period)

# ===== 量价类 =====
elif strategy_name == "量价突破":
    price_period = st.sidebar.slider("价格周期", 10, 40, 20)
    volume_ratio = st.sidebar.slider("量比阈值", 1.0, 3.0, 1.5, 0.1)
    strategy = VolumeBreakthroughStrategy(price_period, volume_ratio)

elif strategy_name == "OBV能量潮":
    ma_period = st.sidebar.slider("OBV均线周期", 10, 40, 20)
    strategy = OBVStrategy(ma_period)

elif strategy_name == "缩量企稳":
    volume_period = st.sidebar.slider("量能周期", 5, 20, 10)
    price_period = st.sidebar.slider("价格周期", 5, 20, 10)
    strategy = ShrinkingVolumeStrategy(volume_period, price_period)

elif strategy_name == "放量突破":
    period = st.sidebar.slider("突破周期", 10, 40, 20)
    vol_mult = st.sidebar.slider("量能倍数", 1.2, 3.0, 1.5, 0.1)
    strategy = VolumeBreakoutStrategy(period, vol_mult)

# ===== 形态类 =====
elif strategy_name == "K线形态":
    strategy = CandlePatternStrategy()

elif strategy_name == "双底形态":
    lookback = st.sidebar.slider("回看周期", 20, 80, 40)
    threshold = st.sidebar.slider("价格阈值(%)", 1, 10, 3) / 100
    strategy = DoubleBottomStrategy(lookback, threshold)

elif strategy_name == "网格策略":
    grid_num = st.sidebar.slider("网格数量", 3, 20, 10)
    grid_size = st.sidebar.slider("网格间距(%)", 1, 10, 3) / 100
    strategy = GridStrategy(grid_num, grid_size)

elif strategy_name == "动态网格":
    grid_num = st.sidebar.slider("网格数量", 3, 20, 10)
    atr_mult = st.sidebar.slider("ATR倍数", 0.5, 3.0, 1.0, 0.1)
    strategy = DynamicGridStrategy(grid_num, atr_mult)

# ===== 组合类 =====
elif strategy_name == "趋势过滤策略":
    st.sidebar.write("基于双均线，趋势过滤")
    short_period = st.sidebar.slider("短期均线", 3, 20, 5)
    long_period = st.sidebar.slider("长期均线", 10, 60, 20)
    trend_period = st.sidebar.slider("趋势周期", 30, 120, 60)
    base_strategy = MACrossStrategy(short_period, long_period)
    strategy = FilteredStrategy(base_strategy, trend_period=trend_period)

elif strategy_name == "移动止损策略":
    st.sidebar.write("基于双均线，移动止损")
    short_period = st.sidebar.slider("短期均线", 3, 20, 5)
    long_period = st.sidebar.slider("长期均线", 10, 60, 20)
    trail_pct = st.sidebar.slider("移动止损(%)", 3, 15, 8) / 100
    base_strategy = MACrossStrategy(short_period, long_period)
    strategy = TrailingStopStrategy(base_strategy, trail_pct=trail_pct)

elif strategy_name == "ATR止损策略":
    st.sidebar.write("基于MACD，ATR止损")
    fast = st.sidebar.slider("MACD快线", 5, 20, 12)
    slow = st.sidebar.slider("MACD慢线", 15, 40, 26)
    atr_mult = st.sidebar.slider("ATR倍数", 1.0, 4.0, 2.0, 0.5)
    base_strategy = MACDStrategy(fast, slow, 9)
    strategy = ATRStopStrategy(base_strategy, atr_mult=atr_mult)

# 运行回测按钮
if st.sidebar.button("🚀 运行回测", type="primary"):
    
    with st.spinner("正在获取数据并运行回测..."):
        try:
            # 创建回测引擎
            engine = BacktestEngine(
                symbol=symbol,
                start_date=start_date.strftime("%Y%m%d"),
                end_date=end_date.strftime("%Y%m%d"),
                initial_capital=initial_capital
            )
            
            engine.set_strategy(strategy)
            result = engine.run()
            
            # 显示结果
            st.success("回测完成！")
            
            # 绩效指标卡片
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "总收益率",
                    f"{result.total_return:.2%}",
                    delta=f"{result.annual_return:.2%} 年化"
                )
            
            with col2:
                st.metric(
                    "最大回撤",
                    f"{result.max_drawdown:.2%}"
                )
            
            with col3:
                st.metric(
                    "夏普比率",
                    f"{result.sharpe_ratio:.2f}"
                )
            
            with col4:
                st.metric(
                    "胜率",
                    f"{result.win_rate:.2%}",
                    delta=f"{result.total_trades} 笔交易"
                )
            
            # 资金曲线图
            st.subheader("资金曲线")
            
            chart_data = pd.DataFrame({
                "资金": result.data["equity"],
                "基准(持有不动)": initial_capital * (1 + result.data["close"].pct_change().cumsum())
            })
            st.line_chart(chart_data)
            
            # 价格与交易点
            st.subheader("价格走势与交易点")
            
            # 创建价格图表数据
            price_data = result.data[["close"]].copy()
            price_data.columns = ["收盘价"]
            st.line_chart(price_data)
            
            # 交易明细
            st.subheader("交易明细")
            
            trades_df = result.get_trades_df()
            if not trades_df.empty:
                st.dataframe(trades_df, use_container_width=True)
            else:
                st.info("无交易记录")
            
            # 详细指标
            with st.expander("查看详细指标"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**收益指标**")
                    st.write(f"- 初始资金: ¥{initial_capital:,.2f}")
                    st.write(f"- 最终资金: ¥{result.final_capital:,.2f}")
                    st.write(f"- 总收益率: {result.total_return:.2%}")
                    st.write(f"- 年化收益率: {result.annual_return:.2%}")
                
                with col2:
                    st.write("**风险指标**")
                    st.write(f"- 最大回撤: {result.max_drawdown:.2%}")
                    st.write(f"- 夏普比率: {result.sharpe_ratio:.2f}")
                    st.write(f"- 卡玛比率: {result.calmar_ratio:.2f}")
                
                st.write("**交易统计**")
                st.write(f"- 交易次数: {result.total_trades}")
                st.write(f"- 胜率: {result.win_rate:.2%}")
                st.write(f"- 盈亏比: {result.profit_factor:.2f}")
                st.write(f"- 平均持仓天数: {result.avg_hold_days:.1f}")
                
        except Exception as e:
            st.error(f"回测失败: {str(e)}")

# 页面底部
st.divider()

# 实时行情（可选功能）
with st.expander("📊 实时行情查询"):
    query_symbol = st.text_input("输入股票代码查询", value="000001", key="realtime")
    
    if st.button("查询"):
        try:
            with st.spinner("获取数据（网络不稳定时可能需要重试）..."):
                df = DataFetcher.get_stock_daily(
                    query_symbol, 
                    (datetime.now() - timedelta(days=30)).strftime("%Y%m%d"),
                    max_retries=5
                )
                
                st.write(f"**{query_symbol} 最近行情**")
                st.dataframe(df.tail(10))
                
                st.line_chart(df["close"])
        except Exception as e:
            st.error(f"查询失败（网络问题，请稍后重试）: {e}")

# 使用说明
with st.expander("📖 使用说明"):
    st.markdown("""
    ### 快速开始
    
    1. 在左侧输入**股票代码**（如 000001 平安银行）
    2. 选择**回测时间范围**
    3. 选择**策略分类**，再选择具体**策略**
    4. 调整策略参数
    5. 点击 **运行回测** 按钮
    
    ### 策略分类说明
    
    #### 📊 均线类
    | 策略 | 说明 |
    |------|------|
    | 双均线交叉 | 短期均线上穿长期均线买入，下穿卖出 |
    | 三均线策略 | 三条均线多头排列时买入 |
    | 均值回归 | 价格偏离均线过多时反向操作 |
    | 自适应趋势 | 根据市场波动自适应调整均线 |
    
    #### 📈 指标类
    | 策略 | 说明 |
    |------|------|
    | MACD金叉死叉 | DIF上穿DEA金叉买入，死叉卖出 |
    | MACD背离 | 价格与MACD背离时反向操作 |
    | KDJ超买超卖 | KDJ超卖区金叉买入，超买区死叉卖出 |
    | KDJ金叉 | K线上穿D线买入 |
    | RSI动量 | RSI超卖回升买入，超买卖出 |
    | 布林带突破 | 价格突破布林带上轨买入 |
    
    #### 🎯 动量类
    | 策略 | 说明 |
    |------|------|
    | 动量策略 | 价格动量强势时买入 |
    | 价值动量 | 结合估值和动量因子 |
    | 质量动量 | 结合盈利质量和动量 |
    | 多因子策略 | 综合多个因子打分 |
    | 轮动策略 | 动量排名轮动 |
    
    #### 📉 趋势类
    | 策略 | 说明 |
    |------|------|
    | 通道突破 | 突破N日高点买入，跌破N日低点卖出 |
    | 趋势跟踪 | 跟随趋势，ATR控制仓位 |
    | DualThrust | 经典日内突破策略 |
    | 突破回踩 | 突破后等待回踩确认买入 |
    
    #### 🔊 量价类
    | 策略 | 说明 |
    |------|------|
    | 量价突破 | 放量突破关键位买入 |
    | OBV能量潮 | 根据OBV趋势交易 |
    | 缩量企稳 | 缩量整理后突破买入 |
    | 放量突破 | 量能配合价格突破 |
    
    #### 🔄 形态类
    | 策略 | 说明 |
    |------|------|
    | K线形态 | 识别看涨/看跌K线形态 |
    | 双底形态 | W底形态确认后买入 |
    | 网格策略 | 固定网格区间交易 |
    | 动态网格 | ATR动态调整网格 |
    
    #### 🛡️ 组合类
    | 策略 | 说明 |
    |------|------|
    | 趋势过滤策略 | 只在大趋势向上时交易 |
    | 移动止损策略 | 基础策略+移动止损保护 |
    | ATR止损策略 | 基础策略+ATR动态止损 |
    
    ### 指标说明
    
    - **夏普比率**: 风险调整后收益，>1 为好，>2 为优秀
    - **最大回撤**: 资金从峰值到谷底的最大跌幅
    - **卡玛比率**: 年化收益 / 最大回撤，越高越好
    - **胜率**: 盈利交易占比
    - **盈亏比**: 平均盈利 / 平均亏损
    """)

# 版本信息
st.sidebar.divider()
st.sidebar.caption("A股量化回测平台 v2.0")
st.sidebar.caption(f"内置 {30}+ 策略")
st.sidebar.caption("数据来源: AKShare")
