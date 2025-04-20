# Di chuyển vào thư mục
`cd cookie_policy_crawler`

# Hưỡng dẫn chạy
```python
python run_crawler.py --urls-file ../../../../data/crawled/check_policy/group_0/urls_with_cookie_policy.csv
```

## Tùy chỉnh các tham số khác
```python
python run_crawler.py --urls-file data/crawled/all_urls_policy-v2.csv --concurrent 8 --delay 1.0 --log-level DEBUG
```
