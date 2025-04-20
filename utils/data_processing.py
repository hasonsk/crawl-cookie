import json
import csv
def load_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)

def save_json(data, file_path):
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

def remove_duplicate_data(data):
    seen = set()
    unique_data = []
    for entry in data:
        key = (entry['url'], tuple(entry['selected_options']))
        if key not in seen:
            seen.add(key)
            unique_data.append(entry)
    return unique_data

def unique_url(data):
    seen = set()
    unique_data = []
    for entry in data:
        if entry['url'] not in seen:
            seen.add(entry['url'])
            unique_data.append(entry)
    return unique_data
