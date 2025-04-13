# Hướng dẫn chạy chương trình thu thập các trang web chứa chính sách cookie

## Setup

Trước khi chạy chương trình, bạn cần đảm bảo đã cài đặt các thư viện sau:
```
pip install selenium webdriver-manager
```

## Chuẩn bị dữ liệu đầu vào

## Chạy chương trình

    ```bash
    python filter-v1.py --folder urls_12001_24000
    ```


## Kết quả

Sau khi chương trình hoàn thành (hoặc bị dừng), kết quả sẽ được lưu vào các file CSV trong thư mục `data/crawled/urls_12001_24000/`:

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
