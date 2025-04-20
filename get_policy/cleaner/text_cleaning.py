import re
import requests
import nltk
from nltk.tokenize import word_tokenize

nltk.download('punkt')

def clean_text(text, stop_words_list):
    text = re.sub(r'<.*?>', '', text)
    text = text.lower()
    text = ' '.join(text.split()).replace("\n", " ")
    text = ' '.join(word for word in word_tokenize(text) if word not in stop_words_list)
    text = re.sub(r'\d+', '', text)
    return text

def get_stop_words(url):
    response = requests.get(url)
    return set(response.text.splitlines())
