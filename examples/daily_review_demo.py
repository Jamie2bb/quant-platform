"""
每日复盘示例
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from report.daily_review import DailyReview, run_daily_review


def main():
    print("=" * 60)
    print("每日复盘示例")
    print("=" * 60)
    
    # 方式1: 快速生成今日复盘
    print("\n正在生成市场复盘报告...")
    
    review = DailyReview()
    
    # 生成文本报告
    report = review.generate_report()
    print(report)
    
    # 生成 HTML 报告
    html_path = os.path.join(os.path.dirname(__file__), "daily_review.html")
    review.generate_html_report(html_path)
    
    print("\n" + "=" * 60)
    print(f"HTML报告已生成: {html_path}")
    print("用浏览器打开可查看可视化报告")
    print("=" * 60)


if __name__ == "__main__":
    main()
