"""
数据获取模块 - 封装 AKShare 接口
"""
import os
import ssl
import urllib3
import time

# 禁用 SSL 警告（公司网络代理环境）
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 全局禁用 SSL 验证（解决公司网络证书问题）
os.environ['CURL_CA_BUNDLE'] = ''
os.environ['REQUESTS_CA_BUNDLE'] = ''

# Monkey patch requests 跳过 SSL 验证 + 增加超时
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 创建带重试的 Session
def create_session():
    session = requests.Session()
    session.verify = False
    
    # 配置重试策略
    retry_strategy = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session

# Patch requests 的默认行为
_original_request = requests.Session.request
def _patched_request(self, *args, **kwargs):
    kwargs['verify'] = False
    kwargs.setdefault('timeout', 30)  # 默认30秒超时
    return _original_request(self, *args, **kwargs)
requests.Session.request = _patched_request

import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List


class DataFetcher:
    """A股数据获取器"""
    
    @staticmethod
    def get_stock_daily(symbol: str, start_date: str, end_date: str = None,
                        adjust: str = "qfq", max_retries: int = 5) -> pd.DataFrame:
        """
        获取股票日K线数据
        
        Args:
            symbol: 股票代码，如 "000001"
            start_date: 开始日期，如 "20230101"
            end_date: 结束日期，默认今天
            adjust: 复权类型 - qfq(前复权), hfq(后复权), 空字符串(不复权)
            max_retries: 最大重试次数
        
        Returns:
            DataFrame: 包含 date, open, high, low, close, volume, amount 等列
        """
        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")
        
        last_error = None
        for attempt in range(max_retries):
            try:
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
                
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2
                    print(f"  获取失败，{wait_time}秒后重试 ({attempt + 1}/{max_retries})...")
                    time.sleep(wait_time)
        
        raise last_error
    
    @staticmethod
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
        
        df = ak.stock_zh_index_daily_em(symbol=f"sh{symbol}" if symbol.startswith("0") else f"sz{symbol}")
        
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
    def get_industry_board() -> pd.DataFrame:
        """
        获取行业板块列表
        
        Returns:
            DataFrame: 行业板块数据
        """
        df = ak.stock_board_industry_name_em()
        return df
    
    @staticmethod
    def get_concept_board() -> pd.DataFrame:
        """
        获取概念板块列表
        
        Returns:
            DataFrame: 概念板块数据
        """
        df = ak.stock_board_concept_name_em()
        return df


# 便捷函数
def get_daily(symbol: str, start_date: str, end_date: str = None) -> pd.DataFrame:
    """快捷获取日K线"""
    return DataFetcher.get_stock_daily(symbol, start_date, end_date)


def get_realtime() -> pd.DataFrame:
    """快捷获取实时行情"""
    return DataFetcher.get_realtime_quotes()
