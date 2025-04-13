[# Hướng dẫn chạy chương trình thu thập các trang web chứa chính sách cookie

## Setup

Trước khi chạy chương trình, bạn cần đảm bảo đã cài đặt các thư viện sau:

* **Python 3:** Chương trình được viết bằng Python 3. Hãy chắc chắn rằng bạn đã cài đặt phiên bản này trên hệ thống của mình.
* **Selenium:** Thư viện để tương tác với trình duyệt web.
* **WebDriver Manager:** Công cụ để tự động quản lý trình điều khiển (driver) cho trình duyệt Chrome.

Bạn có thể cài đặt các thư viện này bằng pip:

```bash
pip install selenium webdriver-manager
```

## Chuẩn bị dữ liệu đầu vào

## Chạy chương trình

1.  **Đảm bảo đã chuẩn bị file đầu vào:** Kiểm tra hoặc tạo file `data/crawled/combined_urls.csv` với danh sách các URL cần kiểm tra. Nếu bạn muốn lọc URL, hãy đảm bảo file `data/raws/cleaned_urls.csv` tồn tại.
2.  **Mở terminal hoặc command prompt:** Di chuyển đến thư mục chứa file script Python của bạn.
3.  **Thực thi script Python**:

    ```bash
    python filter.py
    ```


## Kết quả

Sau khi chương trình hoàn thành (hoặc bị dừng), kết quả sẽ được lưu vào các file CSV trong thư mục `data/crawled/`:

* `urls_with_cookie_policy.csv`: Chứa danh sách các URL mà chương trình đã tìm thấy chính sách cookie, cùng với URL của chính sách đó.
* `urls_without_cookie_policy.csv`: Chứa danh sách các URL mà chương trình không tìm thấy chính sách cookie.
* `urls_cannot_reach.csv`: Chứa danh sách các URL mà chương trình không thể truy cập do lỗi kết nối hoặc timeout.

Mỗi lần chạy, chương trình sẽ ghi thêm dữ liệu vào các file này (chế độ append).


## Theo dõi tiến trình

Trong quá trình chạy, chương trình sẽ hiển thị thông tin tiến trình và các lỗi (nếu có) trên terminal. Thông tin này bao gồm:

* Thời gian và mức độ log (INFO, WARNING, ERROR).
* URL hiện tại đang được xử lý.
* Thông báo khi tìm thấy chính sách cookie.
* Thông báo lỗi kết nối hoặc lỗi khác khi truy cập URL.
* Thông báo khi lưu kết quả định kỳ.
* Tổng số URL đã xử lý.
](https://github.com/hasonsk/crawl-cookie/edit/main/README.md)
