"""
测试数据获取
"""
import os
import ssl
import urllib3

# 禁用 SSL 验证（公司网络环境）
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
os.environ['CURL_CA_BUNDLE'] = ''
os.environ['REQUESTS_CA_BUNDLE'] = ''

# Patch requests
import requests
_original_request = requests.Session.request
def _patched_request(self, *args, **kwargs):
    kwargs['verify'] = False
    return _original_request(self, *args, **kwargs)
requests.Session.request = _patched_request

# 现在导入 akshare
import akshare as ak

print("=" * 50)
print("测试 AKShare 数据获取")
print("=" * 50)

try:
    print("\n1. 获取平安银行日K线...")
    df = ak.stock_zh_a_hist(symbol="000001", period="daily", start_date="20240901", end_date="20240910")
    print(df)
    print("\n✓ 日K线获取成功!")
except Exception as e:
    print(f"✗ 日K线获取失败: {e}")

try:
    print("\n2. 获取实时行情（前5只）...")
    df = ak.stock_zh_a_spot_em()
    print(df[["代码", "名称", "最新价", "涨跌幅"]].head(5))
    print("\n✓ 实时行情获取成功!")
except Exception as e:
    print(f"✗ 实时行情获取失败: {e}")

print("\n" + "=" * 50)
print("测试完成")
print("=" * 50)
