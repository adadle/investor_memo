# coding = utf-8
"""
"""
import requests
import logging
from selenium import webdriver
import json
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from qieman.configuration import conf
from qieman.model.daily_profit import DailyProfit
from qieman.date_util import ts_to_date_str

logging.basicConfig(level=logging.INFO)


class QiemanCraw(object):
    # 模拟chrome浏览器登录的设置
    caps = {
        'browserName': 'chrome',
        'loggingPrefs': {
            'performance': 'ALL',
        },
        'goog:chromeOptions': {
            'w3c': False,
        },
    }

    # 需要切换成自己设备cookie, 不包含access_token
    # 完整的token需要append上: access_token=${token}
    cookie_with_no_token = '_a=A.BEEC6D501F7QEPMMSJY401KJM4GBS0JWV; _ga=GA1.2.361126683.1623211071; sensorsdata2015jssdkcross={"distinct_id":"1434871","first_id":"179eeeb553ac1f-0a0ca0e27ab0f4-37667200-1024000-179eeeb553ba7f","props":{"$latest_traffic_source_type":"直接流量","$latest_search_keyword":"未取到值_直接打开","$latest_referrer":""},"$device_id":"179eeeb553ac1f-0a0ca0e27ab0f4-37667200-1024000-179eeeb553ba7f"}; '

    # UA
    user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'

    CHANNEL = 'qieman'

    engine = create_engine(conf.get('backend', 'mysql_conn_url'))
    Session = sessionmaker(bind=engine)
    session = Session()

    def __init__(self):
        self.x_sign = self._get_sign()
        if not self.x_sign:
            raise Exception("sign is needed, but we got none")

    def fetch_profit_history(self):
        """
        fetch profit history in the past month
        :return:
        """
        headers = self.build_headers()
        profit_url = conf.get('qieman', 'url_profit')
        r = requests.get(profit_url, headers=headers)
        if not r.text:
            logging.error("get url_profit: {}, but got no data {}".format(profit_url, r.text))
        profit_list = r.json().get('dailyProfitList')

        for record in profit_list:
            date_utc_ms = record.get('navDate')
            is_tx_date = record.get('isTxnDate')
            profit = record.get('dailyProfit')

            profit = 0 if not is_tx_date else profit
            item = DailyProfit(data_date=ts_to_date_str(int(date_utc_ms / 1000)),
                               channel=self.CHANNEL, is_tx_date=is_tx_date, profit=profit)
            item.save(self.session)

    def build_headers(self):
        """

        :rtype: object
        """
        access_token = self._get_access_token()
        cookie = self.cookie_with_no_token + ' access_token={}'.format(access_token)
        headers = {
            'Cookie': cookie.encode('utf-8'),
            'User-Agent': self.user_agent,
            'x-sign': self.get_latest_sign()
        }
        return headers

    def _get_access_token(self):
        """
        mock login and get access token from response.
        :return:
        """
        headers = {
            'Referer': 'https://qieman.com/user/signup',
            'Content-Type': 'application/json;charset=UTF-8',
            'User-Agent': self.user_agent,
            'x-sign': self.get_latest_sign()
        }
        url_login = conf.get('qieman', 'url_login')
        post_data = {
            'user': conf.get('qieman', 'login_user'),
            'password': conf.get('qieman', 'login_password'),
        }
        r = requests.post(url_login, data=json.dumps(post_data), headers=headers)
        if not r:
            raise Exception("get access_token error with no data. url {}, headers {}, payload {}".format(
                url_login, headers, post_data))
        return r.json().get('accessToken')

    def get_latest_sign(self):
        """
        check by timestamp from sign, if expired update it.
        :return:
        """
        now = datetime.now()
        daystart = datetime(year=now.year, month=now.month, day=now.day)
        today_sign_ts = int(daystart.timestamp())
        old_sign_ts = int(self.x_sign[:10])
        if old_sign_ts < today_sign_ts:
            self.x_sign = self._get_sign()
        return self.x_sign

    def _get_sign(self):
        """
        get sign for api anti-spam
        :return:
        """
        options = webdriver.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--headless')
        with webdriver.Chrome(options=options, desired_capabilities=self.caps) as browser:
            url = conf.get('qieman', 'url_sign_mock')
            if not url:
                raise Exception("sign_mock_url is none...")
            try:
                browser.get(url)
                info = browser.get_log('performance')
                for i in info:
                    dic_info = json.loads(i["message"])
                    info = dic_info["message"]['params']
                    if ('request' in info and 'headers' in info['request']
                            and 'x-sign' in info['request']['headers']):
                        return info['request']['headers']['x-sign']
            except Exception as e:
                logging.error("get qieman sign error {}".format(e))
