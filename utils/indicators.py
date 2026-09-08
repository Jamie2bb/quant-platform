"""
技术指标计算工具
"""
import pandas as pd
import numpy as np


def SMA(series: pd.Series, period: int) -> pd.Series:
    """简单移动平均"""
    return series.rolling(window=period).mean()


def EMA(series: pd.Series, period: int) -> pd.Series:
    """指数移动平均"""
    return series.ewm(span=period, adjust=False).mean()


def RSI(series: pd.Series, period: int = 14) -> pd.Series:
    """相对强弱指数"""
    delta = series.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def MACD(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    """MACD 指标"""
    ema_fast = EMA(series, fast)
    ema_slow = EMA(series, slow)
    
    dif = ema_fast - ema_slow
    dea = EMA(dif, signal)
    macd = (dif - dea) * 2
    
    return dif, dea, macd


def BOLL(series: pd.Series, period: int = 20, std_dev: float = 2.0):
    """布林带"""
    mid = SMA(series, period)
    std = series.rolling(window=period).std()
    
    upper = mid + std_dev * std
    lower = mid - std_dev * std
    
    return upper, mid, lower


def KDJ(high: pd.Series, low: pd.Series, close: pd.Series, 
        n: int = 9, m1: int = 3, m2: int = 3):
    """KDJ 指标"""
    lowest_low = low.rolling(window=n).min()
    highest_high = high.rolling(window=n).max()
    
    rsv = (close - lowest_low) / (highest_high - lowest_low) * 100
    
    k = rsv.ewm(com=m1-1, adjust=False).mean()
    d = k.ewm(com=m2-1, adjust=False).mean()
    j = 3 * k - 2 * d
    
    return k, d, j


def ATR(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """平均真实波幅"""
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()


def OBV(close: pd.Series, volume: pd.Series) -> pd.Series:
    """能量潮指标"""
    direction = np.sign(close.diff())
    direction.iloc[0] = 0
    
    obv = (direction * volume).cumsum()
    return obv


def VWAP(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
    """成交量加权平均价"""
    typical_price = (high + low + close) / 3
    return (typical_price * volume).cumsum() / volume.cumsum()


def momentum(series: pd.Series, period: int = 10) -> pd.Series:
    """动量"""
    return series.diff(period)


def rate_of_change(series: pd.Series, period: int = 10) -> pd.Series:
    """变化率"""
    return series.pct_change(period) * 100


def williams_r(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """威廉指标"""
    highest_high = high.rolling(window=period).max()
    lowest_low = low.rolling(window=period).min()
    
    return -100 * (highest_high - close) / (highest_high - lowest_low)


def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    为 DataFrame 添加常用技术指标
    
    Args:
        df: 包含 open, high, low, close, volume 列的 DataFrame
    
    Returns:
        添加了技术指标的 DataFrame
    """
    df = df.copy()
    
    # 均线
    df["ma5"] = SMA(df["close"], 5)
    df["ma10"] = SMA(df["close"], 10)
    df["ma20"] = SMA(df["close"], 20)
    df["ma60"] = SMA(df["close"], 60)
    
    # MACD
    df["dif"], df["dea"], df["macd"] = MACD(df["close"])
    
    # RSI
    df["rsi"] = RSI(df["close"])
    
    # 布林带
    df["boll_upper"], df["boll_mid"], df["boll_lower"] = BOLL(df["close"])
    
    # KDJ
    df["k"], df["d"], df["j"] = KDJ(df["high"], df["low"], df["close"])
    
    # ATR
    df["atr"] = ATR(df["high"], df["low"], df["close"])
    
    return df
