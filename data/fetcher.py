"""
数据获取模块 - 封装 AKShare 接口
优化：增加请求间隔、统一重试机制、连接池管理
"""
import os
import ssl
import urllib3
import time
import random
from functools import wraps

# 禁用 SSL 警告（公司网络代理环境）
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 全局禁用 SSL 验证（解决公司网络证书问题）
os.environ['CURL_CA_BUNDLE'] = ''
os.environ['REQUESTS_CA_BUNDLE'] = ''

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 全局请求间隔控制
_last_request_time = 0
_min_request_interval = 1.0  # 最小请求间隔（秒），默认1秒更稳定


def set_request_interval(interval: float):
    """
    设置请求间隔（秒）
    
    - 网络好：0.3~0.5
    - 网络一般：1.0（默认）
    - 网络差：1.5~2.0
    """
    global _min_request_interval
    _min_request_interval = interval
    print(f"请求间隔已设置为 {interval} 秒")


def _rate_limit():
    """请求频率限制"""
    global _last_request_time
    now = time.time()
    elapsed = now - _last_request_time
    if elapsed < _min_request_interval:
        time.sleep(_min_request_interval - elapsed + random.uniform(0.1, 0.3))
    _last_request_time = time.time()


def retry_on_failure(max_retries=5, base_delay=2, silent=False):
    """通用重试装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries):
                try:
                    _rate_limit()  # 请求前限速
                    return func(*args, **kwargs)
                except (ConnectionError, TimeoutError) as e:
                    # 网络错误，多等一会
                    last_error = e
                    if attempt < max_retries - 1:
                        wait_time = base_delay * (attempt + 1) * 1.5 + random.uniform(0.5, 2)
                        if not silent:
                            print(f"  网络错误，{wait_time:.1f}秒后重试 ({attempt + 1}/{max_retries})...")
                        time.sleep(wait_time)
                except Exception as e:
                    # 其他错误
                    error_str = str(e).lower()
                    # 判断是否是网络相关错误
                    if any(x in error_str for x in ['connection', 'timeout', 'refused', 'reset', 'disconnected']):
                        last_error = e
                        if attempt < max_retries - 1:
                            wait_time = base_delay * (attempt + 1) + random.uniform(0.5, 1.5)
                            if not silent:
                                print(f"  连接异常，{wait_time:.1f}秒后重试 ({attempt + 1}/{max_retries})...")
                            time.sleep(wait_time)
                    else:
                        # 非网络错误直接抛出
                        raise e
            raise last_error
        return wrapper
    return decorator


# 创建全局 Session（连接池复用）
def create_session():
    session = requests.Session()
    session.verify = False
    
    # 配置重试策略
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"]
    )
    adapter = HTTPAdapter(
        max_retries=retry_strategy,
        pool_connections=10,
        pool_maxsize=20
    )
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session

_global_session = create_session()


# Patch requests 的默认行为
_original_request = requests.Session.request
def _patched_request(self, *args, **kwargs):
    kwargs['verify'] = False
    kwargs.setdefault('timeout', (10, 30))  # (连接超时, 读取超时)
    return _original_request(self, *args, **kwargs)
requests.Session.request = _patched_request


import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List


class DataFetcher:
    """A股数据获取器"""
    
    @staticmethod
    @retry_on_failure(max_retries=8, base_delay=3)
    def get_stock_daily(symbol: str, start_date: str, end_date: str = None,
                        adjust: str = "qfq", max_retries: int = 5) -> pd.DataFrame:
        """
        获取股票日K线数据
        
        Args:
            symbol: 股票代码，如 "000001"
            start_date: 开始日期，如 "20230101"
            end_date: 结束日期，默认今天
            adjust: 复权类型 - qfq(前复权), hfq(后复权), 空字符串(不复权)
            max_retries: 最大重试次数（已被装饰器处理，保留参数兼容性）
        
        Returns:
            DataFrame: 包含 date, open, high, low, close, volume, amount 等列
        """
        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")
        
        df = ak.stock_zh_a_hist(
            symbol=symbol,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust=adjust
        )
        
        # 统一列名
        df = df.rename(columns={
            "日期": "date",
            "开盘": "open",
            "收盘": "close",
            "最高": "high",
            "最低": "low",
            "成交量": "volume",
            "成交额": "amount",
            "振幅": "amplitude",
            "涨跌幅": "pct_change",
            "涨跌额": "change",
            "换手率": "turnover"
        })
        
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date").sort_index()
        
        return df
    
    @staticmethod
    @retry_on_failure(max_retries=3, base_delay=1)
    def get_stock_minute(symbol: str, period: str = "5") -> pd.DataFrame:
        """
        获取股票分钟K线数据（最近几个交易日）
        
        Args:
            symbol: 股票代码
            period: 周期 - 1/5/15/30/60 分钟
        
        Returns:
            DataFrame: 分钟级K线数据
        """
        df = ak.stock_zh_a_hist_min_em(symbol=symbol, period=period)
        
        df = df.rename(columns={
            "时间": "datetime",
            "开盘": "open",
            "收盘": "close",
            "最高": "high",
            "最低": "low",
            "成交量": "volume",
            "成交额": "amount"
        })
        
        df["datetime"] = pd.to_datetime(df["datetime"])
        df = df.set_index("datetime").sort_index()
        
        return df
    
    @staticmethod
    @retry_on_failure(max_retries=8, base_delay=5)
    def get_realtime_quotes() -> pd.DataFrame:
        """
        获取全市场实时行情
        
        Returns:
            DataFrame: 全市场股票实时数据
        """
        df = ak.stock_zh_a_spot_em()
        
        df = df.rename(columns={
            "代码": "symbol",
            "名称": "name",
            "最新价": "price",
            "涨跌幅": "pct_change",
            "涨跌额": "change",
            "成交量": "volume",
            "成交额": "amount",
            "振幅": "amplitude",
            "最高": "high",
            "最低": "low",
            "今开": "open",
            "昨收": "pre_close",
            "换手率": "turnover",
            "市盈率-动态": "pe",
            "市净率": "pb"
        })
        
        return df
    
    @staticmethod
    @retry_on_failure(max_retries=3, base_delay=2)
    def get_stock_info(symbol: str) -> dict:
        """
        获取股票基本信息
        
        Args:
            symbol: 股票代码
        
        Returns:
            dict: 股票基本信息
        """
        df = ak.stock_individual_info_em(symbol=symbol)
        info = dict(zip(df["item"], df["value"]))
        return info
    
    @staticmethod
    @retry_on_failure(max_retries=5, base_delay=2)
    def get_index_daily(symbol: str, start_date: str, end_date: str = None) -> pd.DataFrame:
        """
        获取指数日K线
        
        Args:
            symbol: 指数代码，如 "000001"(上证指数), "399001"(深证成指), "399006"(创业板指)
            start_date: 开始日期
            end_date: 结束日期
        
        Returns:
            DataFrame: 指数日K线数据
        """
        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")
        
        # 判断交易所
        if symbol.startswith("0") or symbol.startswith("5"):
            index_code = f"sh{symbol}"
        else:
            index_code = f"sz{symbol}"
        
        df = ak.stock_zh_index_daily_em(symbol=index_code)
        
        df = df.rename(columns={
            "date": "date",
            "open": "open",
            "close": "close",
            "high": "high",
            "low": "low",
            "volume": "volume"
        })
        
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date").sort_index()
        df = df[start_date:end_date]
        
        return df
    
    @staticmethod
    @retry_on_failure(max_retries=3, base_delay=2)
    def get_stock_list() -> pd.DataFrame:
        """
        获取全部A股股票列表
        
        Returns:
            DataFrame: 股票代码和名称
        """
        df = ak.stock_info_a_code_name()
        df = df.rename(columns={"code": "symbol", "name": "name"})
        return df
    
    @staticmethod
    @retry_on_failure(max_retries=5, base_delay=3)
    def get_industry_board() -> pd.DataFrame:
        """
        获取行业板块列表
        
        Returns:
            DataFrame: 行业板块数据
        """
        df = ak.stock_board_industry_name_em()
        return df
    
    @staticmethod
    @retry_on_failure(max_retries=5, base_delay=3)
    def get_concept_board() -> pd.DataFrame:
        """
        获取概念板块列表
        
        Returns:
            DataFrame: 概念板块数据
        """
        df = ak.stock_board_concept_name_em()
        return df
    
    @staticmethod
    def get_multiple_stocks(symbols: List[str], start_date: str, end_date: str = None,
                           show_progress: bool = True) -> dict:
        """
        批量获取多只股票数据（带进度显示和智能间隔）
        
        Args:
            symbols: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            show_progress: 是否显示进度
        
        Returns:
            dict: {symbol: DataFrame}
        """
        result = {}
        failed = []
        
        for i, symbol in enumerate(symbols):
            if show_progress:
                print(f"  获取 {symbol} ({i+1}/{len(symbols)})...", end="")
            
            try:
                df = DataFetcher.get_stock_daily(symbol, start_date, end_date)
                result[symbol] = df
                if show_progress:
                    print(f" {len(df)} 条")
            except Exception as e:
                failed.append(symbol)
                if show_progress:
                    print(f" 失败: {e}")
            
            # 每5只股票休息一下
            if (i + 1) % 5 == 0:
                time.sleep(1)
        
        if failed:
            print(f"  失败列表: {failed}")
        
        return result


# 便捷函数
def get_daily(symbol: str, start_date: str, end_date: str = None) -> pd.DataFrame:
    """快捷获取日K线"""
    return DataFetcher.get_stock_daily(symbol, start_date, end_date)


def get_realtime() -> pd.DataFrame:
    """快捷获取实时行情"""
    return DataFetcher.get_realtime_quotes()
