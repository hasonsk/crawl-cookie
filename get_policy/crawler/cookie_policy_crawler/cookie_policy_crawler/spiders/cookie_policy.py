# cookie_policy_crawler/spiders/cookie_policy.py
import scrapy
import csv
import json
import re
import datetime
import logging
import os
from functools import lru_cache
from bs4 import BeautifulSoup
from lingua import LanguageDetectorBuilder
from deep_translator import GoogleTranslator
from boilerpy3 import extractors

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scrapy_crawler.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Thư mục đầu ra
os.makedirs('data/crawled/policy_results', exist_ok=True)

# Lấy stop words chỉ một lần và cache lại
@lru_cache(maxsize=1)
def get_cached_stop_words(url):
    """Lấy và cache stop words"""
    try:
        import requests
        response = requests.get(url)
        if response.status_code == 200:
            return [word.strip() for word in response.text.split('\n') if word.strip()]
        return []
    except Exception as e:
        logger.warning(f"Không thể lấy stop words từ {url}: {e}. Đang sử dụng list trống.")
        return []

stop_words_url = "https://raw.githubusercontent.com/stopwords/vietnamese-stopwords/master/vietnamese-stopwords.txt"
stop_words_list = get_cached_stop_words(stop_words_url)

@lru_cache(maxsize=32)
def get_language_detector():
    """Tạo và cache language detector"""
    return LanguageDetectorBuilder.from_all_languages().build()

class CookiePolicySpider(scrapy.Spider):
    name = "cookie_policy"
    custom_settings = {
        'DOWNLOAD_TIMEOUT': 30,
        'ROBOTSTXT_OBEY': True,
        'CONCURRENT_REQUESTS': 16,
        'DOWNLOAD_DELAY': 0.5,
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'ITEM_PIPELINES': {
            'cookie_policy_crawler.pipelines.CookiePolicyPipeline': 300,
        },
        'FEEDS': {
            'data/crawled/policy_results/results_%(time)s.json': {
                'format': 'json',
                'encoding': 'utf8',
                'store_empty': False,
                'indent': 2,
            },
        },
        'LOG_LEVEL': 'INFO'
    }

    def __init__(self, *args, **kwargs):
        super(CookiePolicySpider, self).__init__(*args, **kwargs)
        self.detector = get_language_detector()
        self.processed_count = 0
        self.success_count = 0
        self.error_count = 0

    def start_requests(self):
        urls = getattr(self, 'start_urls', [])

        if not urls:
            # Nếu không có URLs được cung cấp, thử đọc từ file
            urls_file = getattr(self, 'urls_file', None)
            if urls_file and os.path.exists(urls_file):
                urls = self.load_urls_from_file(urls_file)

        for url in urls:
            yield scrapy.Request(
                url=url,
                callback=self.parse,
                errback=self.errback_handler,
                meta={
                    'download_timeout': 30,
                    'max_retry_times': 2,
                }
            )

    def load_urls_from_file(self, file_path):
      """Đọc URLs từ file và lấy URL cookie policy"""
      urls = []
      try:
        with open(file_path, 'r', encoding='utf-8') as f:
          for line in f:
            parts = line.strip().split(',')
            if len(parts) == 2 and parts[1].strip().startswith(('http://', 'https://')):
              urls.append(parts[1].strip())

        logger.info(f"Đã tải {len(urls)} URLs cookie policy từ file {file_path}")
      except Exception as e:
        logger.error(f"Lỗi đọc file {file_path}: {e}")
      return urls

    def errback_handler(self, failure):
        """Xử lý lỗi khi request thất bại"""
        url = failure.request.url
        self.error_count += 1

        # Lấy thông tin lỗi
        error_message = str(failure.value)
        if hasattr(failure.value, 'reason'):
            error_message = str(failure.value.reason)

        logger.error(f"Request thất bại cho {url}: {error_message}")

        yield {
            "url": url,
            "error": error_message,
            "timestamp": datetime.datetime.now().isoformat()
        }

    def parse(self, response):
        url = response.url
        self.processed_count += 1
        logger.info(f"Processing {self.processed_count}: {url}")

        try:
            # Lấy HTML content
            html_content = response.body.decode('utf-8')

            # Trích xuất nội dung chính
            main_content = self.extract_main_content(html_content)

            # Trích xuất bảng
            tables = self.enhanced_table_extraction(html_content)

            # Phát hiện ngôn ngữ
            # lang = self.detect_language_optimized(main_content)

            # Làm sạch và xử lý text
            original_text, processed_text, lang = self.process_vietnamese_text(main_content)

            # Tạo kết quả
            result = {
                "url": url,
                "lang": lang,
                "original_text": original_text,
                "processed_text": processed_text,
                "tables": tables,
                "timestamp": datetime.datetime.now().isoformat()
            }

            self.success_count += 1
            # In tiến độ sau mỗi 10 URLs
            if self.processed_count % 10 == 0:
                logger.info(f"Tiến độ: {self.success_count} thành công / {self.error_count} lỗi / {self.processed_count} tổng")

            return result

        except Exception as e:
            self.error_count += 1
            logger.error(f"Lỗi xử lý {url}: {str(e)}")
            return {
                "url": url,
                "error": str(e),
                "timestamp": datetime.datetime.now().isoformat()
            }

    def extract_main_content(self, html):
        """Trích xuất nội dung chính sử dụng nhiều phương pháp"""
        # Thử với boilerpy3 trước
        try:
            extractor = extractors.ArticleExtractor()
            content = extractor.get_content(html)
            if content and len(content) > 100:  # Có đủ nội dung
                return self.remove_links(content)
        except Exception as e:
            logger.debug(f"Boilerpy3 extraction failed: {e}")

        # Fallback: Dùng BeautifulSoup
        try:
            soup = BeautifulSoup(html, 'lxml')

            # Loại bỏ các phần tử không cần thiết
            for tag in soup(['script', 'style', 'nav', 'footer', 'header',
                           'form', 'iframe', 'aside', 'meta', 'link', 'noscript']):
                tag.decompose()

            # Tìm các phần tử policy phổ biến
            policy_selectors = [
                {'name': 'div', 'class': re.compile(r'cookie|policy|privacy|chính\s*sách', re.I)},
                {'name': 'section', 'id': re.compile(r'cookie|policy|privacy|chính\s*sách', re.I)},
                {'name': 'article', 'class': re.compile(r'content|main|article|body', re.I)},
                {'name': 'div', 'id': re.compile(r'content|main|article|body', re.I)},
                {'name': 'main'},  # HTML5 main tag
            ]

            for selector in policy_selectors:
                elements = soup.find_all(**selector)
                if elements:
                    # Ưu tiên phần tử có nhiều nội dung nhất
                    elements.sort(key=lambda x: len(x.get_text()), reverse=True)
                    return self.remove_links(elements[0].get_text(separator=' ', strip=True))

            # Nếu không tìm thấy phần tử cụ thể, lấy toàn bộ nội dung body
            body = soup.find('body')
            if body:
                return self.remove_links(body.get_text(separator=' ', strip=True))

            # Fallback cuối cùng
            return self.remove_links(soup.get_text(separator=' ', strip=True))

        except Exception as e:
            logger.error(f"HTML extraction error: {e}")
            return ""

    def remove_links(self, text):
        """Loại bỏ các đường link dẫn đến trang web"""
        return re.sub(r'https?://', '', text)

    def enhanced_table_extraction(self, html):
        """Cải tiến trích xuất bảng với xử lý dự phòng tốt hơn"""
        if not html:
            return []

        try:
            soup = BeautifulSoup(html, 'lxml')
            tables = soup.find_all('table')
            table_data = []

            for table in tables:
                try:
                    # Thử trích xuất tiêu đề từ thead hoặc tr đầu tiên
                    headers = []
                    thead = table.find('thead')
                    if thead and thead.find_all('th'):
                        headers = [th.get_text(strip=True) for th in thead.find_all('th')]
                    else:
                        first_row = table.find('tr')
                        if first_row:
                            headers = [th.get_text(strip=True) for th in first_row.find_all(['th', 'td'])]

                    # Nếu không có tiêu đề hợp lệ, bỏ qua bảng này
                    if not headers or len(headers) < 2:
                        continue

                    # Xử lý các hàng dữ liệu
                    rows = []
                    data_rows = table.find_all('tr')
                    # Bỏ qua hàng đầu tiên nếu đó là tiêu đề
                    start_idx = 1 if len(data_rows) > 0 and len(data_rows[0].find_all('th')) > 0 else 0

                    for tr in data_rows[start_idx:]:
                        cells = tr.find_all('td')
                        if not cells or len(cells) != len(headers):
                            continue

                        row = {headers[i]: cell.get_text(strip=True)
                              for i, cell in enumerate(cells) if i < len(headers)}

                        # Chỉ thêm hàng nếu có dữ liệu
                        if any(val.strip() for val in row.values()):
                            rows.append(row)

                    if rows and len(rows) > 0:
                        table_data.append({
                            "table_metadata": {
                                "columns": headers,
                                "row_count": len(rows)
                            },
                            "data": rows
                        })
                except Exception as e:
                    logger.debug(f"Lỗi khi xử lý bảng: {e}")
                    continue

            return table_data
        except Exception as e:
            logger.error(f"Lỗi trích xuất bảng: {e}")
            return []

    def process_vietnamese_text(self, text):
        """Xử lý text Tiếng Việt, dịch nếu không phải tiếng Việt và làm sạch nội dung"""
        if not text:
            return "", "", None

        lang = self.detect_language_optimized(text)
        translated_text = text

        if lang != "vi":
            try:
                translated_text = GoogleTranslator(source='auto', target='vi').translate(text)
                logger.info(f"Dịch từ {lang} sang tiếng Việt: {text[:30]}...")
            except Exception as e:
                logger.error(f"Lỗi khi dịch văn bản: {e}")
                translated_text = None  # Nếu lỗi, giữ nguyên văn bản gốc

        try:
            if translated_text:
                # Loại bỏ khoảng trắng thừa
                translated_text = re.sub(r'\s+', ' ', translated_text).strip()

                # Loại bỏ stopwords
                if stop_words_list:
                    # words = translated_text.split()
                    # filtered_words = [word for word in words if word.lower() not in stop_words_list]
                    # translated_text = ' '.join(filtered_words)

                    return text, translated_text, lang

        except Exception as e:
            logger.error(f"Lỗi xử lý text: {e}")
            return  text, translated_text, lang

    def detect_language_optimized(self, text):
        """Phát hiện ngôn ngữ với nhiều phương pháp"""
        if not text or len(text) < 50:
            return None

        # Phát hiện Vietnamese bằng các từ đặc trưng
        vietnamese_patterns = [
            r'\b(của|và|trong|những|các|không|được|một|có|là|đã|với|này|cho|đến|từ|về|bạn)\b'
        ]

        for pattern in vietnamese_patterns:
            if len(re.findall(pattern, text, re.I)) > 5:
                return "vi"

        # Sử dụng lingua để phát hiện ngôn ngữ
        try:
            detected_lang = self.detector.detect_language_of(text[:1000])
            if detected_lang:
                return detected_lang.iso_code_639_1.name.lower()
        except Exception as e:
            logger.warning(f"Language detection error: {e}")

        return "unknown"

    def closed(self, reason):
        """Thực thi khi spider kết thúc"""
        logger.info(f"Spider closed: {reason}")
        logger.info(f"Kết quả cuối cùng: {self.success_count} thành công / {self.error_count} lỗi / {self.processed_count} tổng")

        # Tạo báo cáo tóm tắt
        summary = {
            "total_processed": self.processed_count,
            "successful": self.success_count,
            "failed": self.error_count,
            "completion_time": datetime.datetime.now().isoformat()
        }

        with open(f'data/crawled/policy_results/summary_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.json', 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
