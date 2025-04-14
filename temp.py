import pandas as pd
df = pd.read_parquet('data/crawled/filtered/urls_360001_48000crawl_results.parquet')

print(df.status)
