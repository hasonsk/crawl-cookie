import pandas as pd

with open('final_results_2025-04-16.json', encoding='utf-8') as inputfile:
    df = pd.read_json(inputfile)

df.to_csv('final_results_2025-04-16.csv', encoding='utf-8', index=False)
