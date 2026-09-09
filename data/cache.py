"""
数据缓存模块
减少重复网络请求，提高速度
"""
import os
import json
import pickle
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Any
import pandas as pd


class DataCache:
    """
    本地数据缓存
    
    - 日K线数据缓存1天
    - 实时行情缓存5分钟
    - 板块数据缓存1小时
    """
    
    def __init__(self, cache_dir: str = None):
        if cache_dir is None:
            cache_dir = os.path.join(os.path.dirname(__file__), ".cache")
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
    
    def _get_cache_path(self, key: str) -> str:
        """生成缓存文件路径"""
        hash_key = hashlib.md5(key.encode()).hexdigest()[:16]
        return os.path.join(self.cache_dir, f"{hash_key}.pkl")
    
    def get(self, key: str, max_age_seconds: int = 3600) -> Optional[Any]:
        """
        获取缓存
        
        Args:
            key: 缓存键
            max_age_seconds: 最大缓存时间（秒）
        
        Returns:
            缓存的数据，过期或不存在返回 None
        """
        path = self._get_cache_path(key)
        
        if not os.path.exists(path):
            return None
        
        try:
            mtime = os.path.getmtime(path)
            age = datetime.now().timestamp() - mtime
            
            if age > max_age_seconds:
                os.remove(path)
                return None
            
            with open(path, "rb") as f:
                return pickle.load(f)
        except:
            return None
    
    def set(self, key: str, data: Any):
        """保存缓存"""
        path = self._get_cache_path(key)
        try:
            with open(path, "wb") as f:
                pickle.dump(data, f)
        except:
            pass
    
    def clear(self):
        """清空所有缓存"""
        for f in os.listdir(self.cache_dir):
            path = os.path.join(self.cache_dir, f)
            if f.endswith(".pkl"):
                try:
                    os.remove(path)
                except:
                    pass
        print("缓存已清空")
    
    def get_stats(self) -> dict:
        """获取缓存统计"""
        files = [f for f in os.listdir(self.cache_dir) if f.endswith(".pkl")]
        total_size = sum(os.path.getsize(os.path.join(self.cache_dir, f)) for f in files)
        
        return {
            "cache_dir": self.cache_dir,
            "file_count": len(files),
            "total_size_mb": total_size / 1024 / 1024
        }


# 全局缓存实例
_cache = DataCache()


def cached_daily(symbol: str, start_date: str, end_date: str = None):
    """缓存版日K线获取"""
    from .fetcher import DataFetcher
    
    if end_date is None:
        end_date = datetime.now().strftime("%Y%m%d")
    
    key = f"daily_{symbol}_{start_date}_{end_date}"
    
    # 缓存24小时
    data = _cache.get(key, max_age_seconds=86400)
    if data is not None:
        return data
    
    data = DataFetcher.get_stock_daily(symbol, start_date, end_date)
    _cache.set(key, data)
    return data


def cached_realtime():
    """缓存版实时行情（5分钟缓存）"""
    from .fetcher import DataFetcher
    
    key = f"realtime_{datetime.now().strftime('%Y%m%d')}"
    
    # 缓存5分钟
    data = _cache.get(key, max_age_seconds=300)
    if data is not None:
        return data
    
    data = DataFetcher.get_realtime_quotes()
    _cache.set(key, data)
    return data


def cached_industry():
    """缓存版行业板块（1小时缓存）"""
    from .fetcher import DataFetcher
    
    key = f"industry_{datetime.now().strftime('%Y%m%d')}"
    
    data = _cache.get(key, max_age_seconds=3600)
    if data is not None:
        return data
    
    data = DataFetcher.get_industry_board()
    _cache.set(key, data)
    return data


def cached_concept():
    """缓存版概念板块（1小时缓存）"""
    from .fetcher import DataFetcher
    
    key = f"concept_{datetime.now().strftime('%Y%m%d')}"
    
    data = _cache.get(key, max_age_seconds=3600)
    if data is not None:
        return data
    
    data = DataFetcher.get_concept_board()
    _cache.set(key, data)
    return data


def clear_cache():
    """清空缓存"""
    _cache.clear()


def cache_stats():
    """缓存统计"""
    return _cache.get_stats()
