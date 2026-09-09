"""
每日复盘自动化
生成市场复盘报告，包括：
- 大盘概况
- 板块热度
- 涨跌排行
- 异动股票
- 资金流向
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.fetcher import DataFetcher


class DailyReview:
    """
    每日复盘报告生成器
    """
    
    def __init__(self, date: str = None):
        """
        Args:
            date: 复盘日期，默认今天，格式 YYYYMMDD
        """
        self.date = date or datetime.now().strftime("%Y%m%d")
        self.data = {}
        
    def fetch_all_data(self):
        """获取所有需要的数据"""
        print(f"正在获取 {self.date} 的市场数据...")
        
        # 1. 获取实时行情（全市场）
        try:
            self.data["quotes"] = DataFetcher.get_realtime_quotes()
            print(f"  行情数据: {len(self.data['quotes'])} 只股票")
        except Exception as e:
            print(f"  行情数据获取失败: {e}")
            self.data["quotes"] = pd.DataFrame()
        
        # 2. 获取行业板块
        try:
            self.data["industry"] = DataFetcher.get_industry_board()
            print(f"  行业板块: {len(self.data['industry'])} 个")
        except Exception as e:
            print(f"  行业板块获取失败: {e}")
            self.data["industry"] = pd.DataFrame()
        
        # 3. 获取概念板块
        try:
            self.data["concept"] = DataFetcher.get_concept_board()
            print(f"  概念板块: {len(self.data['concept'])} 个")
        except Exception as e:
            print(f"  概念板块获取失败: {e}")
            self.data["concept"] = pd.DataFrame()
        
        # 4. 获取主要指数
        try:
            self.data["index"] = self._get_index_data()
            print(f"  指数数据: {len(self.data['index'])} 个")
        except Exception as e:
            print(f"  指数数据获取失败: {e}")
            self.data["index"] = {}
    
    def _get_index_data(self) -> Dict:
        """获取主要指数数据"""
        indices = {
            "000001": "上证指数",
            "399001": "深证成指",
            "399006": "创业板指",
            "000016": "上证50",
            "000300": "沪深300",
            "000905": "中证500"
        }
        
        result = {}
        for code, name in indices.items():
            try:
                df = DataFetcher.get_index_daily(code, 
                    (datetime.now() - timedelta(days=30)).strftime("%Y%m%d"))
                if len(df) > 0:
                    latest = df.iloc[-1]
                    prev = df.iloc[-2] if len(df) > 1 else latest
                    result[code] = {
                        "name": name,
                        "close": float(latest["close"]),
                        "change": float(latest["close"] - prev["close"]),
                        "pct_change": float((latest["close"] - prev["close"]) / prev["close"] * 100),
                        "volume": float(latest.get("volume", 0))
                    }
            except:
                pass
        
        return result
    
    def analyze_market(self) -> Dict:
        """分析大盘概况"""
        if self.data["quotes"].empty:
            return {}
        
        df = self.data["quotes"]
        
        # 过滤无效数据
        df = df[df["price"] > 0]
        
        # 涨跌统计
        up_count = len(df[df["pct_change"] > 0])
        down_count = len(df[df["pct_change"] < 0])
        flat_count = len(df[df["pct_change"] == 0])
        
        # 涨停跌停
        limit_up = len(df[df["pct_change"] >= 9.9])
        limit_down = len(df[df["pct_change"] <= -9.9])
        
        # 涨幅分布
        dist = {
            ">7%": len(df[df["pct_change"] > 7]),
            "5~7%": len(df[(df["pct_change"] > 5) & (df["pct_change"] <= 7)]),
            "3~5%": len(df[(df["pct_change"] > 3) & (df["pct_change"] <= 5)]),
            "0~3%": len(df[(df["pct_change"] > 0) & (df["pct_change"] <= 3)]),
            "0": flat_count,
            "-3~0%": len(df[(df["pct_change"] < 0) & (df["pct_change"] >= -3)]),
            "-5~-3%": len(df[(df["pct_change"] < -3) & (df["pct_change"] >= -5)]),
            "-7~-5%": len(df[(df["pct_change"] < -5) & (df["pct_change"] >= -7)]),
            "<-7%": len(df[df["pct_change"] < -7]),
        }
        
        return {
            "total_stocks": len(df),
            "up_count": up_count,
            "down_count": down_count,
            "flat_count": flat_count,
            "limit_up": limit_up,
            "limit_down": limit_down,
            "up_ratio": up_count / len(df) if len(df) > 0 else 0,
            "distribution": dist,
            "avg_pct_change": float(df["pct_change"].mean()),
            "median_pct_change": float(df["pct_change"].median())
        }
    
    def get_top_gainers(self, n: int = 20) -> pd.DataFrame:
        """涨幅榜"""
        if self.data["quotes"].empty:
            return pd.DataFrame()
        
        df = self.data["quotes"]
        df = df[df["price"] > 0]
        df = df[~df["name"].str.contains("ST|退市", na=False)]
        
        return df.nlargest(n, "pct_change")[["symbol", "name", "price", "pct_change", "volume", "amount"]]
    
    def get_top_losers(self, n: int = 20) -> pd.DataFrame:
        """跌幅榜"""
        if self.data["quotes"].empty:
            return pd.DataFrame()
        
        df = self.data["quotes"]
        df = df[df["price"] > 0]
        df = df[~df["name"].str.contains("ST|退市", na=False)]
        
        return df.nsmallest(n, "pct_change")[["symbol", "name", "price", "pct_change", "volume", "amount"]]
    
    def get_top_volume(self, n: int = 20) -> pd.DataFrame:
        """成交量榜"""
        if self.data["quotes"].empty:
            return pd.DataFrame()
        
        df = self.data["quotes"]
        df = df[df["price"] > 0]
        
        return df.nlargest(n, "amount")[["symbol", "name", "price", "pct_change", "volume", "amount", "turnover"]]
    
    def get_hot_industries(self, n: int = 10) -> pd.DataFrame:
        """热门行业"""
        if self.data["industry"].empty:
            return pd.DataFrame()
        
        df = self.data["industry"]
        if "pct_change" in df.columns:
            return df.nlargest(n, "pct_change")
        return df.head(n)
    
    def get_hot_concepts(self, n: int = 10) -> pd.DataFrame:
        """热门概念"""
        if self.data["concept"].empty:
            return pd.DataFrame()
        
        df = self.data["concept"]
        if "pct_change" in df.columns:
            return df.nlargest(n, "pct_change")
        return df.head(n)
    
    def find_unusual_stocks(self) -> Dict[str, pd.DataFrame]:
        """寻找异动股票"""
        if self.data["quotes"].empty:
            return {}
        
        df = self.data["quotes"]
        df = df[df["price"] > 0]
        df = df[~df["name"].str.contains("ST|退市", na=False)]
        
        result = {}
        
        # 1. 涨停股（非一字板）
        limit_up = df[df["pct_change"] >= 9.9]
        if len(limit_up) > 0:
            result["涨停股"] = limit_up[["symbol", "name", "price", "pct_change", "amount"]]
        
        # 2. 跌停股
        limit_down = df[df["pct_change"] <= -9.9]
        if len(limit_down) > 0:
            result["跌停股"] = limit_down[["symbol", "name", "price", "pct_change", "amount"]]
        
        # 3. 高换手率（>10%）
        if "turnover" in df.columns:
            high_turnover = df[df["turnover"] > 10]
            if len(high_turnover) > 0:
                result["高换手(>10%)"] = high_turnover.nlargest(20, "turnover")[
                    ["symbol", "name", "price", "pct_change", "turnover", "amount"]]
        
        # 4. 大幅放量（量比>3）
        if "volume_ratio" in df.columns:
            high_vol_ratio = df[df["volume_ratio"] > 3]
            if len(high_vol_ratio) > 0:
                result["大幅放量(量比>3)"] = high_vol_ratio.nlargest(20, "volume_ratio")[
                    ["symbol", "name", "price", "pct_change", "volume_ratio", "amount"]]
        
        return result
    
    def generate_report(self) -> str:
        """生成文字报告"""
        self.fetch_all_data()
        
        market = self.analyze_market()
        
        lines = []
        lines.append("=" * 60)
        lines.append(f"A股市场日报 - {self.date}")
        lines.append("=" * 60)
        
        # 指数行情
        lines.append("\n【主要指数】")
        lines.append("-" * 60)
        for code, info in self.data.get("index", {}).items():
            arrow = "↑" if info["pct_change"] > 0 else ("↓" if info["pct_change"] < 0 else "→")
            lines.append(f"  {info['name']:<10} {info['close']:>10.2f}  {arrow} {info['pct_change']:+.2f}%")
        
        # 大盘概况
        if market:
            lines.append("\n【大盘概况】")
            lines.append("-" * 60)
            lines.append(f"  上涨: {market['up_count']}  下跌: {market['down_count']}  平盘: {market['flat_count']}")
            lines.append(f"  涨停: {market['limit_up']}  跌停: {market['limit_down']}")
            lines.append(f"  涨跌比: {market['up_ratio']:.1%}")
            lines.append(f"  平均涨幅: {market['avg_pct_change']:.2f}%")
            
            lines.append("\n  涨跌分布:")
            for k, v in market["distribution"].items():
                bar = "█" * int(v / max(market["distribution"].values()) * 20) if max(market["distribution"].values()) > 0 else ""
                lines.append(f"    {k:>8}: {v:>5} {bar}")
        
        # 涨幅榜
        top_gainers = self.get_top_gainers(10)
        if not top_gainers.empty:
            lines.append("\n【涨幅榜TOP10】")
            lines.append("-" * 60)
            for _, row in top_gainers.iterrows():
                lines.append(f"  {row['symbol']} {row['name']:<8} {row['price']:>8.2f}  {row['pct_change']:+.2f}%")
        
        # 跌幅榜
        top_losers = self.get_top_losers(10)
        if not top_losers.empty:
            lines.append("\n【跌幅榜TOP10】")
            lines.append("-" * 60)
            for _, row in top_losers.iterrows():
                lines.append(f"  {row['symbol']} {row['name']:<8} {row['price']:>8.2f}  {row['pct_change']:+.2f}%")
        
        # 热门行业
        hot_ind = self.get_hot_industries(5)
        if not hot_ind.empty:
            lines.append("\n【热门行业TOP5】")
            lines.append("-" * 60)
            for _, row in hot_ind.iterrows():
                name = row.get("name", row.get("板块名称", ""))
                pct = row.get("pct_change", row.get("涨跌幅", 0))
                lines.append(f"  {name:<15} {pct:+.2f}%")
        
        # 热门概念
        hot_con = self.get_hot_concepts(5)
        if not hot_con.empty:
            lines.append("\n【热门概念TOP5】")
            lines.append("-" * 60)
            for _, row in hot_con.iterrows():
                name = row.get("name", row.get("板块名称", ""))
                pct = row.get("pct_change", row.get("涨跌幅", 0))
                lines.append(f"  {name:<15} {pct:+.2f}%")
        
        # 异动股
        unusual = self.find_unusual_stocks()
        if unusual:
            lines.append("\n【异动股票】")
            for category, df in unusual.items():
                if len(df) > 0:
                    lines.append(f"\n  {category}:")
                    for _, row in df.head(5).iterrows():
                        lines.append(f"    {row['symbol']} {row['name']:<8} {row['pct_change']:+.2f}%")
        
        lines.append("\n" + "=" * 60)
        lines.append(f"报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return "\n".join(lines)
    
    def generate_html_report(self, output_path: str = None) -> str:
        """生成HTML报告"""
        self.fetch_all_data()
        market = self.analyze_market()
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>A股日报 - {self.date}</title>
    <style>
        body {{ font-family: 'Microsoft YaHei', Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; text-align: center; border-bottom: 2px solid #e74c3c; padding-bottom: 15px; }}
        h2 {{ color: #e74c3c; margin-top: 30px; }}
        .index-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin: 20px 0; }}
        .index-card {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px; border-radius: 8px; text-align: center; }}
        .index-card.up {{ background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%); }}
        .index-card.down {{ background: linear-gradient(135deg, #27ae60 0%, #1e8449 100%); }}
        .index-name {{ font-size: 14px; opacity: 0.9; }}
        .index-value {{ font-size: 24px; font-weight: bold; margin: 5px 0; }}
        .index-change {{ font-size: 16px; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin: 20px 0; }}
        .stat-card {{ background: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center; }}
        .stat-value {{ font-size: 28px; font-weight: bold; color: #333; }}
        .stat-label {{ color: #666; margin-top: 5px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
        th {{ background: #e74c3c; color: white; padding: 10px; text-align: left; }}
        td {{ padding: 8px 10px; border-bottom: 1px solid #eee; }}
        tr:hover {{ background: #f5f5f5; }}
        .up {{ color: #e74c3c; }}
        .down {{ color: #27ae60; }}
        .section {{ margin: 30px 0; }}
        .footer {{ text-align: center; color: #999; margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; }}
    </style>
</head>
<body>
<div class="container">
    <h1>📈 A股市场日报</h1>
    <p style="text-align:center;color:#666;">{self.date}</p>
"""
        
        # 指数行情
        if self.data.get("index"):
            html += '<h2>主要指数</h2><div class="index-grid">'
            for code, info in self.data["index"].items():
                css_class = "up" if info["pct_change"] > 0 else ("down" if info["pct_change"] < 0 else "")
                arrow = "↑" if info["pct_change"] > 0 else ("↓" if info["pct_change"] < 0 else "→")
                html += f'''
                <div class="index-card {css_class}">
                    <div class="index-name">{info["name"]}</div>
                    <div class="index-value">{info["close"]:.2f}</div>
                    <div class="index-change">{arrow} {info["pct_change"]:+.2f}%</div>
                </div>'''
            html += '</div>'
        
        # 大盘概况
        if market:
            html += f'''
            <h2>大盘概况</h2>
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-value up">{market["up_count"]}</div>
                    <div class="stat-label">上涨</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value down">{market["down_count"]}</div>
                    <div class="stat-label">下跌</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value up">{market["limit_up"]}</div>
                    <div class="stat-label">涨停</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value down">{market["limit_down"]}</div>
                    <div class="stat-label">跌停</div>
                </div>
            </div>
            '''
        
        # 涨幅榜
        top_gainers = self.get_top_gainers(15)
        if not top_gainers.empty:
            html += '<div class="section"><h2>🔥 涨幅榜</h2><table>'
            html += '<tr><th>代码</th><th>名称</th><th>现价</th><th>涨跌幅</th><th>成交额(万)</th></tr>'
            for _, row in top_gainers.iterrows():
                pct_class = "up" if row["pct_change"] > 0 else "down"
                amount = row.get("amount", 0) / 10000
                html += f'''<tr>
                    <td>{row["symbol"]}</td>
                    <td>{row["name"]}</td>
                    <td>{row["price"]:.2f}</td>
                    <td class="{pct_class}">{row["pct_change"]:+.2f}%</td>
                    <td>{amount:,.0f}</td>
                </tr>'''
            html += '</table></div>'
        
        # 跌幅榜
        top_losers = self.get_top_losers(15)
        if not top_losers.empty:
            html += '<div class="section"><h2>📉 跌幅榜</h2><table>'
            html += '<tr><th>代码</th><th>名称</th><th>现价</th><th>涨跌幅</th><th>成交额(万)</th></tr>'
            for _, row in top_losers.iterrows():
                pct_class = "up" if row["pct_change"] > 0 else "down"
                amount = row.get("amount", 0) / 10000
                html += f'''<tr>
                    <td>{row["symbol"]}</td>
                    <td>{row["name"]}</td>
                    <td>{row["price"]:.2f}</td>
                    <td class="{pct_class}">{row["pct_change"]:+.2f}%</td>
                    <td>{amount:,.0f}</td>
                </tr>'''
            html += '</table></div>'
        
        html += f'''
    <div class="footer">
        报告生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}<br>
        数据来源: AKShare
    </div>
</div>
</body>
</html>
'''
        
        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html)
            print(f"HTML报告已保存: {output_path}")
        
        return html
    
    def save_report(self, output_dir: str = None):
        """保存报告（文本+HTML）"""
        if output_dir is None:
            output_dir = os.path.dirname(__file__)
        
        os.makedirs(output_dir, exist_ok=True)
        
        # 文本报告
        text_path = os.path.join(output_dir, f"daily_review_{self.date}.txt")
        with open(text_path, "w", encoding="utf-8") as f:
            f.write(self.generate_report())
        print(f"文本报告已保存: {text_path}")
        
        # HTML报告
        html_path = os.path.join(output_dir, f"daily_review_{self.date}.html")
        self.generate_html_report(html_path)


def run_daily_review(date: str = None, output_dir: str = None):
    """运行每日复盘"""
    review = DailyReview(date)
    
    # 打印文本报告
    print(review.generate_report())
    
    # 保存报告
    if output_dir:
        review.save_report(output_dir)
    
    return review
