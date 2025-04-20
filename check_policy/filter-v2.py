import asyncio
import aiohttp
from bs4 import BeautifulSoup
import json
import os
import logging
from urllib.parse import urljoin, urlparse
from aiohttp import ClientTimeout, TCPConnector
import time
from typing import List, Set, Tuple, Optional

# Thiết lập logging đơn giản
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

# Chỉ giữ lại từ khóa liên quan đến cookie
COOKIE_KEYWORDS = [
    'cookie', 'cookies', 'cookie-policy', 'cookie-notice', 'cookie-statement',
    'cookie-consent', 'cookie-preferences', 'chính sách cookie', 'cookies', 'chính sách quyền riêng tư và cookie', 'chính sách bảo mật và cookie',
]

# User-Agent tối thiểu
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
}

class FastCookiePolicyChecker:
    def __init__(self, urls_file: str, output_dir: str, batch_size: int = 50, timeout: int = 15):
        self.urls_file = urls_file
        self.output_dir = output_dir
        self.batch_size = batch_size
        self.timeout = timeout

        os.makedirs(output_dir, exist_ok=True)

        self.has_policy_file = os.path.join(output_dir, "has_policy_urls.json")
        self.no_policy_file = os.path.join(output_dir, "no_policy_urls.json")
        self.error_urls_file = os.path.join(output_dir, "error_urls.json")

        self.has_policy_urls = []
        self.no_policy_urls = []
        self.error_urls = []

        self._load_existing_data()
        self.processed_urls = self._get_processed_urls()

    def _load_existing_data(self):
        """Đọc dữ liệu đã có từ các file output"""
        for filename, target_list in [
            (self.has_policy_file, self.has_policy_urls),
            (self.no_policy_file, self.no_policy_urls),
            (self.error_urls_file, self.error_urls)
        ]:
            if os.path.exists(filename):
                try:
                    with open(filename, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if isinstance(target_list, list):
                            target_list.extend(data)
                        else:
                            target_list = data
                    logger.info(f"Loaded {len(data)} URLs from {filename}")
                except Exception as e:
                    logger.error(f"Error loading {filename}: {e}")

    def _get_processed_urls(self) -> Set[str]:
        """Trả về tập hợp các URL đã được xử lý"""
        processed = set()
        processed.update(item['url'] for item in self.has_policy_urls)
        processed.update(self.no_policy_urls)
        processed.update(item['url'] for item in self.error_urls)
        return processed

    def _save_results(self):
        """Lưu kết quả vào các file"""
        for filename, data in [
            (self.has_policy_file, self.has_policy_urls),
            (self.no_policy_file, self.no_policy_urls),
            (self.error_urls_file, self.error_urls)
        ]:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

    async def _search_bing_for_cookie_policy(self, session, domain: str) -> Optional[str]:
        """Tìm kiếm cookie policy của domain trên Bing - tối ưu hóa chỉ tìm cookie"""
        try:
            search_query = f"{domain} cookie policy OR cookie notice"
            search_url = f"https://www.bing.com/search?q={search_query}"

            async with session.get(search_url, headers=HEADERS, timeout=self.timeout) as response:
                if response.status != 200:
                    return None

                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')

                # Chỉ lấy 3 kết quả đầu tiên
                search_results = soup.select('.b_algo h2 a')[:3]

                for result in search_results:
                    result_url = result.get('href', '')
                    result_text = result.text.lower()

                    # Tối ưu: Kiểm tra nhanh các từ khóa cookie
                    is_cookie_policy = any(keyword in result_url.lower() or keyword in result_text for keyword in COOKIE_KEYWORDS)

                    # Kiểm tra domain nhanh
                    result_domain = urlparse(result_url).netloc
                    original_domain = urlparse(f"https://{domain}").netloc

                    if is_cookie_policy and (domain in result_domain or result_domain in domain):
                        return result_url

                return None
        except Exception:
            return None

    async def _find_cookie_policy_url(self, session, url: str) -> Tuple[str, Optional[str]]:
        """Tìm URL của cookie policy trong trang web - phiên bản tối ưu"""
        try:
            # Làm sạch URL
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url

            async with session.get(url, headers=HEADERS, timeout=self.timeout) as response:
                if response.status != 200:
                    domain = urlparse(url).netloc
                    # Nếu trang không truy cập được, thử tìm trên Bing
                    policy_url = await self._search_bing_for_cookie_policy(session, domain)
                    return url, policy_url

                html = await response.text()

                # Sử dụng parser nhanh hơn
                soup = BeautifulSoup(html, 'html.parser')

                # Chỉ tìm trong các thẻ a có href
                for link in soup.find_all('a', href=True):
                    href = link.get('href')

                    # Bỏ qua các href không hợp lệ
                    if not href or href.startswith('#') or href.startswith('javascript:'):
                        continue

                    # Tối ưu: chỉ kiểm tra URL và text nếu chứa từ 'cookie'
                    if 'cookie' not in href.lower() and 'cookie' not in link.text.lower():
                        continue

                    # Chuyển href thành URL tuyệt đối
                    full_url = urljoin(url, href)

                    # Kiểm tra chính xác URL và văn bản liên kết
                    link_text = link.text.lower()
                    url_lower = full_url.lower()

                    is_cookie_policy = any(keyword in url_lower for keyword in COOKIE_KEYWORDS) or \
                                    any(keyword in link_text for keyword in COOKIE_KEYWORDS)

                    if is_cookie_policy:
                        return url, full_url

                # Nếu không tìm thấy trong trang, thử tìm trên Bing
                domain = urlparse(url).netloc
                policy_url = await self._search_bing_for_cookie_policy(session, domain)
                return url, policy_url

        except asyncio.TimeoutError:
            logger.warning(f"Timeout for {url}")
            return url, None
        except Exception as e:
            logger.error(f"Error processing {url}: {str(e)[:100]}")
            return url, None

    async def _process_url_batch(self, urls: List[str]):
        """Xử lý một batch các URL - phiên bản tối ưu"""
        connector = TCPConnector(limit=self.batch_size, ssl=False)
        timeout = ClientTimeout(total=self.timeout)

        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            tasks = []
            for url in urls:
                if url in self.processed_urls:
                    continue
                tasks.append(self._find_cookie_policy_url(session, url))

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, Exception):
                    continue

                if not isinstance(result, tuple):
                    continue

                original_url, policy_url = result

                if policy_url:
                    self.has_policy_urls.append({
                        'url': original_url,
                        'policy_url': policy_url
                    })
                    self.processed_urls.add(original_url)
                elif policy_url is None:
                    self.error_urls.append({
                        'url': original_url,
                        'error': "Failed to access"
                    })
                    self.processed_urls.add(original_url)
                else:
                    self.no_policy_urls.append(original_url)
                    self.processed_urls.add(original_url)

            # Lưu kết quả sau mỗi batch
            self._save_results()

    async def process_urls(self):
        """Xử lý tất cả các URL từ file - phiên bản tối ưu"""
        try:
            # Đọc danh sách URL
            with open(self.urls_file, 'r', encoding='utf-8') as f:
                urls = [line.strip() for line in f if line.strip()]

            logger.info(f"URLs to process: {len(urls)}, already processed: {len(self.processed_urls)}")

            # Lọc các URL chưa xử lý
            urls_to_process = [url for url in urls if url not in self.processed_urls]

            # Xử lý theo batch
            for i in range(0, len(urls_to_process), self.batch_size):
                batch = urls_to_process[i:i + self.batch_size]
                logger.info(f"Batch {i//self.batch_size + 1}/{(len(urls_to_process)-1)//self.batch_size + 1}: {len(batch)} URLs")

                await self._process_url_batch(batch)

                # Giảm thời gian chờ giữa các batch
                if i + self.batch_size < len(urls_to_process):
                    time.sleep(1)

            logger.info("Completed!")

        except Exception as e:
            logger.error(f"Error: {e}")
            self._save_results()

async def main():
    import argparse

    parser = argparse.ArgumentParser(description='Fast Cookie Policy Checker')
    parser.add_argument('-f', '--urls-file', required=True, help='Path to file with URLs')
    parser.add_argument('-o', '--output-dir', default='results', help='Output directory')
    parser.add_argument('-b', '--batch-size', type=int, default=50, help='Batch size')
    parser.add_argument('-t', '--timeout', type=int, default=15, help='Timeout (seconds)')

    args = parser.parse_args()

    checker = FastCookiePolicyChecker(
        urls_file=args.urls_file,
        output_dir=args.output_dir,
        batch_size=args.batch_size,
        timeout=args.timeout
    )

    await checker.process_urls()

if __name__ == "__main__":
    asyncio.run(main())
