# coding = utf-8
"""
且慢平台数据抓取主程序
"""

from qieman.craw_assert import QiemanCraw

if __name__ == '__main__':
    craw = QiemanCraw()
    craw.fetch_profit_history()
