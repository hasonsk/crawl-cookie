import re
import gc
import logging
from bs4 import BeautifulSoup
from lingua import LanguageDetectorBuilder
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import WebDriverException, TimeoutException
from boilerpy3 import extractors
from concurrent.futures import ThreadPoolExecutor, as_completed
from database import DatabaseManager

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

TIMEOUT = 15

class CookiePolicyCrawler:
    def __init__(self, max_workers=3):
        self.max_workers = max_workers
        self.detector = LanguageDetectorBuilder.from_all_languages().build()
        self.service = Service(ChromeDriverManager().install())
        self.driver_options = self._configure_driver()
        self.cookie_pattern = re.compile(
            r'chính sách cookie|cookie policy|cookies|cookie policy của chúng tôi|'
            r'thông báo về cookie|chính sách quyền riêng tư và cookie|'
            r'chính sách bảo mật và cookie|cookie settings|cookie preferences',
            re.IGNORECASE
        )
        logging.info(f"Khởi tạo trình thu thập với tối đa {max_workers} worker.")

    def _configure_driver(self):
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--blink-settings=imagesEnabled=false")
        options.add_argument("--log-level=3")  # Suppress console logs
        return options

    def _get_driver(self):
        return webdriver.Chrome(
            service=self.service,
            options=self.driver_options
        )

    def _find_policy_url(self, driver, base_url):
        try:
            driver.get(base_url)
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, 'body'))
            )

            all_links = driver.find_elements(By.TAG_NAME, 'a')
            candidate_links = [
                (link.text, link.get_attribute('href'))
                for link in all_links
                if link.get_attribute('href')
            ]

            for text, href in candidate_links:
                if self.cookie_pattern.search(text) or self.cookie_pattern.search(href):
                    try:
                        driver.get(href)
                        WebDriverWait(driver, TIMEOUT // 2).until(
                            EC.presence_of_element_located((By.TAG_NAME, 'body')))
                        body_text = driver.find_element(By.TAG_NAME, 'body').text.lower()
                        if body_text.count("cookie") > 5:
                            return href
                    except Exception:
                        continue

            search_query = f"site:{base_url} (Cookie policy OR chính sách cookie)"
            driver.get(f"https://www.google.com/search?q={search_query}")
            try:
                WebDriverWait(driver, TIMEOUT).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'div.g')))
                first_result = driver.find_element(By.CSS_SELECTOR, 'div.g a')
                first_result_url = first_result.get_attribute('href')
                if base_url in first_result_url:
                    return first_result_url
            except Exception:
                pass

            return None

        except (WebDriverException, TimeoutException):
            return None
        except Exception:
            return None
        finally:
            if driver:
                driver.quit()

    def _extract_content(self, html):
        try:
            extractor = extractors.ArticleExtractor()
            return extractor.get_content(html).text
        except Exception:
            soup = BeautifulSoup(html, 'lxml')
            for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'form', 'iframe', 'aside']):
                tag.decompose()
            return soup.get_text(separator=' ', strip=True)

    def _detect_language(self, text):
        if len(text) > 100:
            return self.detector.detect_language_of(text).name
        return None

    def _extract_tables(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        tables_data = [
            {
                'headers': [th.get_text(strip=True) for th in table.find_all('th')],
                'rows': [
                    [td.get_text(strip=True) for td in tr.find_all('td')]
                    for tr in table.find_all('tr')[1:]
                ]
            }
            for table in soup.find_all('table')
            if len(table.find_all('tr')) > 1
        ]
        return tables_data

    def process_site(self, base_url):
        driver = self._get_driver()
        try:
            policy_url = self._find_policy_url(driver, base_url)
            if not policy_url:
                return { 'base_url': base_url, 'policy_url': policy_url, 'content': None, 'language': None, 'tables': None, 'raw_html': None}

            driver.get(policy_url)
            html = driver.page_source

            return {
                'base_url': base_url,
                'policy_url': policy_url,
                'content': self._extract_content(html),
                'language': self._detect_language(html),
                'tables': self._extract_tables(html),
                'raw_html': html
            }
        except (WebDriverException, TimeoutException):
            return { 'base_url': base_url, 'policy_url': None, 'content': None, 'language': None, 'tables': None, 'raw_html': None}
        except Exception:
            return { 'base_url': base_url, 'policy_url': None, 'content': None, 'language': None, 'tables': None, 'raw_html': None}
        finally:
            driver.quit()
            gc.collect()

    def crawl(self, urls, db_manager):
        logging.info(f"Bắt đầu thu thập thông tin từ {len(urls)} URL.")
        results = []
        processed_count = 0
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(self.process_site, url): url for url in urls}

            for future in as_completed(futures):
                url = futures[future]
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                        processed_count += 1

                    if processed_count % 100 == 0 and processed_count > 0:
                        db_manager.save_policies(results)
                        results = []

                except Exception:
                    pass

        if results:
            db_manager.save_policies(results)
        logging.info(f"Đã hoàn thành thu thập {processed_count} URL.")

    def _is_connection_error(self, e):
        return "net::ERR_" in str(e) or "socket hang up" in str(e).lower()
