"""
Alpha158 因子库 - 参考 Qlib Alpha158
这是微软 Qlib 项目中最经典的因子集，包含 158 个技术因子
"""
import pandas as pd
import numpy as np
from typing import Dict


class Alpha158:
    """
    Qlib Alpha158 因子计算器
    
    包含 6 大类因子：
    1. KBAR - K线形态因子 (6个)
    2. PRICE - 价格因子 (5个)  
    3. VOLUME - 成交量因子 (5个)
    4. HIGH/LOW - 高低价因子 (4个)
    5. ROLLING - 滚动统计因子 (多个)
    6. TECHNICAL - 技术指标因子 (多个)
    """
    
    def __init__(self, data: pd.DataFrame):
        """
        Args:
            data: 包含 open, high, low, close, volume 的 DataFrame
        """
        self.data = data.copy()
        self.factors = pd.DataFrame(index=data.index)
        
        # 标准化列名
        self.open = data['open']
        self.high = data['high']
        self.low = data['low']
        self.close = data['close']
        self.volume = data['volume']
        self.vwap = (data['close'] * data['volume']).cumsum() / data['volume'].cumsum()
    
    def calculate_all(self) -> pd.DataFrame:
        """计算所有 Alpha158 因子"""
        self._kbar_factors()
        self._price_factors()
        self._volume_factors()
        self._high_low_factors()
        self._rolling_factors()
        self._technical_factors()
        self._return_factors()
        
        return self.factors
    
    def _kbar_factors(self):
        """K线形态因子"""
        # KMID: (close - open) / open
        self.factors['KMID'] = (self.close - self.open) / self.open
        
        # KLEN: (high - low) / open
        self.factors['KLEN'] = (self.high - self.low) / self.open
        
        # KMID2: (close - open) / (high - low + 1e-12)
        self.factors['KMID2'] = (self.close - self.open) / (self.high - self.low + 1e-12)
        
        # KUP: (high - max(open, close)) / open
        self.factors['KUP'] = (self.high - np.maximum(self.open, self.close)) / self.open
        
        # KUP2: (high - max(open, close)) / (high - low + 1e-12)
        self.factors['KUP2'] = (self.high - np.maximum(self.open, self.close)) / (self.high - self.low + 1e-12)
        
        # KLOW: (min(open, close) - low) / open
        self.factors['KLOW'] = (np.minimum(self.open, self.close) - self.low) / self.open
        
        # KLOW2: (min(open, close) - low) / (high - low + 1e-12)
        self.factors['KLOW2'] = (np.minimum(self.open, self.close) - self.low) / (self.high - self.low + 1e-12)
    
    def _price_factors(self):
        """价格因子"""
        # RSQR: 价格变化的 R^2
        for d in [5, 10, 20, 30, 60]:
            self.factors[f'RSQR_{d}'] = self._rolling_rsquare(self.close, d)
        
        # RESI: 残差
        for d in [5, 10, 20, 30, 60]:
            self.factors[f'RESI_{d}'] = self._rolling_residual(self.close, d)
        
        # CORR: 价格与成交量相关性
        for d in [5, 10, 20, 30, 60]:
            self.factors[f'CORR_{d}'] = self.close.rolling(d).corr(self.volume)
        
        # CORD: 价格变化与成交量变化相关性
        for d in [5, 10, 20, 30, 60]:
            price_chg = self.close.pct_change()
            vol_chg = self.volume.pct_change()
            self.factors[f'CORD_{d}'] = price_chg.rolling(d).corr(vol_chg)
    
    def _volume_factors(self):
        """成交量因子"""
        # VSTD: 成交量标准差
        for d in [5, 10, 20, 30, 60]:
            self.factors[f'VSTD_{d}'] = self.volume.rolling(d).std() / (self.volume.rolling(d).mean() + 1e-12)
        
        # VSUMP: 成交量正变化占比
        for d in [5, 10, 20, 30, 60]:
            vol_diff = self.volume.diff()
            pos_vol = vol_diff.where(vol_diff > 0, 0)
            self.factors[f'VSUMP_{d}'] = pos_vol.rolling(d).sum() / (self.volume.diff().abs().rolling(d).sum() + 1e-12)
        
        # VSUMN: 成交量负变化占比
        for d in [5, 10, 20, 30, 60]:
            vol_diff = self.volume.diff()
            neg_vol = (-vol_diff).where(vol_diff < 0, 0)
            self.factors[f'VSUMN_{d}'] = neg_vol.rolling(d).sum() / (self.volume.diff().abs().rolling(d).sum() + 1e-12)
        
        # VSUMD: 成交量变化差
        for d in [5, 10, 20, 30, 60]:
            self.factors[f'VSUMD_{d}'] = self.factors[f'VSUMP_{d}'] - self.factors[f'VSUMN_{d}']
    
    def _high_low_factors(self):
        """高低价因子"""
        # HIGH_0: (high - close) / close
        self.factors['HIGH_0'] = (self.high - self.close) / self.close
        
        # LOW_0: (low - close) / close
        self.factors['LOW_0'] = (self.low - self.close) / self.close
        
        for d in [5, 10, 20, 30, 60]:
            # HIGH_N: N日最高价位置
            self.factors[f'HIGH_{d}'] = (self.high.rolling(d).max() - self.close) / self.close
            
            # LOW_N: N日最低价位置
            self.factors[f'LOW_{d}'] = (self.close - self.low.rolling(d).min()) / self.close
            
            # HIGHDAY: 距离N日最高价的天数
            self.factors[f'HIGHDAY_{d}'] = self.high.rolling(d).apply(lambda x: d - 1 - x.argmax(), raw=True)
            
            # LOWDAY: 距离N日最低价的天数
            self.factors[f'LOWDAY_{d}'] = self.low.rolling(d).apply(lambda x: d - 1 - x.argmin(), raw=True)
    
    def _rolling_factors(self):
        """滚动统计因子"""
        for d in [5, 10, 20, 30, 60]:
            # MA: 移动平均
            ma = self.close.rolling(d).mean()
            self.factors[f'MA_{d}'] = ma / self.close - 1
            
            # STD: 标准差
            self.factors[f'STD_{d}'] = self.close.rolling(d).std() / self.close
            
            # BETA: Beta 系数
            self.factors[f'BETA_{d}'] = self._rolling_beta(self.close, d)
            
            # MAX: 最大值
            self.factors[f'MAX_{d}'] = self.close.rolling(d).max() / self.close - 1
            
            # MIN: 最小值
            self.factors[f'MIN_{d}'] = self.close.rolling(d).min() / self.close - 1
            
            # QTLU: 上四分位
            self.factors[f'QTLU_{d}'] = self.close.rolling(d).quantile(0.75) / self.close - 1
            
            # QTLD: 下四分位
            self.factors[f'QTLD_{d}'] = self.close.rolling(d).quantile(0.25) / self.close - 1
            
            # RANK: 当前价格在N日内的排名
            self.factors[f'RANK_{d}'] = self.close.rolling(d).apply(
                lambda x: pd.Series(x).rank().iloc[-1] / len(x), raw=False
            )
            
            # CNTP: 上涨天数占比
            ret = self.close.pct_change()
            self.factors[f'CNTP_{d}'] = (ret > 0).rolling(d).mean()
            
            # CNTN: 下跌天数占比
            self.factors[f'CNTN_{d}'] = (ret < 0).rolling(d).mean()
            
            # CNTD: 上涨减下跌天数占比
            self.factors[f'CNTD_{d}'] = self.factors[f'CNTP_{d}'] - self.factors[f'CNTN_{d}']
            
            # SUMP: 上涨幅度和
            pos_ret = ret.where(ret > 0, 0)
            self.factors[f'SUMP_{d}'] = pos_ret.rolling(d).sum()
            
            # SUMN: 下跌幅度和
            neg_ret = (-ret).where(ret < 0, 0)
            self.factors[f'SUMN_{d}'] = neg_ret.rolling(d).sum()
            
            # SUMD: 涨跌幅度差
            self.factors[f'SUMD_{d}'] = self.factors[f'SUMP_{d}'] - self.factors[f'SUMN_{d}']
    
    def _technical_factors(self):
        """技术指标因子"""
        close = self.close
        high = self.high
        low = self.low
        volume = self.volume
        
        # RSI
        for d in [6, 12, 24]:
            delta = close.diff()
            gain = delta.where(delta > 0, 0).rolling(d).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(d).mean()
            rs = gain / (loss + 1e-12)
            self.factors[f'RSI_{d}'] = 100 - 100 / (1 + rs)
        
        # ROC: 变化率
        for d in [5, 10, 20, 30, 60]:
            self.factors[f'ROC_{d}'] = close.pct_change(d)
        
        # MACD
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd = ema12 - ema26
        signal = macd.ewm(span=9, adjust=False).mean()
        self.factors['MACD'] = macd / close
        self.factors['MACD_SIGNAL'] = signal / close
        self.factors['MACD_HIST'] = (macd - signal) / close
        
        # KDJ
        for d in [9, 14, 19]:
            low_n = low.rolling(d).min()
            high_n = high.rolling(d).max()
            rsv = (close - low_n) / (high_n - low_n + 1e-12) * 100
            k = rsv.ewm(com=2, adjust=False).mean()
            d_val = k.ewm(com=2, adjust=False).mean()
            j = 3 * k - 2 * d_val
            self.factors[f'KDJ_K_{d}'] = k
            self.factors[f'KDJ_D_{d}'] = d_val
            self.factors[f'KDJ_J_{d}'] = j
        
        # BOLL: 布林带
        for d in [5, 10, 20]:
            ma = close.rolling(d).mean()
            std = close.rolling(d).std()
            self.factors[f'BOLL_UP_{d}'] = (ma + 2 * std) / close - 1
            self.factors[f'BOLL_DOWN_{d}'] = (ma - 2 * std) / close - 1
            self.factors[f'BOLL_WIDTH_{d}'] = 4 * std / ma
        
        # ATR: 平均真实波幅
        for d in [5, 10, 14, 20]:
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            self.factors[f'ATR_{d}'] = tr.rolling(d).mean() / close
        
        # OBV: 能量潮
        obv = (np.sign(close.diff()) * volume).cumsum()
        for d in [5, 10, 20]:
            obv_ma = obv.rolling(d).mean()
            self.factors[f'OBV_MA_{d}'] = (obv - obv_ma) / (obv.rolling(d).std() + 1e-12)
        
        # WILLR: 威廉指标
        for d in [6, 10, 14]:
            high_n = high.rolling(d).max()
            low_n = low.rolling(d).min()
            self.factors[f'WILLR_{d}'] = (high_n - close) / (high_n - low_n + 1e-12) * -100
        
        # CCI: 商品通道指数
        for d in [5, 10, 14, 20]:
            tp = (high + low + close) / 3
            ma_tp = tp.rolling(d).mean()
            md = (tp - ma_tp).abs().rolling(d).mean()
            self.factors[f'CCI_{d}'] = (tp - ma_tp) / (0.015 * md + 1e-12)
    
    def _return_factors(self):
        """收益因子"""
        ret = self.close.pct_change()
        
        for d in [1, 2, 3, 4, 5, 10, 20, 30, 60]:
            # 收益率
            self.factors[f'RETURN_{d}'] = self.close.pct_change(d)
        
        # 波动率调整收益
        for d in [5, 10, 20]:
            ret_d = self.close.pct_change(d)
            vol = ret.rolling(d).std()
            self.factors[f'SHARPE_{d}'] = ret_d / (vol * np.sqrt(d) + 1e-12)
    
    def _rolling_rsquare(self, series: pd.Series, window: int) -> pd.Series:
        """计算滚动 R^2"""
        def rsq(x):
            if len(x) < 2:
                return np.nan
            y = np.arange(len(x))
            corr = np.corrcoef(x, y)[0, 1]
            return corr ** 2 if not np.isnan(corr) else np.nan
        return series.rolling(window).apply(rsq, raw=True)
    
    def _rolling_residual(self, series: pd.Series, window: int) -> pd.Series:
        """计算滚动残差"""
        def resi(x):
            if len(x) < 2:
                return np.nan
            y = np.arange(len(x))
            slope = np.polyfit(y, x, 1)[0]
            pred = slope * (len(x) - 1) + x.mean() - slope * (len(x) - 1) / 2
            return (x[-1] - pred) / (x.std() + 1e-12)
        return series.rolling(window).apply(resi, raw=True)
    
    def _rolling_beta(self, series: pd.Series, window: int) -> pd.Series:
        """计算滚动 Beta"""
        ret = series.pct_change()
        mkt_ret = ret.rolling(window).mean()  # 用均值作为市场代理
        
        def beta(x):
            if len(x) < 2:
                return np.nan
            y = np.arange(len(x))
            return np.polyfit(y, x, 1)[0]
        
        return ret.rolling(window).apply(beta, raw=True)


def calculate_alpha158(data: pd.DataFrame) -> pd.DataFrame:
    """
    计算 Alpha158 因子的便捷函数
    
    Args:
        data: 包含 open, high, low, close, volume 的 DataFrame
    
    Returns:
        包含所有因子的 DataFrame
    """
    calculator = Alpha158(data)
    return calculator.calculate_all()
