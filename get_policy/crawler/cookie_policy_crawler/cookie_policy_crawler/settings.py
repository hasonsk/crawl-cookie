# cookie_policy_crawler/settings.py
BOT_NAME = 'cookie_policy_crawler'

SPIDER_MODULES = ['cookie_policy_crawler.spiders']
NEWSPIDER_MODULE = 'cookie_policy_crawler.spiders'

# Cấu hình tối ưu cho crawler
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'

# Tôn trọng robots.txt
ROBOTSTXT_OBEY = True

# Cấu hình đồng thời và delay
CONCURRENT_REQUESTS = 16
CONCURRENT_REQUESTS_PER_DOMAIN = 4
DOWNLOAD_DELAY = 0.5

# Timeout và retry
DOWNLOAD_TIMEOUT = 30
RETRY_ENABLED = True
RETRY_TIMES = 2
RETRY_HTTP_CODES = [500, 502, 503, 504, 522, 524, 408, 429]

# Cache
HTTPCACHE_ENABLED = True
HTTPCACHE_EXPIRATION_SECS = 86400
HTTPCACHE_DIR = 'httpcache'
HTTPCACHE_IGNORE_HTTP_CODES = [500, 502, 503, 504, 522, 524, 408, 429]

# Pipeline
ITEM_PIPELINES = {
   'cookie_policy_crawler.pipelines.CookiePolicyPipeline': 300,
}

# Cho phép redirect giới hạn
REDIRECT_ENABLED = True
REDIRECT_MAX_TIMES = 5

# Middleware
DOWNLOADER_MIDDLEWARES = {
    'scrapy.downloadermiddlewares.retry.RetryMiddleware': 500,
    'scrapy.downloadermiddlewares.redirect.RedirectMiddleware': 600,
}

# Logging
LOG_LEVEL = 'INFO'
LOG_FILE = 'scrapy.log'

# Tối ưu bộ nhớ
MEMUSAGE_ENABLED = True
MEMUSAGE_LIMIT_MB = 2048
MEMUSAGE_WARNING_MB = 1536

# Giới hạn độ sâu
DEPTH_LIMIT = 2

# Thiết lập để tránh bị block
DOWNLOAD_MAXSIZE = 10485760  # 10MB
COOKIES_ENABLED = False
AJAXCRAWL_ENABLED = True
