# coding = utf-8
"""
"""

import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))

if __name__ == '__main__':
    print(os.path.dirname(__file__))
    from configuration import conf

    print(conf.get('qieman', 'login_user'))

