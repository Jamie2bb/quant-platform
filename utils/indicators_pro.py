# -*- coding: utf-8 -*-
"""
专业技术指标库 - 参考通达信/同花顺指标体系
包含 60+ 常用技术指标
"""
import pandas as pd
import numpy as np
from typing import Tuple, Union


# =============================================================================
# 基础函数 - 参考通达信公式函数
# =============================================================================

def REF(series: pd.Series, n: int = 1) -> pd.Series:
    """引用 N 周期前的值（通达信 REF 函数）"""
    return series.shift(n)


def HHV(series: pd.Series, n: int) -> pd.Series:
    """N 周期内最高值（通达信 HHV 函数）"""
    return series.rolling(window=n).max()


def LLV(series: pd.Series, n: int) -> pd.Series:
    """N 周期内最低值（通达信 LLV 函数）"""
    return series.rolling(window=n).min()


def SUM(series: pd.Series, n: int) -> pd.Series:
    """N 周期求和（通达信 SUM 函数）"""
    return series.rolling(window=n).sum()


def STD(series: pd.Series, n: int) -> pd.Series:
    """N 周期标准差（通达信 STD 函数）"""
    return series.rolling(window=n).std()


def AVEDEV(series: pd.Series, n: int) -> pd.Series:
    """N 周期平均绝对偏差（通达信 AVEDEV 函数）"""
    return series.rolling(window=n).apply(lambda x: np.abs(x - x.mean()).mean())


def CROSS(series1: pd.Series, series2: pd.Series) -> pd.Series:
    """上穿判断（通达信 CROSS 函数）"""
    return (series1 > series2) & (series1.shift(1) <= series2.shift(1))


def LONGCROSS(series1: pd.Series, series2: pd.Series, n: int) -> pd.Series:
    """长时间上穿（series1 在 n 周期前低于 series2，现在上穿）"""
    condition1 = series1 > series2
    condition2 = series1.shift(n) < series2.shift(n)
    return condition1 & condition2


def BARSLAST(condition: pd.Series) -> pd.Series:
    """上一次条件成立到现在的周期数"""
    result = pd.Series(index=condition.index, dtype=float)
    last_true = -1
    for i, (idx, val) in enumerate(condition.items()):
        if val:
            last_true = i
            result.iloc[i] = 0
        elif last_true >= 0:
            result.iloc[i] = i - last_true
        else:
            result.iloc[i] = np.nan
    return result


def COUNT(condition: pd.Series, n: int) -> pd.Series:
    """统计 N 周期内条件成立的次数"""
    return condition.astype(int).rolling(window=n).sum()


def EVERY(condition: pd.Series, n: int) -> pd.Series:
    """N 周期内是否一直满足条件"""
    return condition.rolling(window=n).min().astype(bool)


def EXIST(condition: pd.Series, n: int) -> pd.Series:
    """N 周期内是否存在满足条件"""
    return condition.rolling(window=n).max().astype(bool)


def FILTER(condition: pd.Series, n: int) -> pd.Series:
    """过滤连续信号，同一方向信号间隔 N 周期"""
    result = pd.Series(False, index=condition.index)
    last_signal = -n - 1
    for i, (idx, val) in enumerate(condition.items()):
        if val and (i - last_signal > n):
            result.iloc[i] = True
            last_signal = i
    return result


# =============================================================================
# 移动平均线系列
# =============================================================================

def MA(series: pd.Series, n: int) -> pd.Series:
    """简单移动平均（MA）"""
    return series.rolling(window=n).mean()


def EMA(series: pd.Series, n: int) -> pd.Series:
    """指数移动平均（EMA）"""
    return series.ewm(span=n, adjust=False).mean()


def SMA(series: pd.Series, n: int, m: int = 1) -> pd.Series:
    """通达信 SMA 函数: SMA(X,N,M) = (M*X+(N-M)*Y')/N"""
    result = series.copy()
    for i in range(1, len(series)):
        if pd.notna(result.iloc[i-1]):
            result.iloc[i] = (m * series.iloc[i] + (n - m) * result.iloc[i-1]) / n
    return result


def WMA(series: pd.Series, n: int) -> pd.Series:
    """加权移动平均（WMA）"""
    weights = np.arange(1, n + 1)
    return series.rolling(window=n).apply(lambda x: np.dot(x, weights) / weights.sum())


def DEMA(series: pd.Series, n: int) -> pd.Series:
    """双重指数移动平均（DEMA）"""
    ema1 = EMA(series, n)
    ema2 = EMA(ema1, n)
    return 2 * ema1 - ema2


def TEMA(series: pd.Series, n: int) -> pd.Series:
    """三重指数移动平均（TEMA）"""
    ema1 = EMA(series, n)
    ema2 = EMA(ema1, n)
    ema3 = EMA(ema2, n)
    return 3 * ema1 - 3 * ema2 + ema3


def KAMA(series: pd.Series, n: int = 10, fast: int = 2, slow: int = 30) -> pd.Series:
    """考夫曼自适应移动平均（KAMA）"""
    change = abs(series - series.shift(n))
    volatility = series.diff().abs().rolling(window=n).sum()
    er = change / volatility  # 效率比率
    
    fast_sc = 2 / (fast + 1)
    slow_sc = 2 / (slow + 1)
    sc = (er * (fast_sc - slow_sc) + slow_sc) ** 2
    
    kama = series.copy()
    for i in range(n, len(series)):
        kama.iloc[i] = kama.iloc[i-1] + sc.iloc[i] * (series.iloc[i] - kama.iloc[i-1])
    return kama


def ALMA(series: pd.Series, n: int = 9, offset: float = 0.85, sigma: float = 6) -> pd.Series:
    """阿诺德莱格移动平均（ALMA）"""
    m = int(offset * (n - 1))
    s = n / sigma
    weights = np.exp(-((np.arange(n) - m) ** 2) / (2 * s * s))
    weights /= weights.sum()
    return series.rolling(window=n).apply(lambda x: np.dot(x, weights))


# =============================================================================
# 趋势指标
# =============================================================================

def MACD(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """MACD 指标（返回 DIF, DEA, MACD柱）"""
    ema_fast = EMA(close, fast)
    ema_slow = EMA(close, slow)
    dif = ema_fast - ema_slow
    dea = EMA(dif, signal)
    macd = (dif - dea) * 2
    return dif, dea, macd


def DMI(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 14) -> Tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    """动向指标（DMI），返回 PDI, MDI, ADX, ADXR"""
    # True Range
    tr = pd.concat([
        high - low,
        abs(high - close.shift(1)),
        abs(low - close.shift(1))
    ], axis=1).max(axis=1)
    
    # +DM 和 -DM
    hd = high - high.shift(1)
    ld = low.shift(1) - low
    
    pdm = pd.Series(np.where((hd > 0) & (hd > ld), hd, 0), index=high.index)
    mdm = pd.Series(np.where((ld > 0) & (ld > hd), ld, 0), index=high.index)
    
    # 平滑
    tr_sum = SMA(tr, n, 1)
    pdm_sum = SMA(pdm, n, 1)
    mdm_sum = SMA(mdm, n, 1)
    
    # PDI 和 MDI
    pdi = 100 * pdm_sum / tr_sum
    mdi = 100 * mdm_sum / tr_sum
    
    # ADX
    dx = 100 * abs(pdi - mdi) / (pdi + mdi)
    adx = SMA(dx, n, 1)
    adxr = (adx + adx.shift(n)) / 2
    
    return pdi, mdi, adx, adxr


def SAR(high: pd.Series, low: pd.Series, af_step: float = 0.02, af_max: float = 0.2) -> pd.Series:
    """抛物线转向指标（SAR）"""
    length = len(high)
    sar = pd.Series(index=high.index, dtype=float)
    af = af_step
    is_bull = True
    ep = low.iloc[0]
    sar.iloc[0] = high.iloc[0]
    
    for i in range(1, length):
        if is_bull:
            sar.iloc[i] = sar.iloc[i-1] + af * (ep - sar.iloc[i-1])
            sar.iloc[i] = min(sar.iloc[i], low.iloc[i-1], low.iloc[i-2] if i > 1 else low.iloc[i-1])
            
            if high.iloc[i] > ep:
                ep = high.iloc[i]
                af = min(af + af_step, af_max)
            
            if low.iloc[i] < sar.iloc[i]:
                is_bull = False
                sar.iloc[i] = ep
                ep = low.iloc[i]
                af = af_step
        else:
            sar.iloc[i] = sar.iloc[i-1] + af * (ep - sar.iloc[i-1])
            sar.iloc[i] = max(sar.iloc[i], high.iloc[i-1], high.iloc[i-2] if i > 1 else high.iloc[i-1])
            
            if low.iloc[i] < ep:
                ep = low.iloc[i]
                af = min(af + af_step, af_max)
            
            if high.iloc[i] > sar.iloc[i]:
                is_bull = True
                sar.iloc[i] = ep
                ep = high.iloc[i]
                af = af_step
    
    return sar


def SUPERTREND(high: pd.Series, low: pd.Series, close: pd.Series, 
               period: int = 10, multiplier: float = 3.0) -> Tuple[pd.Series, pd.Series]:
    """超级趋势指标（SuperTrend）"""
    atr = ATR(high, low, close, period)
    hl2 = (high + low) / 2
    
    upper_band = hl2 + multiplier * atr
    lower_band = hl2 - multiplier * atr
    
    supertrend = pd.Series(index=close.index, dtype=float)
    direction = pd.Series(index=close.index, dtype=int)
    
    supertrend.iloc[0] = upper_band.iloc[0]
    direction.iloc[0] = 1
    
    for i in range(1, len(close)):
        if close.iloc[i] > upper_band.iloc[i-1]:
            direction.iloc[i] = 1
        elif close.iloc[i] < lower_band.iloc[i-1]:
            direction.iloc[i] = -1
        else:
            direction.iloc[i] = direction.iloc[i-1]
        
        if direction.iloc[i] == 1:
            supertrend.iloc[i] = max(lower_band.iloc[i], supertrend.iloc[i-1]) if direction.iloc[i-1] == 1 else lower_band.iloc[i]
        else:
            supertrend.iloc[i] = min(upper_band.iloc[i], supertrend.iloc[i-1]) if direction.iloc[i-1] == -1 else upper_band.iloc[i]
    
    return supertrend, direction


def ICHIMOKU(high: pd.Series, low: pd.Series, close: pd.Series,
             tenkan: int = 9, kijun: int = 26, senkou_b: int = 52) -> dict:
    """一目均衡表（Ichimoku Cloud）"""
    # 转换线（Tenkan-sen）
    tenkan_sen = (HHV(high, tenkan) + LLV(low, tenkan)) / 2
    
    # 基准线（Kijun-sen）
    kijun_sen = (HHV(high, kijun) + LLV(low, kijun)) / 2
    
    # 先行带 A（Senkou Span A）
    senkou_span_a = ((tenkan_sen + kijun_sen) / 2).shift(kijun)
    
    # 先行带 B（Senkou Span B）
    senkou_span_b = ((HHV(high, senkou_b) + LLV(low, senkou_b)) / 2).shift(kijun)
    
    # 迟行带（Chikou Span）
    chikou_span = close.shift(-kijun)
    
    return {
        'tenkan_sen': tenkan_sen,
        'kijun_sen': kijun_sen,
        'senkou_span_a': senkou_span_a,
        'senkou_span_b': senkou_span_b,
        'chikou_span': chikou_span
    }


# =============================================================================
# 震荡指标
# =============================================================================

def RSI(close: pd.Series, n: int = 14) -> pd.Series:
    """相对强弱指数（RSI）"""
    delta = close.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    avg_gain = SMA(gain, n, 1)
    avg_loss = SMA(loss, n, 1)
    
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def KDJ(high: pd.Series, low: pd.Series, close: pd.Series,
        n: int = 9, m1: int = 3, m2: int = 3) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """KDJ 随机指标"""
    lowest_low = LLV(low, n)
    highest_high = HHV(high, n)
    
    rsv = (close - lowest_low) / (highest_high - lowest_low) * 100
    rsv = rsv.fillna(50)
    
    k = SMA(rsv, m1, 1)
    d = SMA(k, m2, 1)
    j = 3 * k - 2 * d
    
    return k, d, j


def STOCH(high: pd.Series, low: pd.Series, close: pd.Series,
          k_period: int = 14, d_period: int = 3) -> Tuple[pd.Series, pd.Series]:
    """随机指标（Stochastic）"""
    lowest_low = LLV(low, k_period)
    highest_high = HHV(high, k_period)
    
    k = 100 * (close - lowest_low) / (highest_high - lowest_low)
    d = MA(k, d_period)
    
    return k, d


def CCI(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 14) -> pd.Series:
    """商品通道指数（CCI）"""
    tp = (high + low + close) / 3
    ma_tp = MA(tp, n)
    md = AVEDEV(tp, n)
    return (tp - ma_tp) / (0.015 * md)


def WILLR(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 14) -> pd.Series:
    """威廉指标（Williams %R）"""
    highest_high = HHV(high, n)
    lowest_low = LLV(low, n)
    return -100 * (highest_high - close) / (highest_high - lowest_low)


def ROC(close: pd.Series, n: int = 12) -> pd.Series:
    """变动率指标（ROC）"""
    return (close - close.shift(n)) / close.shift(n) * 100


def MOMENTUM(close: pd.Series, n: int = 10) -> pd.Series:
    """动量指标（Momentum）"""
    return close - close.shift(n)


def TRIX(close: pd.Series, n: int = 12) -> pd.Series:
    """三重指数平滑移动平均（TRIX）"""
    ema1 = EMA(close, n)
    ema2 = EMA(ema1, n)
    ema3 = EMA(ema2, n)
    return (ema3 - ema3.shift(1)) / ema3.shift(1) * 100


def DPO(close: pd.Series, n: int = 20) -> pd.Series:
    """去趋势价格摆动（DPO）"""
    shift_period = n // 2 + 1
    return close.shift(shift_period) - MA(close, n)


def UO(high: pd.Series, low: pd.Series, close: pd.Series,
       s: int = 7, m: int = 14, l: int = 28) -> pd.Series:
    """终极波动指标（Ultimate Oscillator）"""
    prev_close = close.shift(1)
    bp = close - pd.concat([low, prev_close], axis=1).min(axis=1)
    tr = pd.concat([high, prev_close], axis=1).max(axis=1) - pd.concat([low, prev_close], axis=1).min(axis=1)
    
    avg_s = SUM(bp, s) / SUM(tr, s)
    avg_m = SUM(bp, m) / SUM(tr, m)
    avg_l = SUM(bp, l) / SUM(tr, l)
    
    return 100 * (4 * avg_s + 2 * avg_m + avg_l) / 7


def AO(high: pd.Series, low: pd.Series) -> pd.Series:
    """动量震荡器（Awesome Oscillator）"""
    median = (high + low) / 2
    return MA(median, 5) - MA(median, 34)


def AC(high: pd.Series, low: pd.Series) -> pd.Series:
    """加速震荡器（Accelerator Oscillator）"""
    ao = AO(high, low)
    return ao - MA(ao, 5)


# =============================================================================
# 波动率指标
# =============================================================================

def ATR(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 14) -> pd.Series:
    """平均真实波幅（ATR）"""
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return SMA(tr, n, 1)


def BOLL(close: pd.Series, n: int = 20, std_dev: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """布林带（Bollinger Bands）"""
    mid = MA(close, n)
    std = STD(close, n)
    upper = mid + std_dev * std
    lower = mid - std_dev * std
    return upper, mid, lower


def BOLL_WIDTH(close: pd.Series, n: int = 20, std_dev: float = 2.0) -> pd.Series:
    """布林带宽度"""
    upper, mid, lower = BOLL(close, n, std_dev)
    return (upper - lower) / mid * 100


def BOLL_PCT(close: pd.Series, n: int = 20, std_dev: float = 2.0) -> pd.Series:
    """布林带百分比（%B）"""
    upper, mid, lower = BOLL(close, n, std_dev)
    return (close - lower) / (upper - lower)


def KC(high: pd.Series, low: pd.Series, close: pd.Series, 
       n: int = 20, atr_mult: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """肯特纳通道（Keltner Channel）"""
    mid = EMA(close, n)
    atr = ATR(high, low, close, n)
    upper = mid + atr_mult * atr
    lower = mid - atr_mult * atr
    return upper, mid, lower


def DC(high: pd.Series, low: pd.Series, n: int = 20) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """唐奇安通道（Donchian Channel）"""
    upper = HHV(high, n)
    lower = LLV(low, n)
    mid = (upper + lower) / 2
    return upper, mid, lower


def NATR(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 14) -> pd.Series:
    """标准化 ATR"""
    atr = ATR(high, low, close, n)
    return atr / close * 100


def CHAIKIN_VOL(high: pd.Series, low: pd.Series, n: int = 10, roc_n: int = 10) -> pd.Series:
    """蔡金波动率（Chaikin Volatility）"""
    hl_ema = EMA(high - low, n)
    return ROC(hl_ema, roc_n)


# =============================================================================
# 成交量指标
# =============================================================================

def OBV(close: pd.Series, volume: pd.Series) -> pd.Series:
    """能量潮指标（OBV）"""
    direction = np.sign(close.diff())
    direction.iloc[0] = 0
    return (direction * volume).cumsum()


def VWAP(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
    """成交量加权平均价（VWAP）"""
    tp = (high + low + close) / 3
    return (tp * volume).cumsum() / volume.cumsum()


def MFI(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series, n: int = 14) -> pd.Series:
    """资金流量指标（MFI）"""
    tp = (high + low + close) / 3
    mf = tp * volume
    
    delta = tp.diff()
    positive_mf = mf.where(delta > 0, 0)
    negative_mf = mf.where(delta < 0, 0)
    
    positive_sum = SUM(positive_mf, n)
    negative_sum = SUM(negative_mf, n)
    
    mfi = 100 - 100 / (1 + positive_sum / negative_sum)
    return mfi


def AD(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
    """累积/派发线（A/D Line）"""
    clv = ((close - low) - (high - close)) / (high - low)
    clv = clv.fillna(0)
    return (clv * volume).cumsum()


def ADOSC(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series,
          fast: int = 3, slow: int = 10) -> pd.Series:
    """蔡金 A/D 震荡器（Chaikin A/D Oscillator）"""
    ad = AD(high, low, close, volume)
    return EMA(ad, fast) - EMA(ad, slow)


def CMF(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series, n: int = 20) -> pd.Series:
    """蔡金资金流（Chaikin Money Flow）"""
    clv = ((close - low) - (high - close)) / (high - low)
    clv = clv.fillna(0)
    return SUM(clv * volume, n) / SUM(volume, n)


def EMV(high: pd.Series, low: pd.Series, volume: pd.Series, n: int = 14) -> pd.Series:
    """简易波动指标（Ease of Movement）"""
    dm = ((high + low) / 2) - ((high.shift(1) + low.shift(1)) / 2)
    br = volume / (high - low)
    emv = dm / br
    return MA(emv, n)


def VPT(close: pd.Series, volume: pd.Series) -> pd.Series:
    """量价趋势指标（VPT）"""
    return (volume * close.pct_change()).cumsum()


def NVI(close: pd.Series, volume: pd.Series) -> pd.Series:
    """负成交量指标（NVI）"""
    nvi = pd.Series(1000.0, index=close.index)
    for i in range(1, len(close)):
        if volume.iloc[i] < volume.iloc[i-1]:
            nvi.iloc[i] = nvi.iloc[i-1] * (1 + close.pct_change().iloc[i])
        else:
            nvi.iloc[i] = nvi.iloc[i-1]
    return nvi


def PVI(close: pd.Series, volume: pd.Series) -> pd.Series:
    """正成交量指标（PVI）"""
    pvi = pd.Series(1000.0, index=close.index)
    for i in range(1, len(close)):
        if volume.iloc[i] > volume.iloc[i-1]:
            pvi.iloc[i] = pvi.iloc[i-1] * (1 + close.pct_change().iloc[i])
        else:
            pvi.iloc[i] = pvi.iloc[i-1]
    return pvi


def VOLUME_RATIO(volume: pd.Series, n: int = 5) -> pd.Series:
    """量比"""
    avg_vol = MA(volume.shift(1), n)
    return volume / avg_vol


def VOLUME_OSC(volume: pd.Series, fast: int = 5, slow: int = 10) -> pd.Series:
    """成交量震荡器"""
    return (MA(volume, fast) - MA(volume, slow)) / MA(volume, slow) * 100


# =============================================================================
# 强弱指标
# =============================================================================

def ADX(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 14) -> pd.Series:
    """平均方向指数（ADX）"""
    _, _, adx, _ = DMI(high, low, close, n)
    return adx


def AROON(high: pd.Series, low: pd.Series, n: int = 25) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """阿隆指标（Aroon）"""
    aroon_up = 100 * high.rolling(window=n+1).apply(lambda x: n - x.argmax()) / n
    aroon_down = 100 * low.rolling(window=n+1).apply(lambda x: n - x.argmin()) / n
    aroon_osc = aroon_up - aroon_down
    return aroon_up, aroon_down, aroon_osc


def MASS_INDEX(high: pd.Series, low: pd.Series, ema_n: int = 9, sum_n: int = 25) -> pd.Series:
    """质量指数（Mass Index）"""
    hl_range = high - low
    ema1 = EMA(hl_range, ema_n)
    ema2 = EMA(ema1, ema_n)
    ratio = ema1 / ema2
    return SUM(ratio, sum_n)


def VORTEX(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 14) -> Tuple[pd.Series, pd.Series]:
    """旋涡指标（Vortex）"""
    tr = pd.concat([
        high - low,
        abs(high - close.shift(1)),
        abs(low - close.shift(1))
    ], axis=1).max(axis=1)
    
    vm_plus = abs(high - low.shift(1))
    vm_minus = abs(low - high.shift(1))
    
    tr_sum = SUM(tr, n)
    vi_plus = SUM(vm_plus, n) / tr_sum
    vi_minus = SUM(vm_minus, n) / tr_sum
    
    return vi_plus, vi_minus


# =============================================================================
# 综合计算函数
# =============================================================================

def add_all_indicators(df: pd.DataFrame, include_advanced: bool = False) -> pd.DataFrame:
    """
    为 DataFrame 添加所有技术指标
    
    Args:
        df: 包含 open, high, low, close, volume 列的 DataFrame
        include_advanced: 是否包含高级指标
    
    Returns:
        添加了技术指标的 DataFrame
    """
    result = df.copy()
    
    # 基础均线
    for n in [5, 10, 20, 60, 120, 250]:
        result[f'ma{n}'] = MA(df['close'], n)
    
    result['ema12'] = EMA(df['close'], 12)
    result['ema26'] = EMA(df['close'], 26)
    
    # MACD
    result['dif'], result['dea'], result['macd'] = MACD(df['close'])
    
    # KDJ
    result['k'], result['d'], result['j'] = KDJ(df['high'], df['low'], df['close'])
    
    # RSI
    result['rsi6'] = RSI(df['close'], 6)
    result['rsi12'] = RSI(df['close'], 12)
    result['rsi24'] = RSI(df['close'], 24)
    
    # 布林带
    result['boll_upper'], result['boll_mid'], result['boll_lower'] = BOLL(df['close'])
    result['boll_pct'] = BOLL_PCT(df['close'])
    
    # ATR
    result['atr'] = ATR(df['high'], df['low'], df['close'])
    
    # 成交量指标
    result['obv'] = OBV(df['close'], df['volume'])
    result['volume_ratio'] = VOLUME_RATIO(df['volume'])
    
    # 威廉指标
    result['wr'] = WILLR(df['high'], df['low'], df['close'])
    
    # CCI
    result['cci'] = CCI(df['high'], df['low'], df['close'])
    
    # ROC
    result['roc'] = ROC(df['close'], 12)
    
    if include_advanced:
        # DMI
        result['pdi'], result['mdi'], result['adx'], result['adxr'] = DMI(df['high'], df['low'], df['close'])
        
        # SAR
        result['sar'] = SAR(df['high'], df['low'])
        
        # 超级趋势
        result['supertrend'], result['supertrend_dir'] = SUPERTREND(df['high'], df['low'], df['close'])
        
        # MFI
        result['mfi'] = MFI(df['high'], df['low'], df['close'], df['volume'])
        
        # CMF
        result['cmf'] = CMF(df['high'], df['low'], df['close'], df['volume'])
        
        # TRIX
        result['trix'] = TRIX(df['close'])
        
        # 阿隆指标
        result['aroon_up'], result['aroon_down'], result['aroon_osc'] = AROON(df['high'], df['low'])
    
    return result


# =============================================================================
# 信号生成函数
# =============================================================================

def generate_signals(df: pd.DataFrame) -> dict:
    """
    根据技术指标生成交易信号
    
    Returns:
        dict: 各类信号汇总
    """
    signals = {
        'bullish': [],
        'bearish': [],
        'neutral': []
    }
    
    if len(df) < 60:
        return signals
    
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    
    # MACD 信号
    if 'dif' in df.columns and 'dea' in df.columns:
        if latest['dif'] > latest['dea'] and prev['dif'] <= prev['dea']:
            signals['bullish'].append('MACD金叉')
        elif latest['dif'] < latest['dea'] and prev['dif'] >= prev['dea']:
            signals['bearish'].append('MACD死叉')
        elif latest['dif'] > latest['dea']:
            signals['bullish'].append('MACD多头')
        else:
            signals['bearish'].append('MACD空头')
    
    # KDJ 信号
    if 'k' in df.columns and 'd' in df.columns:
        if latest['k'] > 80 and latest['d'] > 80:
            signals['bearish'].append('KDJ超买')
        elif latest['k'] < 20 and latest['d'] < 20:
            signals['bullish'].append('KDJ超卖')
        elif latest['k'] > latest['d'] and prev['k'] <= prev['d']:
            signals['bullish'].append('KDJ金叉')
        elif latest['k'] < latest['d'] and prev['k'] >= prev['d']:
            signals['bearish'].append('KDJ死叉')
    
    # RSI 信号
    if 'rsi12' in df.columns:
        rsi = latest['rsi12']
        if rsi > 70:
            signals['bearish'].append(f'RSI超买({rsi:.0f})')
        elif rsi < 30:
            signals['bullish'].append(f'RSI超卖({rsi:.0f})')
    
    # 布林带信号
    if 'boll_pct' in df.columns:
        boll_pct = latest['boll_pct']
        if boll_pct > 0.9:
            signals['bearish'].append('触及布林上轨')
        elif boll_pct < 0.1:
            signals['bullish'].append('触及布林下轨')
    
    # 均线信号
    if all(f'ma{n}' in df.columns for n in [5, 10, 20, 60]):
        ma5, ma10, ma20, ma60 = latest['ma5'], latest['ma10'], latest['ma20'], latest['ma60']
        if ma5 > ma10 > ma20 > ma60:
            signals['bullish'].append('均线多头排列')
        elif ma5 < ma10 < ma20 < ma60:
            signals['bearish'].append('均线空头排列')
    
    # 量价信号
    if 'volume_ratio' in df.columns:
        vr = latest['volume_ratio']
        if vr > 2:
            signals['neutral'].append(f'放量({vr:.1f}倍)')
        elif vr < 0.5:
            signals['neutral'].append(f'缩量({vr:.1f}倍)')
    
    return signals
