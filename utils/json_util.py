import json

def read_json_file(file_path):
    with open(file_path, 'r+', encoding='utf-8') as file:
        return json.load(file)

def save_urls_to_file(urls, output_file):
    with open(output_file, 'w', encoding='utf-8') as file:
        json.dump(list(urls), file, ensure_ascii=False, indent=4)
