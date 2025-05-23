import json
import logging
import signal
import sys
import re
import csv
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from concurrent.futures import ThreadPoolExecutor, as_completed
from selenium.common.exceptions import WebDriverException, TimeoutException

# Configuration
MAX_WORKERS = 5
TIMEOUT = 10
SAVE_INTERVAL = 100
DRIVER_CACHE = None

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
        global DRIVER_CACHE
        if DRIVER_CACHE is None:
            DRIVER_CACHE = Service(ChromeDriverManager().install())

    def _register_signal_handler(self):
        signal.signal(signal.SIGINT, self._handle_interrupt)
        signal.signal(signal.SIGTERM, self._handle_interrupt)

    def _handle_interrupt(self, signum, frame):
        logging.info("Received interrupt signal. Saving results...")
        self._save_results()
        sys.exit(0)

    def _atomic_save(func):
        def wrapper(self, *args, **kwargs):
            while self.lock:
                pass
            self.lock = True
            result = func(self, *args, **kwargs)
            self.lock = False
            return result
        return wrapper

    @_atomic_save
    def _save_results(self):
        try:
            self._save_to_csv('../data/crawled/check_policy/urls_120001_132000/urls_with_cookie_policy.csv', self.urls_with_policy)
            self.urls_with_policy = []
            self._save_to_csv('../data/crawled/check_policy/urls_120001_132000/urls_without_cookie_policy.csv', [[url] for url in self.urls_without_policy])
            self.urls_without_policy = []
            self._save_to_csv('../data/crawled/check_policy/urls_120001_132000/urls_cannot_reach.csv', [[url] for url in self.urls_cannot_reach])
            self.urls_cannot_reach = []
            logging.info(f"Progress saved. Total processed: {len(self.processed_urls)}")
        except Exception as e:
            logging.error(f"Error saving results: {e}")
            sys.exit(-1)

    def _save_to_csv(self, file_path, data):
        with open(file_path, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(data)

    def setup_driver(self):
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--blink-settings=imagesEnabled=false")
        options.add_argument("--log-level=3")
        return webdriver.Chrome(service=DRIVER_CACHE, options=options)

    def _is_connection_error(self, exception):
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
            WebDriverWait(driver, TIMEOUT).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))

            cookie_pattern = re.compile(
                r'chính sách cookie|cookie policy|cookies|cookie policy của chúng tôi|'
                r'thông báo về cookie|chính sách quyền riêng tư và cookie|'
                r'chính sách bảo mật và cookie|cookie settings|cookie preferences|politica cookies|Cookies',
                re.IGNORECASE
            )

            all_links = driver.find_elements(By.TAG_NAME, 'a')
            candidate_links = [
                (link.text, link.get_attribute('href'))
                for link in all_links if link.get_attribute('href')
            ]

            for text, href in candidate_links:
                if cookie_pattern.search(text) or cookie_pattern.search(href):
                    try:
                        driver.get(href)
                        WebDriverWait(driver, TIMEOUT // 2).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
                        body_text = driver.find_element(By.TAG_NAME, 'body').text.lower()
                        if body_text.count("cookie") > 5:
                            logging.info(f"Found policy at {href}")
                            return url, href
                    except Exception:
                        continue

            search_query = f"site:{url} (Cookie policy OR chính sách cookie)"
            driver.get(f"https://www.google.com/search?q={search_query}")
            try:
                WebDriverWait(driver, TIMEOUT).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div.g')))
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
                except Exception as e:
                    logging.error(f"Processing failed: {str(e)[:200]}")

                if (i + 1) % SAVE_INTERVAL == 0:
                    self._save_results()

        self._save_results()
        return self.urls_with_policy, self.urls_without_policy, self.urls_cannot_reach

def read_urls_from_csv_files(file_paths):
    urls = set()
    for file_path in file_paths:
        try:
            with open(file_path, 'r') as f:
                reader = csv.reader(f)
                next(reader, None)
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
            writer.writerow(['URL'])
            for url in urls:
                writer.writerow([url])
    except Exception as e:
        logging.error(f"Error writing to file {file_path}: {e}")

def filter_urls(output_file='../data/crawled/combined_urls.csv'):
    input_files = ["../data/raws/splitted-v3/urls_120001_132000.csv"]
    reference_files = [
        "../data/crawled/check_policy/urls_120001_132000/urls_cannot_reach-v1.csv",
        "../data/crawled/check_policy/urls_120001_132000/urls_without_cookie_policy-v1.csv",
        "../data/crawled/check_policy/urls_120001_132000/urls_with_cookie_policy-v1.csv",
        "../data/crawled/check_policy/urls_120001_132000/urls_cannot_reach.csv",
        "../data/crawled/check_policy/urls_120001_132000/urls_without_cookie_policy.csv",
        "../data/crawled/check_policy/urls_120001_132000/urls_with_cookie_policy.csv",
    ]

    reference_urls = read_urls_from_csv_files(reference_files)
    input_urls = read_urls_from_csv_files(input_files)
    filtered_urls = [url for url in input_urls if url not in reference_urls]

    write_urls_to_csv(filtered_urls, output_file)
    logging.info(f"Filtered URLs saved to {output_file} with {len(filtered_urls)} entries.")

def main():
    # input_file = "../data/crawled/combined_urls.csv"
    input_file = "../data/raws/splitted-v3/urls_120001_132000.csv"
    # create output directory if not exists
    output_dir = "../data/crawled/check_policy/urls_120001_132000"
    os.makedirs(output_dir, exist_ok=True)
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

if __name__ == "__main__":
    main()
    # filter_urls()
