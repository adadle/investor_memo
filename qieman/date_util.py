# coding = utf-8
"""
日期工具类
"""

__author__ = 'Eric Lee'

import time


def ts_to_date_str(ts):
    """
    时间戳转日期格式
    :param ts:
    :return:
    """
    return time.strftime('%Y-%m-%d', time.localtime(ts))
