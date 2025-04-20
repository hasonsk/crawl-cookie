import scrapy
import csv
import re
from urllib.parse import urlparse


class CookiePolicySpider(scrapy.Spider):
    name = "cookie_policy"
    custom_settings = {
        'DOWNLOAD_DELAY': 1,
        'ROBOTSTXT_OBEY': False,
        'USER_AGENT': 'Mozilla/5.0',
        'LOG_LEVEL': 'INFO',
    }

    def __init__(self, input_csv=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_urls = []
        if input_csv:
            with open(input_csv, newline='') as f:
                reader = csv.DictReader(f)
                self.start_urls = [row['URL'].strip() for row in reader if row.get('URL')]
        self.cookie_pattern = re.compile(
            r'cookie policy|chính sách cookie|thông báo về cookie|cookie settings|cookie preferences'
            r'|cookies|cookie policy của chúng tôi|chính sách bảo mật và cookie'
            r'chính sách quyền riêng tư và cooki|',
            re.IGNORECASE
        )
        self.result_with_policy = []
        self.result_without_policy = []
        self.result_cannot_reach = []

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(url=url, callback=self.parse_homepage, errback=self.handle_failure, meta={'original_url': url})

    def parse_homepage(self, response):
        original_url = response.meta['original_url']
        # Tìm liên kết có nội dung liên quan cookie
        links = response.css('a::attr(href)').getall()
        texts = response.css('a::text').getall()
        candidates = set(zip(texts, links))

        for text, href in candidates:
            if href and self.cookie_pattern.search(text or '') or self.cookie_pattern.search(href):
                yield response.follow(href, callback=self.parse_cookie_page, meta={'original_url': original_url})
                return

        # Nếu không tìm thấy, search Bing
        domain = urlparse(original_url).netloc
        query_url = f"https://www.bing.com/search?q=site:{domain}+cookie+policy"
        yield scrapy.Request(url=query_url, callback=self.parse_bing_results, meta={'original_url': original_url})

    def parse_bing_results(self, response):
        original_url = response.meta['original_url']
        result_url = response.css("li.b_algo h2 a::attr(href)").get()
        if result_url:
            yield scrapy.Request(url=result_url, callback=self.parse_cookie_page, meta={'original_url': original_url})
        else:
            self.result_without_policy.append(original_url)

    def parse_cookie_page(self, response):
        original_url = response.meta['original_url']
        if response.text.lower().count("cookie") > 5:
            self.logger.info(f"[FOUND] {original_url} → {response.url}")
            self.result_with_policy.append((original_url, response.url))
        else:
            self.result_without_policy.append(original_url)

    def handle_failure(self, failure):
        url = failure.request.meta.get('original_url')
        self.logger.warning(f"[FAIL] Cannot access {url}")
        self.result_cannot_reach.append(url)

    def closed(self, reason):
        # Save results
        import csv

        with open("urls_with_policy.csv", "w", newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["URL", "Policy URL"])
            writer.writerows(self.result_with_policy)

        def save_list(data, path):
            with open(path, "w", newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["URL"])
                for url in data:
                    writer.writerow([url])

        save_list(self.result_without_policy, "urls_without_policy.csv")
        save_list(self.result_cannot_reach, "urls_cannot_reach.csv")
