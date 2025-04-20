Dưới đây là giải thích chi tiết về các thư viện được sử dụng trong script cookie policy checker:

# How to run
```shell
python filter-v2.py -f ../data/raws/splitted-v3/urls_X_Y.csv -o ../data/crawled/check_policy/urls_X_Y -b 50 -t 15
```
Thay X và Y tương ứng từ thư mục `../data/raws/splitted-v3/`

Ví dụ

```shell
python filter-v2.py -f ../data/raws/splitted-v3/urls_120001_132000.csv -o ../data/crawled/check_policy/urls_120001_132000 -b 50 -t 15
```

### 1. asyncio
- **Mục đích**: Thư viện chuẩn của Python để viết code bất đồng bộ (asynchronous)
- **Lợi ích**: Cho phép xử lý nhiều URL cùng lúc mà không cần tạo nhiều thread
- **Chức năng chính**:
  - `asyncio.gather()`: Chạy nhiều coroutine cùng lúc và đợi tất cả hoàn thành
  - `asyncio.run()`: Chạy một coroutine bất đồng bộ và quản lý event loop

### 2. aiohttp
- **Mục đích**: Thư viện HTTP client/server bất đồng bộ
- **Lợi ích**: Thực hiện các HTTP request không chặn (non-blocking), giúp tăng hiệu suất khi cần crawl nhiều trang
- **Chức năng chính**:
  - `ClientSession`: Quản lý phiên HTTP, duy trì cookies, headers
  - `TCPConnector`: Kiểm soát số lượng kết nối đồng thời
  - `ClientTimeout`: Đặt thời gian timeout cho các request

### 3. BeautifulSoup (bs4)
- **Mục đích**: Phân tích và trích xuất dữ liệu từ HTML/XML
- **Lợi ích**: API đơn giản, dễ sử dụng để tìm và phân tích các phần tử HTML
- **Chức năng chính**:
  - `find_all()`: Tìm tất cả thẻ phù hợp với điều kiện
  - `select()`: Tìm phần tử bằng CSS selector
  - Truy cập thuộc tính và nội dung của phần tử HTML

### 4. json
- **Mục đích**: Thư viện chuẩn để đọc/ghi dữ liệu định dạng JSON
- **Lợi ích**: Giúp lưu trữ và tải dữ liệu cấu trúc
- **Chức năng chính**:
  - `json.dump()`: Ghi đối tượng Python ra file JSON
  - `json.load()`: Đọc dữ liệu JSON từ file vào đối tượng Python

### 5. os
- **Mục đích**: Thư viện chuẩn cung cấp các chức năng tương tác với hệ điều hành
- **Lợi ích**: Quản lý thư mục, đường dẫn, môi trường
- **Chức năng chính**:
  - `os.path.join()`: Kết hợp đường dẫn an toàn đa nền tảng
  - `os.makedirs()`: Tạo thư mục và các thư mục cha nếu chưa tồn tại

### 6. logging
- **Mục đích**: Thư viện chuẩn để ghi log trong Python
- **Lợi ích**: Cung cấp cơ chế ghi log linh hoạt để theo dõi tiến trình và debug
- **Chức năng chính**:
  - `basicConfig()`: Cấu hình cơ bản cho logging
  - Các cấp độ log: INFO, ERROR, WARNING

### 7. urllib.parse
- **Mục đích**: Thư viện chuẩn xử lý URL
- **Lợi ích**: Phân tích và xử lý các thành phần URL
- **Chức năng chính**:
  - `urljoin()`: Kết hợp URL cơ sở với URL tương đối để có URL tuyệt đối
  - `urlparse()`: Phân tích URL thành các thành phần (scheme, netloc, path...)

### 8. time
- **Mục đích**: Thư viện chuẩn làm việc với thời gian
- **Lợi ích**: Cung cấp các chức năng liên quan đến thời gian và độ trễ
- **Chức năng chính**:
  - `time.sleep()`: Tạm dừng thực thi trong một khoảng thời gian

### 9. typing
- **Mục đích**: Thư viện chuẩn hỗ trợ type hints trong Python
- **Lợi ích**: Giúp làm rõ kiểu dữ liệu của tham số và giá trị trả về
- **Chức năng chính**:
  - `List`, `Set`, `Tuple`, `Optional`: Các kiểu dữ liệu phức tạp

### 10. argparse
- **Mục đích**: Thư viện chuẩn để xử lý đối số dòng lệnh
- **Lợi ích**: Giúp tạo giao diện dòng lệnh chuyên nghiệp
- **Chức năng chính**:
  - `ArgumentParser`: Định nghĩa và phân tích các đối số dòng lệnh

### Sự kết hợp của các thư viện này cho phép:

1. **Xử lý đồng thời nhiều URL** (asyncio + aiohttp) - tăng tốc độ xử lý
2. **Phân tích HTML một cách hiệu quả** (BeautifulSoup) - tìm liên kết cookie policy
3. **Lưu trữ kết quả cấu trúc** (json) - dễ dàng phân tích sau này
4. **Theo dõi tiến trình** (logging) - giám sát quá trình thực thi
5. **Xử lý URL an toàn** (urllib.parse) - đảm bảo các URL được xử lý đúng định dạng

Script sử dụng lập trình bất đồng bộ qua asyncio và aiohttp, giúp tăng hiệu suất đáng kể so với phương pháp truyền thống khi cần phải xử lý hàng nghìn URL.
