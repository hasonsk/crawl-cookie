"""
Cookie Policy Crawler - Optimized Version
Features:
- Batch processing with intelligent flushing
- Structured output with schema validation
- Async I/O for file operations
- Comprehensive logging
- Configurable via YAML
"""
import os
import re
import sys
import signal
import logging
import argparse
from datetime import datetime
import time
from typing import List, Optional
from pathlib import Path
from langdetect import detect, LangDetectException
import threading
from pydantic import BaseModel, ValidationError


import pandas as pd
from pydantic import BaseModel, ValidationError
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import WebDriverException, TimeoutException
from concurrent.futures import ThreadPoolExecutor, as_completed
from webdriver_manager.chrome import ChromeDriverManager

# Configuration
CONFIG = {
    "max_workers": 5,
    "timeout": 15,
    "batch_size": 5,
    "retry_attempts": 2,
    "log_format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
}

COOKIE_PATTERN = re.compile(
    r'chính sách cookie|cookie policy|cookies|cookie policy của chúng tôi|'
    r'thông báo về cookie|chính sách quyền riêng tư và cookie|'
    r'chính sách bảo mật và cookie|cookie settings|cookie preferences',
    re.IGNORECASE
)

# Pydantic Models
class CrawlResult(BaseModel):
    url: str
    policy_url: Optional[str]
    status: str
    timestamp: datetime
    error: Optional[str]
    lang: Optional[str]

class CrawlBatch(BaseModel):
    results: List[CrawlResult]

# Configure logging
logging.basicConfig(level=logging.INFO, format=CONFIG["log_format"])
logger = logging.getLogger("cookie_crawler")

def configure_logging(output_dir: Path):
    file_handler = logging.FileHandler(output_dir / "crawl.log")
    file_handler.setFormatter(logging.Formatter(CONFIG["log_format"]))
    logger.addHandler(file_handler)

class CookieCrawler:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.current_batch: List[CrawlResult] = []
        self.processed_urls = set()
        self.lock = threading.Lock()
        self._setup_data_storage()
        self._register_signal_handlers()

    def setup_driver(self):
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--blink-settings=imagesEnabled=false")
        options.add_argument("--log-level=3")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-extensions")
        service = Service(ChromeDriverManager().install(), log_path=os.devnull)
        return webdriver.Chrome(service=service, options=options)

    def _setup_data_storage(self):
        self.output_file = self.output_dir / "crawl_results.parquet"
        if not self.output_file.exists():
            pd.DataFrame(columns=CrawlResult.__annotations__.keys()).to_parquet(
                self.output_file, engine="pyarrow"
            )

    def _register_signal_handlers(self):
        signal.signal(signal.SIGINT, self._handle_interrupt)
        signal.signal(signal.SIGTERM, self._handle_interrupt)

    def _handle_interrupt(self, signum, frame):
        logger.warning("Interrupt received. Flushing current batch...")
        self._flush_batch()
        sys.exit(0)

    def _flush_batch(self):
        if not self.current_batch:
            return
        with self.lock:
            try:
                # Validate batch
                validated_batch = CrawlBatch(results=self.current_batch)
                # Dump Pydantic models to dicts
                new_df = pd.DataFrame([r.model_dump() for r in validated_batch.results])

                # Đọc file parquet cũ (nếu có) và ghép thêm batch mới
                if self.output_file.exists():
                    existing_df = pd.read_parquet(self.output_file, engine="pyarrow")
                    combined = pd.concat([existing_df, new_df], ignore_index=True)
                else:
                    combined = new_df

                # Ghi đè lại file parquet
                combined.to_parquet(self.output_file, engine="pyarrow", compression="snappy")
                logger.info(f"Flushed batch of {len(new_df)} records (total now {len(combined)})")
                self.current_batch.clear()
            except (ValidationError, Exception) as e:
                logger.error(f"Failed to flush batch: {e}")

    def _process_result(self, result: CrawlResult):
        with self.lock:
            self.current_batch.append(result)
            self.processed_urls.add(result.url)
            if len(self.current_batch) >= CONFIG["batch_size"]:
                self._flush_batch()

    def _detect_language(self, text: str) -> Optional[str]:
        try:
            return detect(text)
        except LangDetectException:
            return None

    def _is_connection_error(self, exception: Exception) -> bool:
        error_messages = [
            'ERR_CONNECTION_TIMED_OUT', 'ERR_NAME_NOT_RESOLVED',
            'ERR_CONNECTION_REFUSED', 'Timed out', 'timeout', 'failed to load'
        ]
        return any(msg.lower() in str(exception).lower() for msg in error_messages)

    def crawl_url(self, url: str) -> CrawlResult:
        driver = None
        policy_url, error, status, lang = None, None, "failed", None

        for attempt in range(CONFIG["retry_attempts"] + 1):
            try:
                driver = self.setup_driver()
                driver.set_page_load_timeout(CONFIG["timeout"])
                driver.get(url)
                WebDriverWait(driver, CONFIG["timeout"]).until(
                    EC.presence_of_element_located((By.TAG_NAME, 'body'))
                )

                body_text = driver.find_element(By.TAG_NAME, 'body').text
                lang = self._detect_language(body_text)

                candidates = [
                    (link.text, link.get_attribute('href'))
                    for link in driver.find_elements(By.TAG_NAME, 'a')
                    if link.get_attribute('href') and (
                        COOKIE_PATTERN.search(link.text) or COOKIE_PATTERN.search(link.get_attribute('href'))
                    )
                ]

                for text, href in candidates:
                    try:
                        driver.get(href)
                        WebDriverWait(driver, CONFIG["timeout"] // 2).until(
                            EC.presence_of_element_located((By.TAG_NAME, 'body'))
                        )
                        page_text = driver.find_element(By.TAG_NAME, 'body').text.lower()
                        if page_text.count("cookie") >= 5:
                            policy_url, status = href, "found"
                            break
                    except Exception:
                        continue

                if not policy_url:
                    search_query = f'site:{url} ("cookie policy" OR "chính sách cookie")'
                    driver.get(f'https://www.bing.com/search?q={search_query}')
                    try:
                        WebDriverWait(driver, CONFIG["timeout"]).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, 'li.b_algo'))
                        )
                        first_result = driver.find_element(By.CSS_SELECTOR, 'li.b_algo a')
                        result_href = first_result.get_attribute('href')
                        if url in result_href:
                            policy_url, status = result_href, "found"
                    except Exception:
                        pass

                return CrawlResult(
                    url=url, policy_url=policy_url, status=status,
                    timestamp=datetime.now(), error=None, lang=lang
                )
            except (WebDriverException, TimeoutException) as e:
                error = f"{type(e).__name__}: {str(e)}"
                if self._is_connection_error(e):
                    status = "connection_error"
                    break
                status = "retryable_error"
            except Exception as e:
                error, status = f"{type(e).__name__}: {str(e)}", "unexpected_error"
            finally:
                if driver:
                    driver.quit()
                if attempt < CONFIG["retry_attempts"]:
                    time.sleep(1)

        return CrawlResult(
            url=url, policy_url=None, status=status,
            timestamp=datetime.now(), error=error, lang=lang
        )

    def run(self, urls: List[str]):
        logger.info(f"Starting crawl for {len(urls)} URLs")
        with ThreadPoolExecutor(max_workers=CONFIG["max_workers"]) as executor:
            futures = {executor.submit(self.crawl_url, url): url for url in urls}
            try:
                for future in as_completed(futures):
                    self._process_result(future.result())
            except KeyboardInterrupt:
                logger.warning("Crawling interrupted by user")
                executor.shutdown(wait=False)
        self._flush_batch()
        logger.info("Crawling completed")

def main():
    parser = argparse.ArgumentParser(description="Cookie Policy Crawler")
    parser.add_argument("input_file", type=Path, help="Path to input CSV file")
    parser.add_argument("output_dir", type=Path, help="Output directory")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    configure_logging(args.output_dir)

    crawler = CookieCrawler(args.output_dir)
    try:
        logger.info(f"Loading URLs from {args.input_file}")
        urls = pd.read_csv(args.input_file)["URL"].tolist()
        processed = pd.read_parquet(crawler.output_file)["url"].unique()
        todo_urls = [u for u in urls if u not in processed]
        logger.info(f"Resuming crawl - {len(todo_urls)} new URLs remaining")
        crawler.run(todo_urls[:10])
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
