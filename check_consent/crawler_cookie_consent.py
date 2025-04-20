import os
import json
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

options = webdriver.ChromeOptions()
# options.add_argument("--headless")  # Chạy ẩn trình duyệt
options.add_argument("--disable-notifications")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
rules = []

def extract_table_data(html):
    """Trích xuất dữ liệu từ các bảng HTML và chuyển thành JSON"""
    soup = BeautifulSoup(html, 'html.parser')
    tables = soup.find_all('table')
    table_data = []

    for table in tables:
        headers = [th.get_text(strip=True) for th in table.find_all('th')]
        rows = []
        for tr in table.find_all('tr')[1:]:
            cells = tr.find_all('td')
            row = {}
            for i, cell in enumerate(cells):
                if i < len(headers):
                    row[headers[i]] = cell.get_text(strip=True)
            rows.append(row)
        if rows:
            table_data.append({f"table_{idx}": rows for idx in range(len(table_data)+1)})

    return table_data

def check_matcher(driver, matcher):
    """Kiểm tra từng matcher điều kiện"""
    target = matcher['target']['selector']
    # print("Checking matcher:", target)

    try:
        element = WebDriverWait(driver, 2).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, target))
        )

        return element.is_displayed()

    except:
        return False

def check_detectors(driver, detectors):
    """Kiểm tra điều kiện phát hiện banner"""
    for detector in detectors:
        try:
            # Kiểm tra presentMatcher
            # for matcher in detector.get('presentMatcher', []):
            #     if not check_matcher(driver, matcher):
            #         return False

            # Kiểm tra showingMatcher
            for matcher in detector.get('showingMatcher', []):
                if not check_matcher(driver, matcher):
                    return False

        except:
            return False
    print("All detectors passed")
    return True

def handle_cookie_banner(driver, rules):
    """Xử lý cookie banner dựa trên rules dạng list từ Consent-O-Matic"""
    for rule in rules:
        try:
            # Lấy tên rule và config từ cấu trúc JSON
            rule_name = rule['cpm_type']
            rule_config = rule[rule_name]

            # Kiểm tra detectors
            if not check_detectors(driver, rule_config['detectors']):
                continue

            print(f"Detected {rule_name} banner")
            # execute_complex_methods(driver, rule_config['methods'])
            return rule_name

        except Exception as e:
            print(f"Error processing {rule_name}: {str(e)}")
            continue

    return None

def execute_complex_methods(driver, methods):
    """Xử lý các method phức tạp với cấu trúc lồng nhau"""
    for method in methods:
        try:
            action = method.get('action', {})
            method_type = action.get('type')
            method_name = method.get('name', '')

            # Xử lý các loại action khác nhau
            if method_type == 'list':
                handle_list_action(driver, action['actions'])

            elif method_type == 'ifcss':
                handle_ifcss_action(driver, action)

            elif method_type == 'foreach':
                handle_foreach_action(driver, action)

            elif method_name == 'SAVE_CONSENT':
                handle_save_action(
                    driver,
                    action['target']['selector']
                )

            # Thêm các loại action khác tại đây

        except Exception as e:
            print(f"Error executing method: {str(e)}")

def handle_list_action(driver, actions):
    """Xử lý action dạng list"""
    for sub_action in actions:
        execute_complex_methods(driver, [{'action': sub_action}])

def handle_ifcss_action(driver, action):
    """Xử lý action điều kiện ifcss"""
    target = action['target']
    elements = driver.find_elements(
        By.CSS_SELECTOR,
        target['selector']
    )

    if elements:
        if 'textFilter' in target:
            text_match = any(
                filter_text in element.text
                for element in elements
                for filter_text in target['textFilter']
            )
            if text_match:
                execute_complex_methods(driver, [action['trueAction']])
        else:
            execute_complex_methods(driver, [action['trueAction']])
    else:
        if 'falseAction' in action:
            execute_complex_methods(driver, [action['falseAction']])

def handle_foreach_action(driver, action):
    """Xử lý action lặp foreach"""
    elements = driver.find_elements(
        By.CSS_SELECTOR,
        action['target']['selector']
    )

    for element in elements:
        try:
            # Focus vào element hiện tại
            driver.execute_script("arguments[0].scrollIntoView();", element)
            execute_complex_methods(driver, [action['action']])
        except:
            continue

def execute_methods(driver, methods):
    """Thực thi các phương thức xử lý banner"""
    for method in methods:
        try:
            action = method.get('action', {})
            action_type = action.get('type')

            if action_type == 'click':
                handle_click_action(driver, action['target'])

            elif action_type == 'consent':
                handle_consent_action(driver, action['consents'])

            elif action_type == 'hide':
                handle_hide_action(driver, action['target'])

            elif method['name'] == 'SAVE_CONSENT':
                handle_save_action(driver)

        except Exception as e:
            print(f"Error executing method {method.get('name')}: {str(e)}")

def handle_click_action(driver, target):
    """Xử lý action click"""
    selector = target['selector']
    element = WebDriverWait(driver, 5).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
    )
    element.click()
    time.sleep(1)

def handle_consent_action(driver, consents):
    """Xử lý các consent checkbox"""
    for consent in consents:
        try:
            selector = consent['toggleAction']['target']['selector']
            checkbox = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )

            # Toggle checkbox nếu chưa được chọn
            if not checkbox.is_selected():
                checkbox.click()
                time.sleep(0.5)

        except:
            continue

def handle_hide_action(driver, target):
    """Ẩn banner nếu cần"""
    selector = target['selector']
    driver.execute_script(f"""
        document.querySelector('{selector}').style.display = 'none';
    """)

def execute_methods(driver, methods):
    """Thực thi các phương thức xử lý banner với cơ chế save động"""
    save_selector = None
    consent_actions = []

    # First pass: Tìm cấu hình save và thu thập consent
    for method in methods:
        try:
            action = method.get('action', {})

            if method['name'] == 'SAVE_CONSENT':
                save_selector = action['target']['selector']

            elif action.get('type') == 'consent':
                consent_actions.extend(action['consents'])

        except KeyError:
            continue

    # Second pass: Thực thi các action
    for method in methods:
        try:
            action = method.get('action', {})
            action_type = action.get('type')

            if action_type == 'click':
                handle_click_action(driver, action['target'])

            elif action_type == 'consent':
                handle_consent_action(driver, consent_actions)

            elif action_type == 'hide':
                handle_hide_action(driver, action['target'])

            # Xử lý save sau cùng
            if method['name'] == 'SAVE_CONSENT' and save_selector:
                handle_save_action(driver, save_selector)

        except Exception as e:
            print(f"Error executing method {method.get('name')}: {str(e)}")

def handle_save_action(driver, selector):
    """Xử lý lưu consent theo selector từ cấu hình"""
    try:
        element = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
        )
        element.click()
        print(f"Clicked save button with selector: {selector}")

        # Verify save success
        WebDriverWait(driver, 5).until(
            EC.invisibility_of_element_located((By.CSS_SELECTOR, selector))
        )
        time.sleep(1)

    except Exception as e:
        print(f"Failed to save consent: {str(e)}")
        raise

def get_cookie_data(driver, url):
    """Thu thập dữ liệu chính từ trang"""
    try:
        driver.get(url)
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))

        # Xử lý cookie banner
        cmp_type = handle_cookie_banner(driver, rules)
        time.sleep(2)  # Chờ banner đóng

        # Trích xuất toàn bộ HTML
        html_content = driver.page_source
        tables_json = extract_table_data(html_content)

        # Thu thập cookies sau tương tác
        cookies = driver.get_cookies()

        return {
            'url': url,
            'cmp_type': cmp_type,
            'html_content': html_content,
            'tables': tables_json,
            'cookies': cookies
        }

    except Exception as e:
        print(f"Error processing {url}: {str(e)}")
        return None

def get_rules(rules_folder):
  rules = []
  for file_name in os.listdir(rules_folder):
    if file_name.endswith('.json'):
      with open(os.path.join(rules_folder, file_name)) as f:
        rule_data = json.load(f)
        rule_name = os.path.splitext(file_name)[0]
        rule_data['cpm_type'] = rule_name
        rules.append(rule_data)
  return rules

rules_folder = 'Consent-O-Matic/rules'
rules = get_rules(rules_folder)

# Đọc danh sách URL
with open("urls.txt", "r") as f:
    urls = [line.strip() for line in f if line.strip()]

results = []
errors = []

for idx, url in enumerate(urls):
    print(f"Processing {idx+1}/{len(urls)}: {url}")
    try:
        result = get_cookie_data(driver, url)
        if result:
            results.append(result)
        else:
            errors.append(url)
    except Exception as e:
        errors.append(url)
        print(f"Critical error with {url}: {str(e)}")

# Lưu kết quả
with open("cookie_results.json", "w") as f:
    json.dump(results, f, indent=2)

with open("error_urls.txt", "w") as f:
    f.write("\n".join(errors))

driver.quit()
print("Crawling completed!")
