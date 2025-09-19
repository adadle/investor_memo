# 且慢平台数据抓取

## 项目简介

本项目主要解决个人日常理财平台的数据抓取功能，方便后续自动化记账及数据分析工作。

## 功能特性

### 且慢平台数据抓取
- **Mock登录设计实现**: 爬取数据和个人账户相关，在调用data api之前，需要拿到access_token，通过chrome抓包使用登录api的形式，伪装登录请求
- **x-sign的捕获及更新**: 在调用登录API时，服务端进行接口加密操作，使用chrome webdriver伪造请求，拿到服务端的sign值

### 应用功能
- 抓取每日收益
- 抓取指定基金、组合的数据

## 技术实现

### 核心组件
- `QiemanCraw`: 主要的数据抓取类
  - `_get_access_token()`: 获取访问令牌
  - `_get_sign()`: 获取x-sign签名
  - `fetch_profit_history()`: 抓取历史收益数据
- `DailyProfit`: 每日收益数据模型
- `configuration`: 配置管理模块
- `date_util`: 日期工具函数

## 部署和自动化

### 环境要求
- Python 3.x
- Chrome浏览器
- ChromeDriver
- MySQL数据库

### 安装步骤

1. **安装Python依赖**
   ```bash
   pip install -r requirements.txt
   ```

2. **安装Chrome WebDriver**
   ```bash
   # 设置yum repo
   cat > /etc/yum.repos.d/google-chrome.repo << EOF
   [google-chrome]
   name=google-chrome
   baseurl=http://dl.google.com/linux/chrome/rpm/stable/x86_64
   enabled=1
   gpgcheck=1
   gpgkey=https://dl.google.com/linux/linux_signing_key.pub
   EOF
   
   # 安装chrome浏览器
   yum install -y google-chrome-stable --nogpgcheck
   
   # 下载并安装chromedriver
   wget -N https://chromedriver.storage.googleapis.com/2.35/chromedriver_linux64.zip -P ~/
   unzip ~/chromedriver_linux64.zip -d ~/
   mv -f ~/chromedriver /usr/local/bin/chromedriver
   chmod 0755 /usr/local/bin/chromedriver
   export PATH="/usr/local/bin:$PATH"
   ```

3. **安装数据库**
   - 使用MySQL进行存储
   - DDL可参考`scripts/db.sql`

4. **配置环境变量**
   - 默认读取`qieman/config.cfg`文件
   - 生产环境设置: `export IS_PROD=1`
   - 生产环境配置文件路径: `~/.fire/craw_config.cfg`

### 自动化运行

设置crontab自动运行:
```bash
0 8 * * 6 source /root/.zshrc; export IS_PROD=1; export PATH="/usr/local/bin:$PATH"; cd /path/to/project; python qieman/main.py >> /data/logs/qieman.log 2>&1
```

## 使用方法

### 基本使用
```python
from qieman import QiemanCraw

# 创建爬虫实例
craw = QiemanCraw()

# 抓取历史收益数据
craw.fetch_profit_history()
```

### 直接运行
```bash
python qieman/main.py
```

## 配置说明

在`qieman/config.cfg`文件中配置以下参数:

```ini
[qieman]
login_user=your_username
login_password=your_password
url_sign_mock=https://qieman.com
url_profit=https://qieman.com/pmdj/v2/user/profits-history
url_login=https://qieman.com/pmdj/v1/user/login

[backend]
mysql_conn_url=mysql://user:password@host:port/database
```

## 更新日志

- 2021-09-28 完成v1.0的且慢每日收益抓取入库
- 2024-01-XX 重构代码结构，将所有且慢相关代码整合到qieman目录下