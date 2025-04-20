import os
import sys
import argparse
import time
import logging
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from cookie_policy_crawler.spiders.cookie_policy import CookiePolicySpider

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("run_crawler.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main():
    """Chạy crawler với các tùy chọn dòng lệnh"""
    parser = argparse.ArgumentParser(description='Crawl cookie policies và trích xuất nội dung')
    parser.add_argument('--urls-file', '-f', required=True,
                        help='File chứa danh sách URLs (CSV hoặc txt)')
    parser.add_argument('--output-dir', '-o', default='data/crawled/policy_results',
                        help='Thư mục lưu kết quả')
    parser.add_argument('--concurrent', '-c', type=int, default=16,
                        help='Số lượng request đồng thời')
    parser.add_argument('--delay', '-d', type=float, default=0.5,
                        help='Thời gian delay giữa các request')
    parser.add_argument('--timeout', '-t', type=int, default=30,
                        help='Thời gian timeout cho mỗi request (giây)')
    parser.add_argument('--log-level', '-l', default='INFO',
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                        help='Mức độ logging')

    args = parser.parse_args()

    start_time = time.time()
    logger.info(f"Bắt đầu crawl với file URLs: {args.urls_file}")

    if not os.path.exists(args.urls_file):
        logger.error(f"File không tồn tại: {args.urls_file}")
        sys.exit(1)

    # Đảm bảo thư mục đầu ra tồn tại
    os.makedirs(args.output_dir, exist_ok=True)

    # Tạo settings cho Scrapy
    settings = get_project_settings()
    settings.update({
        'CONCURRENT_REQUESTS': args.concurrent,
        'DOWNLOAD_DELAY': args.delay,
        'DOWNLOAD_TIMEOUT': args.timeout,
        'LOG_LEVEL': args.log_level,
        'FEEDS': {
            f'{args.output_dir}/results_%(time)s.json': {
                'format': 'json',
                'encoding': 'utf8',
                'indent': 2,
            },
        },
    })

    # Tạo crawler process
    process = CrawlerProcess(settings)

    # Khởi chạy spider
    process.crawl(CookiePolicySpider, urls_file=args.urls_file)
    process.start()  # Script sẽ block ở đây cho đến khi crawl xong

    elapsed_time = time.time() - start_time
    logger.info(f"Crawl hoàn tất trong {elapsed_time:.2f} giây")

if __name__ == "__main__":
    main()
