# main.py
import csv
from database import DatabaseManager
from crawler import CookiePolicyCrawler

def load_urls(csv_path):
    with open(csv_path, 'r') as f:
        return [row['URL'] for row in csv.DictReader(f)]

def main():
    # input_file = "../scripts/data/crawled/combined_urls.csv"
    # urls = load_urls(input_file)
    urls = [
        "https://joyjourneys.com.vn/",
        "https://teanalabs.vn/",
        "https://www.sugartown.vn/",
        "https://fiingroup.vn/",
        "https://saigonesebaguette.vn/",
        "https://gazano.vn/",

    ]
    db_manager = DatabaseManager()
    crawler = CookiePolicyCrawler(max_workers=5)
    crawler.crawl(urls[:10], db_manager)

if __name__ == '__main__':
    main()
