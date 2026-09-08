# 策略模块
from .base import BaseStrategy

# 基础策略
from .ma_cross import MACrossStrategy, TripleMAStrategy
from .momentum import MomentumStrategy, RSIMomentumStrategy
from .breakout import BreakoutStrategy, BollingerBreakoutStrategy, VolumeBreakoutStrategy
from .macd import MACDStrategy, MACDDivergenceStrategy
from .kdj import KDJStrategy, KDJGoldenStrategy
from .grid import GridStrategy, DynamicGridStrategy, MeanReversionStrategy

# 高级策略 - 因子策略
from .factor import MultiFactorStrategy, ValueMomentumStrategy, QualityMomentumStrategy

# 高级策略 - 趋势跟踪
from .trend import TrendFollowingStrategy, DualThrustStrategy, AdaptiveTrendStrategy

# 高级策略 - 止损策略
from .stop_loss import TrailingStopStrategy, FixedRatioStopStrategy, ATRStopStrategy, TimeStopStrategy

# 高级策略 - 量价策略
from .volume import VolumeBreakthroughStrategy, OBVStrategy, VolumeProfileStrategy, ShrinkingVolumeStrategy

# 高级策略 - 形态识别
from .pattern import CandlePatternStrategy, DoubleBottomStrategy, BreakoutRetestStrategy

# 高级策略 - 组合策略
from .composite import CompositeStrategy, ConfirmationStrategy, FilteredStrategy, RotationStrategy

__all__ = [
    # 基类
    'BaseStrategy',
    
    # 均线策略
    'MACrossStrategy', 'TripleMAStrategy',
    
    # 动量策略
    'MomentumStrategy', 'RSIMomentumStrategy',
    
    # 突破策略
    'BreakoutStrategy', 'BollingerBreakoutStrategy', 'VolumeBreakoutStrategy',
    
    # MACD策略
    'MACDStrategy', 'MACDDivergenceStrategy',
    
    # KDJ策略
    'KDJStrategy', 'KDJGoldenStrategy',
    
    # 网格策略
    'GridStrategy', 'DynamicGridStrategy', 'MeanReversionStrategy',
    
    # 因子策略
    'MultiFactorStrategy', 'ValueMomentumStrategy', 'QualityMomentumStrategy',
    
    # 趋势策略
    'TrendFollowingStrategy', 'DualThrustStrategy', 'AdaptiveTrendStrategy',
    
    # 止损策略
    'TrailingStopStrategy', 'FixedRatioStopStrategy', 'ATRStopStrategy', 'TimeStopStrategy',
    
    # 量价策略
    'VolumeBreakthroughStrategy', 'OBVStrategy', 'VolumeProfileStrategy', 'ShrinkingVolumeStrategy',
    
    # 形态策略
    'CandlePatternStrategy', 'DoubleBottomStrategy', 'BreakoutRetestStrategy',
    
    # 组合策略
    'CompositeStrategy', 'ConfirmationStrategy', 'FilteredStrategy', 'RotationStrategy',
]
