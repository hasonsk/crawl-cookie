from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

def initialize_driver():
    options = webdriver.ChromeOptions()
    # options.add_argument('--headless')
    # options.add_argument('--no-sandbox')
    # options.add_argument("--disable-setuid-sandbox")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver

# def crawl_url(driver, url):
#     driver.get(url)
#     wait = WebDriverWait(driver, 10)
#     exist_consent = True

#     try:
#         wait.until(EC.element_to_be_clickable((By.ID, "onetrust-pc-btn-handler"))).click()
#         wait.until(EC.alert_is_present())
#         driver.switch_to.alert.accept()
#     except Exception:
#         exist_consent = False

#     checkboxes = driver.find_elements(By.CSS_SELECTOR, "input[type='checkbox']")
#     selected_options = [checkbox.get_attribute("name") for checkbox in checkboxes if checkbox.is_selected()]
#     cookies = driver.get_cookies()
#     driver.delete_all_cookies()

#     return {"url": url, "selected_options": selected_options, "cookies": cookies, "exist_consent": exist_consent}

def crawl_url(driver, url):
    driver.get(url)
    exist_consent = True

    try:
        # Wait for the page to load completely by checking for the presence of the body tag
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

        # Check if the consent button exists
        consent_button = driver.find_elements(By.ID, "onetrust-pc-btn-handler")
        if consent_button:
            exist_consent = True
            print("Consent button detected.")
        else:
            exist_consent = False
    except Exception:
        exist_consent = False

    checkboxes = driver.find_elements(By.CSS_SELECTOR, "input[type='checkbox']")
    selected_options = [checkbox.get_attribute("name") for checkbox in checkboxes if checkbox.is_selected()]
    cookies = driver.get_cookies()
    driver.delete_all_cookies()

    return {"url": url, "selected_options": selected_options, "cookies": cookies, "exist_consent": exist_consent}

def crawl_cookies(urls):
    driver = initialize_driver()
    data_list = []
    error_urls = []

    for index, url in enumerate(urls, start=1):
        try:
            print(f"Crawling URL {index}/{len(urls)}: {url}")
            data = crawl_url(driver, url)
            data_list.append(data)
            print(f"Successfully crawled URL {index}/{len(urls)}: {url}")
        except Exception as e:
            error_urls.append(url)
            print(f"Error processing URL {index}/{len(urls)}: {url} - {e}")
            continue

    driver.quit()
    print(f"Finished crawling all URLs.")
    print(f"Error URLs: {len(error_urls)}")
    with open("data/raws/error_urls.txt", "w") as f:
        for url in error_urls:
            f.write(url + "\n")
    return data_list
