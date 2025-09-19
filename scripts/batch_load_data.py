# coding = utf-8
"""
离线更新excel填充数据
"""

__author__ = 'Eric Lee'

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))

from qieman.craw_assert import QiemanCraw

if __name__ == '__main__':
    m = QiemanCraw()
    print(m.get_latest_sign())