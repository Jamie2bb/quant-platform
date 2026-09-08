"""
Alpha 因子库 - 参考 Qlib Alpha Factors
提供量化投资常用的因子计算
"""
import pandas as pd
import numpy as np
from abc import ABC, abstractmethod
from typing import Optional


class BaseFactor(ABC):
    """因子基类"""
    
    def __init__(self, name: str = None):
        self.name = name or self.__class__.__name__
    
    @abstractmethod
    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """计算因子值"""
        pass
    
    def __call__(self, data: pd.DataFrame) -> pd.Series:
        return self.calculate(data)


# ============ 动量因子 ============

class MomentumFactor(BaseFactor):
    """动量因子: N日收益率"""
    
    def __init__(self, period: int = 20):
        super().__init__(f"Momentum_{period}")
        self.period = period
    
    def calculate(self, data: pd.DataFrame) -> pd.Series:
        return data["close"].pct_change(self.period)


class ReversalFactor(BaseFactor):
    """反转因子: 短期反转效应"""
    
    def __init__(self, period: int = 5):
        super().__init__(f"Reversal_{period}")
        self.period = period
    
    def calculate(self, data: pd.DataFrame) -> pd.Series:
        # 负的短期收益率（反转）
        return -data["close"].pct_change(self.period)


class RSFactor(BaseFactor):
    """相对强弱因子: 相对于均值的位置"""
    
    def __init__(self, period: int = 20):
        super().__init__(f"RS_{period}")
        self.period = period
    
    def calculate(self, data: pd.DataFrame) -> pd.Series:
        close = data["close"]
        ma = close.rolling(self.period).mean()
        std = close.rolling(self.period).std()
        return (close - ma) / std


# ============ 波动率因子 ============

class VolatilityFactor(BaseFactor):
    """波动率因子: 历史波动率"""
    
    def __init__(self, period: int = 20):
        super().__init__(f"Volatility_{period}")
        self.period = period
    
    def calculate(self, data: pd.DataFrame) -> pd.Series:
        returns = data["close"].pct_change()
        return returns.rolling(self.period).std() * np.sqrt(252)


class ATRFactor(BaseFactor):
    """ATR因子: 平均真实波幅"""
    
    def __init__(self, period: int = 14):
        super().__init__(f"ATR_{period}")
        self.period = period
    
    def calculate(self, data: pd.DataFrame) -> pd.Series:
        high = data["high"]
        low = data["low"]
        close = data["close"]
        
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(self.period).mean()
        
        # 标准化为比例
        return atr / close


class VolatilityRatioFactor(BaseFactor):
    """波动率比率: 短期波动/长期波动"""
    
    def __init__(self, short_period: int = 5, long_period: int = 20):
        super().__init__(f"VolRatio_{short_period}_{long_period}")
        self.short_period = short_period
        self.long_period = long_period
    
    def calculate(self, data: pd.DataFrame) -> pd.Series:
        returns = data["close"].pct_change()
        short_vol = returns.rolling(self.short_period).std()
        long_vol = returns.rolling(self.long_period).std()
        return short_vol / long_vol


# ============ 成交量因子 ============

class VolumeFactor(BaseFactor):
    """成交量因子: 量比"""
    
    def __init__(self, period: int = 20):
        super().__init__(f"Volume_{period}")
        self.period = period
    
    def calculate(self, data: pd.DataFrame) -> pd.Series:
        volume = data["volume"]
        avg_vol = volume.rolling(self.period).mean()
        return volume / avg_vol


class VolumeMAFactor(BaseFactor):
    """成交量均线因子"""
    
    def __init__(self, short_period: int = 5, long_period: int = 20):
        super().__init__(f"VolumeMA_{short_period}_{long_period}")
        self.short_period = short_period
        self.long_period = long_period
    
    def calculate(self, data: pd.DataFrame) -> pd.Series:
        volume = data["volume"]
        short_ma = volume.rolling(self.short_period).mean()
        long_ma = volume.rolling(self.long_period).mean()
        return short_ma / long_ma - 1


class AmountFactor(BaseFactor):
    """成交额因子: 换手率代理"""
    
    def __init__(self, period: int = 20):
        super().__init__(f"Amount_{period}")
        self.period = period
    
    def calculate(self, data: pd.DataFrame) -> pd.Series:
        amount = data["close"] * data["volume"]
        avg_amount = amount.rolling(self.period).mean()
        return amount / avg_amount


class OBVFactor(BaseFactor):
    """OBV因子: 能量潮"""
    
    def __init__(self, period: int = 20):
        super().__init__(f"OBV_{period}")
        self.period = period
    
    def calculate(self, data: pd.DataFrame) -> pd.Series:
        close = data["close"]
        volume = data["volume"]
        
        direction = np.sign(close.diff())
        obv = (volume * direction).cumsum()
        
        # 标准化
        obv_ma = obv.rolling(self.period).mean()
        obv_std = obv.rolling(self.period).std()
        return (obv - obv_ma) / obv_std


# ============ 价格形态因子 ============

class HighLowFactor(BaseFactor):
    """价格位置因子: 当前价在N日高低点的位置"""
    
    def __init__(self, period: int = 20):
        super().__init__(f"HighLow_{period}")
        self.period = period
    
    def calculate(self, data: pd.DataFrame) -> pd.Series:
        close = data["close"]
        high_n = data["high"].rolling(self.period).max()
        low_n = data["low"].rolling(self.period).min()
        return (close - low_n) / (high_n - low_n)


class GapFactor(BaseFactor):
    """跳空因子: 开盘缺口"""
    
    def calculate(self, data: pd.DataFrame) -> pd.Series:
        return (data["open"] - data["close"].shift(1)) / data["close"].shift(1)


class BodyFactor(BaseFactor):
    """实体因子: K线实体大小"""
    
    def calculate(self, data: pd.DataFrame) -> pd.Series:
        body = abs(data["close"] - data["open"])
        range_ = data["high"] - data["low"]
        return body / range_


class ShadowFactor(BaseFactor):
    """影线因子: 上下影线比例"""
    
    def calculate(self, data: pd.DataFrame) -> pd.Series:
        upper_shadow = data["high"] - data[["open", "close"]].max(axis=1)
        lower_shadow = data[["open", "close"]].min(axis=1) - data["low"]
        range_ = data["high"] - data["low"]
        return (upper_shadow - lower_shadow) / range_


# ============ 趋势因子 ============

class TrendFactor(BaseFactor):
    """趋势因子: 价格与均线的偏离"""
    
    def __init__(self, period: int = 20):
        super().__init__(f"Trend_{period}")
        self.period = period
    
    def calculate(self, data: pd.DataFrame) -> pd.Series:
        close = data["close"]
        ma = close.rolling(self.period).mean()
        return (close - ma) / ma


class TrendStrengthFactor(BaseFactor):
    """趋势强度因子: ADX"""
    
    def __init__(self, period: int = 14):
        super().__init__(f"TrendStrength_{period}")
        self.period = period
    
    def calculate(self, data: pd.DataFrame) -> pd.Series:
        high = data["high"]
        low = data["low"]
        close = data["close"]
        
        # +DM, -DM
        plus_dm = high.diff()
        minus_dm = -low.diff()
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0
        plus_dm[(plus_dm < minus_dm)] = 0
        minus_dm[(minus_dm < plus_dm)] = 0
        
        # TR
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # Smoothed
        atr = tr.rolling(self.period).mean()
        plus_di = 100 * (plus_dm.rolling(self.period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(self.period).mean() / atr)
        
        # ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(self.period).mean()
        
        return adx / 100  # 标准化到 0-1


class MACDFactor(BaseFactor):
    """MACD因子"""
    
    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        super().__init__(f"MACD_{fast}_{slow}_{signal}")
        self.fast = fast
        self.slow = slow
        self.signal = signal
    
    def calculate(self, data: pd.DataFrame) -> pd.Series:
        close = data["close"]
        ema_fast = close.ewm(span=self.fast, adjust=False).mean()
        ema_slow = close.ewm(span=self.slow, adjust=False).mean()
        macd = ema_fast - ema_slow
        signal = macd.ewm(span=self.signal, adjust=False).mean()
        
        # 标准化
        return (macd - signal) / close


# ============ 相关性因子 ============

class BetaFactor(BaseFactor):
    """Beta因子: 相对于基准的系统性风险"""
    
    def __init__(self, period: int = 60):
        super().__init__(f"Beta_{period}")
        self.period = period
    
    def calculate(self, data: pd.DataFrame, benchmark: pd.Series = None) -> pd.Series:
        returns = data["close"].pct_change()
        
        if benchmark is None:
            # 如果没有基准，用自身均值作为代理
            benchmark = returns.rolling(self.period).mean()
        
        # 计算 beta = Cov(r, rm) / Var(rm)
        cov = returns.rolling(self.period).cov(benchmark)
        var = benchmark.rolling(self.period).var()
        
        return cov / var


class CorrelationFactor(BaseFactor):
    """相关性因子: 与成交量的相关性"""
    
    def __init__(self, period: int = 20):
        super().__init__(f"PriceVolCorr_{period}")
        self.period = period
    
    def calculate(self, data: pd.DataFrame) -> pd.Series:
        returns = data["close"].pct_change()
        volume_change = data["volume"].pct_change()
        return returns.rolling(self.period).corr(volume_change)


# ============ 组合因子 ============

class QualityFactor(BaseFactor):
    """质量因子: 综合评分"""
    
    def __init__(self, period: int = 20):
        super().__init__(f"Quality_{period}")
        self.period = period
    
    def calculate(self, data: pd.DataFrame) -> pd.Series:
        close = data["close"]
        volume = data["volume"]
        
        # 稳定性（低波动率为好）
        vol = close.pct_change().rolling(self.period).std()
        vol_score = 1 - (vol - vol.rolling(60).min()) / (vol.rolling(60).max() - vol.rolling(60).min())
        
        # 流动性（高成交量为好）
        vol_ratio = volume / volume.rolling(self.period).mean()
        liq_score = vol_ratio.clip(0, 2) / 2
        
        # 趋势（上涨趋势为好）
        trend = close / close.rolling(self.period).mean() - 1
        trend_score = (trend + 0.2) / 0.4  # 标准化
        
        # 综合得分
        return 0.4 * vol_score + 0.3 * liq_score + 0.3 * trend_score


class CompositeMomentumFactor(BaseFactor):
    """复合动量因子"""
    
    def __init__(self):
        super().__init__("CompositeMomentum")
    
    def calculate(self, data: pd.DataFrame) -> pd.Series:
        close = data["close"]
        
        # 多周期动量
        mom_5 = close.pct_change(5)
        mom_10 = close.pct_change(10)
        mom_20 = close.pct_change(20)
        
        # 标准化
        def zscore(s):
            return (s - s.rolling(60).mean()) / s.rolling(60).std()
        
        return 0.5 * zscore(mom_5) + 0.3 * zscore(mom_10) + 0.2 * zscore(mom_20)


# ============ 因子计算器 ============

class FactorCalculator:
    """
    因子计算器
    
    批量计算多个因子
    """
    
    def __init__(self):
        self.factors: list = []
    
    def add_factor(self, factor: BaseFactor):
        """添加因子"""
        self.factors.append(factor)
        return self
    
    def add_all_basic_factors(self):
        """添加所有基础因子"""
        self.factors.extend([
            MomentumFactor(20),
            MomentumFactor(60),
            ReversalFactor(5),
            RSFactor(20),
            VolatilityFactor(20),
            ATRFactor(14),
            VolumeFactor(20),
            OBVFactor(20),
            HighLowFactor(20),
            TrendFactor(20),
            TrendStrengthFactor(14),
            MACDFactor(),
            QualityFactor(20),
            CompositeMomentumFactor()
        ])
        return self
    
    def calculate(self, data: pd.DataFrame) -> pd.DataFrame:
        """计算所有因子"""
        results = {}
        
        for factor in self.factors:
            try:
                results[factor.name] = factor.calculate(data)
            except Exception as e:
                print(f"计算因子 {factor.name} 失败: {e}")
                results[factor.name] = pd.Series(np.nan, index=data.index)
        
        return pd.DataFrame(results)
    
    def get_factor_names(self) -> list:
        """获取因子名称列表"""
        return [f.name for f in self.factors]


# 预定义因子集合
MOMENTUM_FACTORS = [
    MomentumFactor(5),
    MomentumFactor(10),
    MomentumFactor(20),
    MomentumFactor(60),
    ReversalFactor(5),
    RSFactor(20),
]

VOLATILITY_FACTORS = [
    VolatilityFactor(10),
    VolatilityFactor(20),
    ATRFactor(14),
    VolatilityRatioFactor(5, 20),
]

VOLUME_FACTORS = [
    VolumeFactor(5),
    VolumeFactor(20),
    VolumeMAFactor(5, 20),
    AmountFactor(20),
    OBVFactor(20),
]

TREND_FACTORS = [
    TrendFactor(10),
    TrendFactor(20),
    TrendFactor(60),
    TrendStrengthFactor(14),
    MACDFactor(),
]

ALL_FACTORS = MOMENTUM_FACTORS + VOLATILITY_FACTORS + VOLUME_FACTORS + TREND_FACTORS
