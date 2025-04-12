import sqlite3
import json
from contextlib import contextmanager
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class DatabaseManager:
    def __init__(self, db_path='cookie_policies.db'):
        self.db_path = db_path
        self._init_db()
        logging.info(f"Khởi tạo DatabaseManager với đường dẫn: {db_path}")

    def _init_db(self):
        with self.connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS policies (
                    base_url TEXT PRIMARY KEY,
                    policy_url TEXT,
                    content TEXT,
                    language TEXT,
                    tables_json TEXT,
                    raw_html TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_lang ON policies(language)')
            logging.info("Đã kiểm tra và tạo bảng 'policies' (nếu chưa tồn tại).")

    @contextmanager
    def connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute('PRAGMA journal_mode = WAL')
        try:
            yield conn
        finally:
            conn.close()
            logging.debug("Đã đóng kết nối database.")

    def save_policy(self, conn, data):
        conn.execute('''
            INSERT OR REPLACE INTO policies
            (base_url, policy_url, content, language, tables_json, raw_html)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            data['base_url'],
            data['policy_url'],
            data['content'],
            data['language'],
            json.dumps(data['tables']),
            data['raw_html']
        ))
        logging.debug(f"Đã lưu/cập nhật chính sách cho: {data['base_url']}")

    def save_policies(self, policies_data):
        """Lưu một danh sách các chính sách vào database."""
        if not policies_data:
            logging.info("Không có dữ liệu chính sách nào để lưu.")
            return

        with self.connection() as conn:
            cursor = conn.cursor()
            for data in policies_data:
                try:
                    cursor.execute('''
                        INSERT OR REPLACE INTO policies
                        (base_url, policy_url, content, language, tables_json, raw_html)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        data['base_url'],
                        data['policy_url'],
                        data['content'],
                        data['language'],
                        json.dumps(data['tables']),
                        data['raw_html']
                    ))
                    logging.debug(f"Đã lưu/cập nhật chính sách cho: {data['base_url']}")
                except sqlite3.Error as e:
                    logging.error(f"Lỗi khi lưu chính sách cho {data['base_url']}: {e}")
            conn.commit()
            logging.info(f"Đã lưu thành công {len(policies_data)} chính sách vào database.")
