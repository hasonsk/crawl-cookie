import logging
import signal
import sys
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from concurrent.futures import ThreadPoolExecutor, as_completed
from selenium.common.exceptions import WebDriverException, TimeoutException
import csv
import argparse

# Configuration
MAX_WORKERS = 5
TIMEOUT = 10
SAVE_INTERVAL = 5
DRIVER_CACHE = None  # Cache for WebDriver service

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Crawler:
    def __init__(self):
        self.urls_with_policy = []
        self.urls_without_policy = []
        self.urls_cannot_reach = []
        self.processed_urls = set()
        self.lock = False
        self._register_signal_handler()
        self._init_driver_service()

    def _init_driver_service(self):
        """Initialize and cache ChromeDriver service"""
        global DRIVER_CACHE
        if DRIVER_CACHE is None:
            DRIVER_CACHE = Service(ChromeDriverManager().install())

    def _register_signal_handler(self):
        signal.signal(signal.SIGINT, self._handle_interrupt)
        signal.signal(signal.SIGTERM, self._handle_interrupt)

    def _handle_interrupt(self, signum, frame):
        logging.info("\nReceived interrupt signal. Saving results...")
        self._save_results()
        sys.exit(0)

    def _atomic_save(func):
        def wrapper(self, *args, **kwargs):
            while self.lock: pass
            self.lock = True
            result = func(self, *args, **kwargs)
            self.lock = False
            return result
        return wrapper

    @_atomic_save
    def _save_results(self):
        try:
            # Save successful URLs
            with open(f'data/crawled/filtered/output_folder/urls_with_cookie_policy.csv', 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerows(self.urls_with_policy)
                self.urls_with_policy = []

            # Save URLs without policy
            with open(f'data/crawled/filtered/output_folderurls_without_cookie_policy.csv', 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerows([[url] for url in self.urls_without_policy])
                self.urls_without_policy = []

            # Save unreachable URLs
            with open(f'data/crawled/filtered/output_folder/urls_cannot_reach.csv', 'a', newline='') as f:
                writer = csv.writer(f)
                # writer.writerow(['URL'])
                writer.writerows([[url] for url in self.urls_cannot_reach])
                self.urls_cannot_reach = []

            logging.info(f"Progress saved. Total processed: {len(self.processed_urls)}")
        except Exception as e:
            logging.error(f"Error saving results: {e}")

    def setup_driver(self):
        """Create new driver instance using cached service"""
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--blink-settings=imagesEnabled=false")
        options.add_argument("--log-level=3")  # Suppress console logs
        return webdriver.Chrome(service=DRIVER_CACHE, options=options)

    def _is_connection_error(self, exception):
        """Check if exception is related to connection issues"""
        error_messages = [
            'ERR_CONNECTION_TIMED_OUT',
            'ERR_NAME_NOT_RESOLVED',
            'ERR_CONNECTION_REFUSED',
            'Timed out'
        ]
        return any(msg in str(exception) for msg in error_messages)

    def process_url(self, url):
        if url in self.processed_urls:
            return
        self.processed_urls.add(url)

        driver = None
        try:
            driver = self.setup_driver()
            driver.set_page_load_timeout(TIMEOUT)

            logging.info(f"Crawling: {url}")
            driver.get(url)
            WebDriverWait(driver, TIMEOUT).until(
                EC.presence_of_element_located((By.TAG_NAME, 'body')))

            # Phần xử lý tìm chính sách cookie...
            # Precompile regex patterns
            cookie_pattern = re.compile(
                r'chính sách cookie|cookie policy|cookies|cookie policy của chúng tôi|'
                r'thông báo về cookie|chính sách quyền riêng tư và cookie|'
                r'chính sách bảo mật và cookie|cookie settings|cookie preferences',
                re.IGNORECASE
            )

            # Find all links once
            all_links = driver.find_elements(By.TAG_NAME, 'a')
            candidate_links = [
                (link.text, link.get_attribute('href'))
                for link in all_links
                if link.get_attribute('href')
            ]

            # Check links in descending order of priority
            for text, href in candidate_links:
                if cookie_pattern.search(text) or cookie_pattern.search(href):
                    try:
                        driver.get(href)
                        WebDriverWait(driver, TIMEOUT//2).until(
                            EC.presence_of_element_located((By.TAG_NAME, 'body')))
                        body_text = driver.find_element(By.TAG_NAME, 'body').text.lower()
                        if body_text.count("cookie") > 5:
                            logging.info(f"Found policy at {href}")
                            return url, href
                    except Exception:
                        continue

            # Fallback to Google search
            search_query = f"site:{url} (Cookie policy OR chính sách cookie)"
            driver.get(f"https://www.google.com/search?q={search_query}")
            try:
                WebDriverWait(driver, TIMEOUT).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'div.g')))
                first_result = driver.find_element(By.CSS_SELECTOR, 'div.g a')
                first_result_url = first_result.get_attribute('href')
                if url in first_result_url:
                    return url, first_result_url
            except Exception:
                pass

            return url, None

        except (WebDriverException, TimeoutException) as e:
            if self._is_connection_error(e):
                logging.error(f"Connection error for {url}: {str(e)[:200]}")
                self.urls_cannot_reach.append(url)
                return url, None
            else:
                logging.warning(f"General error for {url}: {str(e)[:200]}")
                self.urls_cannot_reach.append(url)
                return url, None
        except Exception as e:
            logging.error(f"Unexpected error for {url}: {str(e)[:200]}")
            self.urls_without_policy.append(url)
            return url, None
        finally:
            if driver:
                driver.quit()

    def crawl_cookie_policy(self, urls):
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(self.process_url, url): url for url in urls}

            for i, future in enumerate(as_completed(futures)):
                try:
                    base_url, policy_url = future.result()
                    if policy_url:
                        self.urls_with_policy.append((base_url, policy_url))
                    # Các URL không thể truy cập đã được xử lý trong process_url
                except Exception as e:
                    logging.error(f"Processing failed: {str(e)[:200]}")

                if (i + 1) % SAVE_INTERVAL == 0:
                    self._save_results()

        self._save_results()
        return self.urls_with_policy, self.urls_without_policy, self.urls_cannot_reach

def main():
    parser = argparse.ArgumentParser(description="Crawl cookie policies from URLs.")
    parser.add_argument('--file', type=str, help='Path to the input CSV file containing URLs')
    args = parser.parse_args()

    input_file = f'data/crawled/splitted-v3/{args.file}.csv'
    crawler = Crawler()

    try:
        with open(input_file, 'r') as f:
            reader = csv.DictReader(f)
            urls = list({row['URL'].strip() for row in reader if row['URL'].strip()})
        if not urls:
            logging.warning("No URLs found in the input file.")
            return

        logging.info(f"Starting to crawl {len(urls)} URLs")
        crawler.crawl_cookie_policy(urls)

    except FileNotFoundError:
        logging.error(f"Input file not found: {input_file}")
    except Exception as e:
        logging.error(f"Fatal error: {e}")
    finally:
        crawler._save_results()

# Viet ham doc từ 4 file, sau do loc ra cac url trung lap
def read_urls_from_csv_files(file_paths):
    urls = set()
    for file_path in file_paths:
        try:
            with open(file_path, 'r') as f:
                reader = csv.reader(f)
                next(reader, None)  # Skip header
                urls.update(row[0].strip() for row in reader if row and row[0].strip())
        except FileNotFoundError:
            logging.error(f"File not found: {file_path}")
        except Exception as e:
            logging.error(f"Error reading file {file_path}: {e}")
    return urls

def write_urls_to_csv(urls, file_path):
    try:
        with open(file_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['URL'])  # Write header
            for url in urls:
                writer.writerow([url])
    except Exception as e:
        logging.error(f"Error writing to file {file_path}: {e}")

def filter_urls(output_file = 'data/crawled/combined_urls.csv'):
    input_files = [
                "data/crawled/splitted-v3/urls_1_12000.csv"
                # 'data/crawled/splitted-v2/urls_1_12000.csv',
                # 'data/crawled/splitted-v2/urls_12001_24000.csv',
                # 'data/crawled/splitted-v2/urls_24001_36000.csv',
                ]

    reference_file = [
                "data/crawled/filtered/urls_1_120004/urls_cannot_reach.csv",
                "data/crawled/filtered/urls_1_120004/urls_without_cookie_policy.csv",
                "data/crawled/filtered/urls_1_120004/urls_with_cookie_policy.csv",
                "data/crawled/filtered/urls_1_120004/urls_cannot_reach-v1.csv",
                "data/crawled/filtered/urls_1_120004/urls_without_cookie_policy-v1.csv",
                "data/crawled/filtered/urls_1_120004/urls_with_cookie_policy-v1.csv",
                # "data/crawled/filtered/group_1/urls_list_10/urls_without_cookie_policy.csv",
                # "data/crawled/filtered/group_1/urls_list_10/urls_cannot_reach.csv",
                # "data/crawled/filtered/group_1/urls_list_10/urls_with_cookie_policy.csv",
                ]

    # Read URLs from the reference file
    reference_urls = read_urls_from_csv_files(reference_file)

    # Read URLs from the input files
    input_urls = read_urls_from_csv_files(input_files)
    print(f"Input URLs: {len(input_urls)}")

    # Filter out URLs that are present in the reference file
    filtered_urls = [url for url in input_urls if url not in reference_urls]
    print(f"Filtered URLs: {len(filtered_urls)}")

    # Write the filtered URLs to the output file
    write_urls_to_csv(filtered_urls, output_file)
    logging.info(f"Filtered URLs saved to {output_file}")

if __name__ == "__main__":
    main()
    # filter_urls()
