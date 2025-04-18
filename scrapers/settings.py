BOT_NAME = 'rawbeans'

SPIDER_MODULES = ['scrapers.spiders']
NEWSPIDER_MODULE = 'scrapers.spiders'

# 遵循robots.txt规则
ROBOTSTXT_OBEY = True

# 设置默认请求头
DEFAULT_REQUEST_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
}

# 下载延迟，避免对服务器施加太大压力
DOWNLOAD_DELAY = 2

# 禁用cookies
COOKIES_ENABLED = False

# 配置日志级别
LOG_LEVEL = 'INFO'

# 配置项目管道
ITEM_PIPELINES = {
    'scrapers.pipelines.RawBeansPipeline': 300,
}

# Windows平台特殊设置
import platform
if platform.system() == 'Windows':
    # 禁用信号处理，避免Windows平台问题
    SIGNALS_DISABLE_REACTOR_STOP = True
    SIGNALS_DISABLE_SHUTDOWN_HANDLERS = True
    # 禁用telnet控制台，避免Windows平台问题
    TELNETCONSOLE_ENABLED = False 