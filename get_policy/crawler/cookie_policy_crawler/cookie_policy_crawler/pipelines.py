# cookie_policy_crawler/pipelines.py
import json
import os
import datetime
import logging
from itemadapter import ItemAdapter
from collections import defaultdict

logger = logging.getLogger(__name__)

class CookiePolicyPipeline:
    def __init__(self):
        self.output_dir = "../../../../../data/crawled/get_policy/group_0/urls_with_cookie_policy.csv"
        os.makedirs(self.output_dir, exist_ok=True)

        # Theo dõi số lượng theo ngôn ngữ
        self.language_stats = defaultdict(int)
        self.success_count = 0
        self.error_count = 0
        self.results_buffer = []
        self.buffer_size = 50  # Kích thước buffer trước khi ghi xuống đĩa

    def process_item(self, item, spider):
        # Chuyển đổi item thành dict nếu cần
        item_dict = ItemAdapter(item).asdict()

        # Cập nhật thống kê
        if "error" in item_dict:
            self.error_count += 1
        else:
            self.success_count += 1
            if "lang" in item_dict:
                self.language_stats[item_dict["lang"]] += 1

        # Thêm vào buffer
        self.results_buffer.append(item_dict)

        # Lưu buffer khi đạt kích thước
        if len(self.results_buffer) >= self.buffer_size:
            self._save_buffer()

        return item

    def _save_buffer(self):
        """Lưu buffer hiện tại xuống file"""
        if not self.results_buffer:
            return

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"batch_{len(self.results_buffer)}_{timestamp}.json"
        filepath = os.path.join(self.output_dir, filename)

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.results_buffer, f, ensure_ascii=False, indent=2)

            logger.info(f"Đã lưu batch gồm {len(self.results_buffer)} items vào {filepath}")
            # Làm trống buffer
            self.results_buffer = []
        except Exception as e:
            logger.error(f"Lỗi khi lưu batch: {e}")

    def close_spider(self, spider):
        """Xử lý khi spider kết thúc"""
        # Lưu buffer cuối cùng nếu có
        if self.results_buffer:
            self._save_buffer()

        # Tạo báo cáo tổng hợp
        summary = {
            "crawl_stats": {
                "total_processed": self.success_count + self.error_count,
                "successful": self.success_count,
                "failed": self.error_count,
                "success_rate": round((self.success_count / (self.success_count + self.error_count or 1)) * 100, 2)
            },
            "language_stats": dict(self.language_stats),
            "timestamp": datetime.datetime.now().isoformat()
        }

        # Lưu báo cáo
        summary_file = os.path.join(self.output_dir, f"crawl_summary_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        logger.info(f"Crawl hoàn tất. Báo cáo tổng hợp lưu tại {summary_file}")
        logger.info(f"Thống kê: {self.success_count} thành công, {self.error_count} thất bại")
        logger.info(f"Phân bố ngôn ngữ: {dict(self.language_stats)}")

# python run_crawler.py --urls-file data/crawled/all_urls_policy-v2.csv
# crawl-cookie/data/crawled/check_policy/group_0/urls_with_cookie_policy.csv
