# -*- coding: utf-8 -*-
"""
我的持仓 - Web 页面组件
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.fetcher import DataFetcher
from utils.indicators import SMA, RSI, MACD, KDJ, BOLL

# 尝试导入高级指标库
try:
    from utils.indicators_pro import add_all_indicators, generate_signals
    HAS_PRO_INDICATORS = True
except ImportError:
    HAS_PRO_INDICATORS = False

from strategy import MACrossStrategy, MACDStrategy, KDJStrategy

# 尝试导入公式策略
try:
    from strategy.formula import FormulaStrategy, FORMULA_LIBRARY, create_formula_strategy, list_formula_strategies
    HAS_FORMULA = True
except ImportError:
    HAS_FORMULA = False


def init_session_state():
    """初始化会话状态"""
    if 'holdings' not in st.session_state:
        st.session_state.holdings = []
    if 'total_capital' not in st.session_state:
        st.session_state.total_capital = 100000
    if 'stop_loss_pct' not in st.session_state:
        st.session_state.stop_loss_pct = 8
    if 'take_profit_pct' not in st.session_state:
        st.session_state.take_profit_pct = 20
    if 'trailing_stop_pct' not in st.session_state:
        st.session_state.trailing_stop_pct = 5
    if 'max_single_pct' not in st.session_state:
        st.session_state.max_single_pct = 30
    if 'max_loss_per_trade' not in st.session_state:
        st.session_state.max_loss_per_trade = 2


def render_portfolio_page():
    """渲染持仓管理页面"""
    init_session_state()
    
    st.title("💼 我的持仓分析")
    
    # 创建标签页
    tabs = ["📊 持仓管理", "🔍 技术分析", "⚠️ 风险监控", "📐 仓位计算", "📈 策略回测"]
    
    if HAS_FORMULA:
        tabs.append("📝 公式策略")
        tabs.append("🔎 选股扫描")
    
    tab_objects = st.tabs(tabs)
    
    # ========== Tab 1: 持仓管理 ==========
    with tab_objects[0]:
        render_holdings_management()
    
    # ========== Tab 2: 技术分析 ==========
    with tab_objects[1]:
        render_technical_analysis()
    
    # ========== Tab 3: 风险监控 ==========
    with tab_objects[2]:
        render_risk_monitor()
    
    # ========== Tab 4: 仓位计算 ==========
    with tab_objects[3]:
        render_position_calculator()
    
    # ========== Tab 5: 策略回测 ==========
    with tab_objects[4]:
        render_backtest()
    
    # ========== Tab 6: 公式策略 ==========
    if HAS_FORMULA and len(tab_objects) > 5:
        with tab_objects[5]:
            render_formula_strategy()
    
    # ========== Tab 7: 选股扫描 ==========
    if HAS_FORMULA and len(tab_objects) > 6:
        with tab_objects[6]:
            render_stock_scanner()


def render_holdings_management():
    """持仓管理"""
    st.subheader("持仓列表")
    
    # 参数设置
    with st.expander("⚙️ 风控参数设置", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.session_state.total_capital = st.number_input(
                "总资金 (元)", 
                min_value=10000, 
                max_value=100000000,
                value=st.session_state.total_capital,
                step=10000
            )
            st.session_state.max_single_pct = st.number_input(
                "单只最大仓位 (%)", 
                min_value=5, 
                max_value=100,
                value=st.session_state.max_single_pct,
                step=5
            )
        with col2:
            st.session_state.stop_loss_pct = st.number_input(
                "止损线 (%)", 
                min_value=1, 
                max_value=30,
                value=st.session_state.stop_loss_pct
            )
            st.session_state.take_profit_pct = st.number_input(
                "止盈线 (%)", 
                min_value=5, 
                max_value=100,
                value=st.session_state.take_profit_pct
            )
        with col3:
            st.session_state.trailing_stop_pct = st.number_input(
                "移动止盈回撤 (%)", 
                min_value=1, 
                max_value=20,
                value=st.session_state.trailing_stop_pct
            )
            st.session_state.max_loss_per_trade = st.number_input(
                "单笔最大亏损 (%)", 
                min_value=1, 
                max_value=10,
                value=st.session_state.max_loss_per_trade
            )
    
    # 添加持仓
    st.markdown("---")
    st.subheader("添加持仓")
    
    col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 1])
    with col1:
        new_code = st.text_input("股票代码", placeholder="如 600519")
    with col2:
        new_name = st.text_input("股票名称", placeholder="如 贵州茅台")
    with col3:
        new_cost = st.number_input("成本价", min_value=0.0, value=0.0, step=0.01)
    with col4:
        new_shares = st.number_input("持仓数量", min_value=0, value=0, step=100)
    with col5:
        st.write("")
        st.write("")
        if st.button("➕ 添加", use_container_width=True):
            if new_code and new_name:
                # 检查是否已存在
                exists = any(h['code'] == new_code for h in st.session_state.holdings)
                if exists:
                    st.warning(f"{new_code} 已在列表中")
                else:
                    st.session_state.holdings.append({
                        'code': new_code,
                        'name': new_name,
                        'cost': new_cost,
                        'shares': new_shares,
                        'current_price': 0,
                        'highest_price': 0
                    })
                    st.success(f"已添加 {new_code} {new_name}")
                    st.rerun()
            else:
                st.warning("请输入股票代码和名称")
    
    # 显示持仓列表
    st.markdown("---")
    if st.session_state.holdings:
        # 转为 DataFrame 显示
        df = pd.DataFrame(st.session_state.holdings)
        
        # 添加操作列
        st.dataframe(
            df[['code', 'name', 'cost', 'shares']],
            column_config={
                'code': '代码',
                'name': '名称',
                'cost': st.column_config.NumberColumn('成本价', format="%.2f"),
                'shares': st.column_config.NumberColumn('数量', format="%d")
            },
            use_container_width=True,
            hide_index=True
        )
        
        # 删除持仓
        col1, col2 = st.columns([3, 1])
        with col1:
            delete_code = st.selectbox(
                "选择要删除的股票",
                options=[h['code'] + ' ' + h['name'] for h in st.session_state.holdings]
            )
        with col2:
            st.write("")
            st.write("")
            if st.button("🗑️ 删除", type="secondary"):
                code_to_delete = delete_code.split()[0]
                st.session_state.holdings = [
                    h for h in st.session_state.holdings if h['code'] != code_to_delete
                ]
                st.success(f"已删除 {delete_code}")
                st.rerun()
        
        # 修改成本价
        st.markdown("---")
        st.subheader("修改成本价")
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            edit_stock = st.selectbox(
                "选择股票",
                options=[h['code'] + ' ' + h['name'] for h in st.session_state.holdings],
                key="edit_stock"
            )
        with col2:
            edit_cost = st.number_input("新成本价", min_value=0.0, value=0.0, step=0.01, key="edit_cost")
        with col3:
            st.write("")
            st.write("")
            if st.button("✏️ 更新", key="update_cost"):
                code_to_edit = edit_stock.split()[0]
                for h in st.session_state.holdings:
                    if h['code'] == code_to_edit:
                        h['cost'] = edit_cost
                        st.success(f"已更新 {edit_stock} 成本价为 {edit_cost}")
                        break
    else:
        st.info("暂无持仓，请添加股票")


def render_technical_analysis():
    """技术分析"""
    st.subheader("技术分析")
    
    if not st.session_state.holdings:
        st.info("请先在「持仓管理」中添加股票")
        return
    
    # 选择股票
    selected = st.selectbox(
        "选择要分析的股票",
        options=[f"{h['code']} {h['name']}" for h in st.session_state.holdings]
    )
    
    if st.button("🔍 开始分析", type="primary"):
        code = selected.split()[0]
        name = selected.split()[1] if len(selected.split()) > 1 else ""
        
        with st.spinner(f"正在分析 {code} {name}..."):
            try:
                # 获取数据
                start_date = (datetime.now() - timedelta(days=180)).strftime("%Y%m%d")
                df = DataFetcher.get_stock_daily(code, start_date)
                
                if len(df) < 60:
                    st.error("数据不足，无法分析")
                    return
                
                # 计算指标
                current_price = df['close'].iloc[-1]
                change_pct = df['pct_change'].iloc[-1] if 'pct_change' in df.columns else 0
                
                # 均线
                ma5 = df['close'].rolling(5).mean().iloc[-1]
                ma10 = df['close'].rolling(10).mean().iloc[-1]
                ma20 = df['close'].rolling(20).mean().iloc[-1]
                ma60 = df['close'].rolling(60).mean().iloc[-1]
                
                # MACD
                dif, dea, macd_hist = MACD(df['close'])
                
                # RSI
                rsi = RSI(df['close'], 14).iloc[-1]
                
                # KDJ
                k, d, j = KDJ(df['high'], df['low'], df['close'])
                
                # 布林带
                boll_upper, boll_mid, boll_lower = BOLL(df['close'])
                boll_width = boll_upper.iloc[-1] - boll_lower.iloc[-1]
                boll_position = (current_price - boll_lower.iloc[-1]) / boll_width * 100 if boll_width > 0 else 50
                
                # 显示基本信息
                st.markdown(f"### {code} {name}")
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("当前价格", f"¥{current_price:.2f}", f"{change_pct:+.2f}%")
                with col2:
                    # 查找成本价
                    holding = next((h for h in st.session_state.holdings if h['code'] == code), None)
                    if holding and holding['cost'] > 0:
                        profit_pct = (current_price - holding['cost']) / holding['cost'] * 100
                        st.metric("持仓盈亏", f"{profit_pct:+.2f}%", f"成本 ¥{holding['cost']:.2f}")
                    else:
                        st.metric("持仓盈亏", "未设置成本")
                with col3:
                    st.metric("RSI", f"{rsi:.1f}", "超买" if rsi > 70 else ("超卖" if rsi < 30 else "中性"))
                with col4:
                    st.metric("布林位置", f"{boll_position:.0f}%", "上轨" if boll_position > 80 else ("下轨" if boll_position < 20 else "中轨"))
                
                # 均线分析
                st.markdown("---")
                st.markdown("#### 均线位置")
                
                ma_data = pd.DataFrame({
                    '均线': ['MA5', 'MA10', 'MA20', 'MA60'],
                    '价格': [ma5, ma10, ma20, ma60],
                    '位置': [
                        '✅ 在上方' if current_price > ma5 else '❌ 在下方',
                        '✅ 在上方' if current_price > ma10 else '❌ 在下方',
                        '✅ 在上方' if current_price > ma20 else '❌ 在下方',
                        '✅ 在上方' if current_price > ma60 else '❌ 在下方',
                    ]
                })
                st.dataframe(ma_data, hide_index=True, use_container_width=True)
                
                # 判断均线趋势
                if ma5 > ma10 > ma20 > ma60:
                    st.success("📈 均线多头排列，趋势向上")
                elif ma5 < ma10 < ma20 < ma60:
                    st.error("📉 均线空头排列，趋势向下")
                else:
                    st.warning("〰️ 均线纠缠，方向不明")
                
                # 技术指标详情
                st.markdown("---")
                st.markdown("#### 技术指标")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # MACD
                    macd_status = "金叉（多头）" if dif.iloc[-1] > dea.iloc[-1] else "死叉（空头）"
                    if dif.iloc[-2] <= dea.iloc[-2] and dif.iloc[-1] > dea.iloc[-1]:
                        macd_status = "⚡ 刚金叉！"
                    elif dif.iloc[-2] >= dea.iloc[-2] and dif.iloc[-1] < dea.iloc[-1]:
                        macd_status = "⚡ 刚死叉！"
                    
                    st.markdown(f"""
                    **MACD**
                    - DIF: {dif.iloc[-1]:.3f}
                    - DEA: {dea.iloc[-1]:.3f}
                    - 状态: {macd_status}
                    """)
                
                with col2:
                    # KDJ
                    kdj_status = "观望"
                    if k.iloc[-1] > 80 and d.iloc[-1] > 80:
                        kdj_status = "⚠️ 超买区"
                    elif k.iloc[-1] < 20 and d.iloc[-1] < 20:
                        kdj_status = "💡 超卖区"
                    elif k.iloc[-1] > d.iloc[-1] and k.iloc[-2] <= d.iloc[-2]:
                        kdj_status = "⚡ 金叉"
                    elif k.iloc[-1] < d.iloc[-1] and k.iloc[-2] >= d.iloc[-2]:
                        kdj_status = "⚡ 死叉"
                    
                    st.markdown(f"""
                    **KDJ**
                    - K: {k.iloc[-1]:.1f}
                    - D: {d.iloc[-1]:.1f}
                    - J: {j.iloc[-1]:.1f}
                    - 状态: {kdj_status}
                    """)
                
                # 信号汇总
                st.markdown("---")
                st.markdown("#### 信号汇总")
                
                bullish = []
                bearish = []
                
                if current_price > ma20:
                    bullish.append("站上20日均线")
                else:
                    bearish.append("跌破20日均线")
                
                if dif.iloc[-1] > dea.iloc[-1]:
                    bullish.append("MACD金叉")
                else:
                    bearish.append("MACD死叉")
                
                if rsi < 30:
                    bullish.append("RSI超卖")
                elif rsi > 70:
                    bearish.append("RSI超买")
                
                if boll_position < 20:
                    bullish.append("触及布林下轨")
                elif boll_position > 80:
                    bearish.append("触及布林上轨")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**✅ 多头信号**")
                    if bullish:
                        for s in bullish:
                            st.markdown(f"- {s}")
                    else:
                        st.markdown("- 无")
                
                with col2:
                    st.markdown("**⚠️ 空头信号**")
                    if bearish:
                        for s in bearish:
                            st.markdown(f"- {s}")
                    else:
                        st.markdown("- 无")
                
                # 综合评分
                score = len(bullish) * 20 - len(bearish) * 20
                score = max(-100, min(100, score))
                
                st.markdown("---")
                if score >= 20:
                    st.success(f"📊 综合评分: {score:+d} 分 — 偏多，可持有观察")
                elif score <= -20:
                    st.error(f"📊 综合评分: {score:+d} 分 — 偏空，注意风险")
                else:
                    st.warning(f"📊 综合评分: {score:+d} 分 — 中性，观望为主")
                
                # K线图
                st.markdown("---")
                st.markdown("#### 价格走势（近60日）")
                chart_df = df.tail(60)[['close']].copy()
                chart_df['MA5'] = df['close'].rolling(5).mean().tail(60)
                chart_df['MA20'] = df['close'].rolling(20).mean().tail(60)
                st.line_chart(chart_df)
                
            except Exception as e:
                st.error(f"分析失败: {e}")


def render_risk_monitor():
    """风险监控"""
    st.subheader("风险监控")
    
    if not st.session_state.holdings:
        st.info("请先在「持仓管理」中添加股票")
        return
    
    if st.button("🔄 刷新监控", type="primary"):
        alerts = []
        status_list = []
        
        progress = st.progress(0)
        
        for i, holding in enumerate(st.session_state.holdings):
            code = holding['code']
            name = holding['name']
            cost = holding['cost']
            
            progress.progress((i + 1) / len(st.session_state.holdings), f"正在检查 {code} {name}...")
            
            try:
                start_date = (datetime.now() - timedelta(days=120)).strftime("%Y%m%d")
                df = DataFetcher.get_stock_daily(code, start_date)
                
                if len(df) < 20:
                    continue
                
                current_price = df['close'].iloc[-1]
                change_pct = df['pct_change'].iloc[-1] if 'pct_change' in df.columns else 0
                
                # 更新持仓中的当前价
                holding['current_price'] = current_price
                if holding['highest_price'] == 0 or current_price > holding['highest_price']:
                    holding['highest_price'] = current_price
                
                # 计算盈亏
                profit_pct = 0
                if cost > 0:
                    profit_pct = (current_price - cost) / cost * 100
                
                status_list.append({
                    '代码': code,
                    '名称': name,
                    '现价': current_price,
                    '涨跌': f"{change_pct:+.2f}%",
                    '成本': cost if cost > 0 else '-',
                    '盈亏': f"{profit_pct:+.2f}%" if cost > 0 else '-'
                })
                
                # ========== 检查止损止盈 ==========
                
                if cost > 0:
                    # 固定止损
                    loss_pct = (cost - current_price) / cost * 100
                    if loss_pct >= st.session_state.stop_loss_pct:
                        alerts.append({
                            'level': '🔴 危险',
                            'stock': f"{code} {name}",
                            'type': '止损',
                            'message': f"已亏损 {loss_pct:.1f}%，触发 {st.session_state.stop_loss_pct}% 止损线",
                            'price': current_price
                        })
                    
                    # 固定止盈
                    if profit_pct >= st.session_state.take_profit_pct:
                        alerts.append({
                            'level': '🟢 机会',
                            'stock': f"{code} {name}",
                            'type': '止盈',
                            'message': f"已盈利 {profit_pct:.1f}%，达到 {st.session_state.take_profit_pct}% 止盈线",
                            'price': current_price
                        })
                
                # 移动止盈
                if holding['highest_price'] > 0 and profit_pct > 0:
                    drawdown = (holding['highest_price'] - current_price) / holding['highest_price'] * 100
                    if drawdown >= st.session_state.trailing_stop_pct:
                        alerts.append({
                            'level': '🟡 警告',
                            'stock': f"{code} {name}",
                            'type': '移动止盈',
                            'message': f"从最高点 ¥{holding['highest_price']:.2f} 回撤 {drawdown:.1f}%",
                            'price': current_price
                        })
                
                # ========== 检查均线破位 ==========
                
                ma20 = df['close'].rolling(20).mean()
                prev_close = df['close'].iloc[-2]
                
                if prev_close >= ma20.iloc[-2] and current_price < ma20.iloc[-1]:
                    alerts.append({
                        'level': '🟡 警告',
                        'stock': f"{code} {name}",
                        'type': '破位',
                        'message': f"跌破20日均线 ¥{ma20.iloc[-1]:.2f}",
                        'price': current_price
                    })
                elif prev_close < ma20.iloc[-2] and current_price > ma20.iloc[-1]:
                    alerts.append({
                        'level': '🟢 机会',
                        'stock': f"{code} {name}",
                        'type': '突破',
                        'message': f"突破20日均线 ¥{ma20.iloc[-1]:.2f}",
                        'price': current_price
                    })
                
                # ========== 检查MACD ==========
                
                dif, dea, _ = MACD(df['close'])
                if dif.iloc[-1] > dea.iloc[-1] and dif.iloc[-2] <= dea.iloc[-2]:
                    alerts.append({
                        'level': '🟢 机会',
                        'stock': f"{code} {name}",
                        'type': 'MACD',
                        'message': 'MACD金叉',
                        'price': current_price
                    })
                elif dif.iloc[-1] < dea.iloc[-1] and dif.iloc[-2] >= dea.iloc[-2]:
                    alerts.append({
                        'level': '🟡 警告',
                        'stock': f"{code} {name}",
                        'type': 'MACD',
                        'message': 'MACD死叉',
                        'price': current_price
                    })
                
            except Exception as e:
                st.warning(f"检查 {code} 失败: {e}")
        
        progress.empty()
        
        # 显示持仓状态
        st.markdown("### 持仓状态")
        if status_list:
            st.dataframe(pd.DataFrame(status_list), hide_index=True, use_container_width=True)
        
        # 显示提醒
        st.markdown("### 风险提醒")
        if alerts:
            # 按级别排序
            danger = [a for a in alerts if '危险' in a['level']]
            warning = [a for a in alerts if '警告' in a['level']]
            opportunity = [a for a in alerts if '机会' in a['level']]
            
            if danger:
                st.error("**🔴 危险信号**")
                for a in danger:
                    st.markdown(f"- **{a['stock']}**: {a['message']} (现价 ¥{a['price']:.2f})")
            
            if warning:
                st.warning("**🟡 警告信号**")
                for a in warning:
                    st.markdown(f"- **{a['stock']}**: {a['message']} (现价 ¥{a['price']:.2f})")
            
            if opportunity:
                st.success("**🟢 机会信号**")
                for a in opportunity:
                    st.markdown(f"- **{a['stock']}**: {a['message']} (现价 ¥{a['price']:.2f})")
        else:
            st.success("✅ 当前无需关注的风险提醒")


def render_position_calculator():
    """仓位计算"""
    st.subheader("仓位计算器")
    
    st.markdown("""
    根据止损价和风险控制，计算应该买入多少股。
    
    **原理**：
    - 单笔最大亏损 = 总资金 × 最大亏损比例
    - 每股风险 = 买入价 - 止损价
    - 最大买入股数 = 单笔最大亏损 / 每股风险
    """)
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        calc_price = st.number_input("计划买入价 (元)", min_value=0.01, value=10.0, step=0.1)
        calc_stop = st.number_input("止损价 (元)", min_value=0.01, value=9.0, step=0.1)
    
    with col2:
        calc_capital = st.number_input(
            "总资金 (元)", 
            min_value=10000, 
            value=st.session_state.total_capital,
            step=10000
        )
        calc_max_loss = st.number_input(
            "单笔最大亏损 (%)", 
            min_value=0.5, 
            max_value=10.0,
            value=float(st.session_state.max_loss_per_trade),
            step=0.5
        )
    
    if st.button("📐 计算仓位", type="primary"):
        if calc_stop >= calc_price:
            st.error("止损价必须低于买入价")
        else:
            # 计算
            risk_per_share = calc_price - calc_stop
            stop_pct = risk_per_share / calc_price * 100
            
            max_risk = calc_capital * calc_max_loss / 100
            shares_by_risk = int(max_risk / risk_per_share / 100) * 100
            
            max_position = calc_capital * st.session_state.max_single_pct / 100
            shares_by_position = int(max_position / calc_price / 100) * 100
            
            shares = min(shares_by_risk, shares_by_position)
            amount = shares * calc_price
            position_pct = amount / calc_capital * 100
            actual_max_loss = shares * risk_per_share
            actual_max_loss_pct = actual_max_loss / calc_capital * 100
            
            # 限制原因
            limit_reason = ""
            if shares_by_risk < shares_by_position:
                limit_reason = f"受风险控制限制（单笔最大亏损 {calc_max_loss}%）"
            else:
                limit_reason = f"受仓位限制（单只最大 {st.session_state.max_single_pct}%）"
            
            # 显示结果
            st.markdown("---")
            st.markdown("### 计算结果")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("建议买入", f"{shares} 股", f"{shares // 100} 手")
            with col2:
                st.metric("买入金额", f"¥{amount:,.0f}", f"仓位 {position_pct:.1f}%")
            with col3:
                st.metric("最大亏损", f"¥{actual_max_loss:,.0f}", f"占比 {actual_max_loss_pct:.2f}%")
            
            st.info(f"📌 {limit_reason}")
            
            st.markdown(f"""
            **计算明细**：
            - 止损幅度: {stop_pct:.1f}%
            - 每股风险: ¥{risk_per_share:.2f}
            - 按风险计算: {shares_by_risk} 股
            - 按仓位限制: {shares_by_position} 股
            - 取较小值: {shares} 股
            """)


def render_backtest():
    """策略回测"""
    st.subheader("策略回测")
    
    if not st.session_state.holdings:
        st.info("请先在「持仓管理」中添加股票")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        bt_stock = st.selectbox(
            "选择股票",
            options=[f"{h['code']} {h['name']}" for h in st.session_state.holdings]
        )
    
    with col2:
        bt_strategy = st.selectbox(
            "选择策略",
            options=["双均线(5/20)", "双均线(10/30)", "MACD", "KDJ"]
        )
    
    col1, col2 = st.columns(2)
    with col1:
        bt_start = st.date_input("开始日期", value=datetime.now() - timedelta(days=365))
    with col2:
        bt_end = st.date_input("结束日期", value=datetime.now())
    
    if st.button("📈 运行回测", type="primary"):
        code = bt_stock.split()[0]
        name = bt_stock.split()[1] if len(bt_stock.split()) > 1 else ""
        
        # 选择策略
        if bt_strategy == "双均线(5/20)":
            strategy = MACrossStrategy(5, 20)
        elif bt_strategy == "双均线(10/30)":
            strategy = MACrossStrategy(10, 30)
        elif bt_strategy == "MACD":
            strategy = MACDStrategy()
        else:
            strategy = KDJStrategy()
        
        with st.spinner(f"正在回测 {code} {name}..."):
            try:
                from backtest.engine import BacktestEngine
                
                engine = BacktestEngine(
                    symbol=code,
                    start_date=bt_start.strftime("%Y%m%d"),
                    end_date=bt_end.strftime("%Y%m%d"),
                    initial_capital=st.session_state.total_capital
                )
                engine.set_strategy(strategy)
                result = engine.run()
                
                # 计算买入持有收益
                df = engine.data
                buy_hold_return = (df['close'].iloc[-1] / df['close'].iloc[0] - 1) * 100
                excess_return = result.total_return * 100 - buy_hold_return
                
                # 显示结果
                st.markdown(f"### {code} {name} - {strategy.name}")
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("策略收益", f"{result.total_return*100:+.2f}%")
                with col2:
                    st.metric("买入持有", f"{buy_hold_return:+.2f}%")
                with col3:
                    st.metric("超额收益", f"{excess_return:+.2f}%", 
                              delta="优于" if excess_return > 0 else "不如")
                with col4:
                    st.metric("最大回撤", f"{result.max_drawdown*100:.2f}%")
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("夏普比率", f"{result.sharpe_ratio:.2f}")
                with col2:
                    st.metric("交易次数", f"{result.total_trades}")
                with col3:
                    st.metric("胜率", f"{result.win_rate*100:.1f}%")
                with col4:
                    st.metric("盈亏比", f"{result.profit_factor:.2f}")
                
                # 综合评价
                st.markdown("---")
                if excess_return > 5 and result.max_drawdown < 0.15:
                    st.success("✅ 策略表现优于买入持有，且回撤可控")
                elif excess_return > 0:
                    st.warning("⚠️ 策略略优于买入持有")
                else:
                    st.error("❌ 策略不如买入持有，建议调整参数或换策略")
                
                # 资金曲线
                st.markdown("---")
                st.markdown("#### 资金曲线")
                
                chart_data = pd.DataFrame({
                    "策略资金": result.data["equity"],
                    "买入持有": st.session_state.total_capital * (1 + df["close"].pct_change().cumsum())
                })
                st.line_chart(chart_data)
                
                # 交易明细
                with st.expander("查看交易明细"):
                    trades_df = result.get_trades_df()
                    if not trades_df.empty:
                        st.dataframe(trades_df, use_container_width=True)
                    else:
                        st.info("无交易记录")
                
            except Exception as e:
                st.error(f"回测失败: {e}")


def render_formula_strategy():
    """公式策略页面"""
    st.subheader("📝 公式策略")
    
    st.markdown("""
    使用类似**通达信/同花顺**的公式语法定义买卖条件。
    
    **支持的函数**：
    - 均线: `MA(C,5)`, `EMA(C,12)`, `SMA(C,5,1)`
    - 引用: `REF(C,1)`, `HHV(H,20)`, `LLV(L,10)`
    - 逻辑: `CROSS(MA(C,5),MA(C,20))`, `COUNT(C>MA(C,5),5)`
    - 指标: `RSI(C,14)`, `DIF`, `DEA`, `K`, `D`, `J`
    
    **变量**：`C`=收盘价, `O`=开盘价, `H`=最高价, `L`=最低价, `V`=成交量
    """)
    
    # 模式选择
    mode = st.radio("选择模式", ["使用预设策略", "自定义公式"], horizontal=True)
    
    if mode == "使用预设策略":
        # 显示预设策略列表
        strategies = list_formula_strategies()
        
        col1, col2 = st.columns([1, 2])
        with col1:
            selected_name = st.selectbox(
                "选择策略",
                options=[s["name"] for s in strategies]
            )
        with col2:
            selected = next(s for s in strategies if s["name"] == selected_name)
            st.info(f"📖 {selected['description']}")
        
        if selected_name in FORMULA_LIBRARY:
            config = FORMULA_LIBRARY[selected_name]
            st.code(f"买入条件: {config['buy']}\n卖出条件: {config['sell']}", language="python")
        
        buy_formula = FORMULA_LIBRARY[selected_name]["buy"]
        sell_formula = FORMULA_LIBRARY[selected_name]["sell"]
        strategy_name = selected_name
        
    else:
        # 自定义公式
        st.markdown("---")
        buy_formula = st.text_area(
            "买入条件",
            value="CROSS(MA(df['close'],5), MA(df['close'],20))",
            help="当条件为 True 时触发买入"
        )
        sell_formula = st.text_area(
            "卖出条件", 
            value="CROSS(MA(df['close'],20), MA(df['close'],5))",
            help="当条件为 True 时触发卖出"
        )
        strategy_name = st.text_input("策略名称", value="我的策略")
    
    # 选择股票回测
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        test_code = st.text_input("股票代码", value="000001")
    with col2:
        test_start = st.date_input("开始日期", value=datetime.now() - timedelta(days=365))
    with col3:
        test_capital = st.number_input("初始资金", value=100000, step=10000)
    
    if st.button("🚀 运行公式回测", type="primary"):
        with st.spinner("正在回测..."):
            try:
                from backtest.engine import BacktestEngine
                
                strategy = FormulaStrategy(
                    buy_formula=buy_formula,
                    sell_formula=sell_formula,
                    name=strategy_name
                )
                
                engine = BacktestEngine(
                    symbol=test_code,
                    start_date=test_start.strftime("%Y%m%d"),
                    end_date=datetime.now().strftime("%Y%m%d"),
                    initial_capital=test_capital
                )
                engine.set_strategy(strategy)
                result = engine.run()
                
                # 显示结果
                df = engine.data
                buy_hold = (df['close'].iloc[-1] / df['close'].iloc[0] - 1) * 100
                excess = result.total_return * 100 - buy_hold
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("策略收益", f"{result.total_return*100:+.2f}%")
                with col2:
                    st.metric("买入持有", f"{buy_hold:+.2f}%")
                with col3:
                    st.metric("超额收益", f"{excess:+.2f}%")
                with col4:
                    st.metric("最大回撤", f"{result.max_drawdown*100:.2f}%")
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("夏普比率", f"{result.sharpe_ratio:.2f}")
                with col2:
                    st.metric("交易次数", f"{result.total_trades}")
                with col3:
                    st.metric("胜率", f"{result.win_rate*100:.1f}%")
                with col4:
                    st.metric("盈亏比", f"{result.profit_factor:.2f}")
                
                # 资金曲线
                st.markdown("---")
                chart_data = pd.DataFrame({
                    "策略": result.data["equity"],
                    "买入持有": test_capital * (1 + df["close"].pct_change().cumsum())
                })
                st.line_chart(chart_data)
                
                # 交易明细
                with st.expander("查看交易明细"):
                    trades_df = result.get_trades_df()
                    if not trades_df.empty:
                        st.dataframe(trades_df, use_container_width=True)
                
            except Exception as e:
                st.error(f"回测失败: {e}")
                import traceback
                st.code(traceback.format_exc())


def render_stock_scanner():
    """选股扫描页面"""
    st.subheader("🔎 选股扫描")
    
    st.markdown("""
    使用公式条件筛选符合条件的股票。
    
    **注意**：扫描需要获取每只股票的历史数据，速度较慢。建议先用较小的股票列表测试。
    """)
    
    # 预设选股条件
    from strategy.formula import SCAN_PRESETS, StockScanner
    
    preset = st.selectbox(
        "选择预设条件",
        options=["自定义"] + list(SCAN_PRESETS.keys())
    )
    
    if preset == "自定义":
        st.markdown("---")
        conditions_text = st.text_area(
            "输入条件（每行一个，格式：条件名|公式）",
            value="站上20日线|df['close'] > MA(df['close'],20)\nMACD金叉|CROSS(DIF, DEA)",
            height=150
        )
        conditions = []
        for line in conditions_text.strip().split("\n"):
            if "|" in line:
                name, formula = line.split("|", 1)
                conditions.append((name.strip(), formula.strip()))
    else:
        conditions = SCAN_PRESETS[preset]
        st.markdown("**选中的条件：**")
        for name, formula in conditions:
            st.markdown(f"- {name}: `{formula}`")
    
    st.markdown("---")
    
    # 股票列表
    stock_input = st.text_area(
        "输入股票代码（每行一个）",
        value="000001\n600519\n000858\n600036\n601318",
        height=100
    )
    
    stocks = []
    for line in stock_input.strip().split("\n"):
        code = line.strip()
        if code:
            stocks.append({"code": code, "name": ""})
    
    st.info(f"共 {len(stocks)} 只股票待扫描")
    
    if st.button("🔍 开始扫描", type="primary"):
        scanner = StockScanner()
        for name, formula in conditions:
            scanner.add_condition(name, formula)
        
        progress = st.progress(0)
        status = st.empty()
        
        results = []
        failed = []
        
        for i, stock in enumerate(stocks):
            code = stock["code"]
            progress.progress((i + 1) / len(stocks))
            status.text(f"正在扫描 {code}...")
            
            try:
                start = (datetime.now() - timedelta(days=180)).strftime("%Y%m%d")
                df = DataFetcher.get_stock_daily(code, start)
                
                check_result = scanner.check_stock(df)
                
                if all(check_result.values()):
                    # 获取当前价格
                    current_price = df['close'].iloc[-1]
                    change_pct = df['pct_change'].iloc[-1] if 'pct_change' in df.columns else 0
                    
                    results.append({
                        "代码": code,
                        "现价": f"{current_price:.2f}",
                        "涨跌": f"{change_pct:+.2f}%",
                        **{k: "✅" if v else "❌" for k, v in check_result.items()}
                    })
            except Exception as e:
                failed.append(code)
        
        progress.empty()
        status.empty()
        
        # 显示结果
        st.markdown("### 扫描结果")
        
        if results:
            st.success(f"找到 {len(results)} 只符合条件的股票")
            st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)
        else:
            st.warning("未找到符合条件的股票")
        
        if failed:
            st.caption(f"扫描失败: {', '.join(failed)}")


# 如果直接运行此文件
if __name__ == "__main__":
    render_portfolio_page()
