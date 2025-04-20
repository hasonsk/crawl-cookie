from scripts.utils.json_util import read_json_file

def combine_cookie_data(selected_cookies_file, policies_file, output_file):
    selected_cookies_data = read_json_file(selected_cookies_file)
    policies_data = read_json_file(policies_file)

    policies_dict = {item['url']: item['cookie_policy'] for item in policies_data}

    combined_data = []

    for item in selected_cookies_data:
        url = item['url']
        combined_item = {
            'url': url,
            'selected_options': item.get('selected_options', []),
            'cookies': [cookie['name'] for cookie in item.get('cookies', [])],
            'cookie_policy': policies_dict.get(url, '')
        }
        combined_data.append(combined_item)

    with open(output_file, 'w', encoding='utf-8') as file:
        json.dump(combined_data, file, ensure_ascii=False, indent=4)
