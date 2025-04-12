import os
import pandas as pd

DATASET_DIR = "data/crawled/dataset_5_800_000"
OUTPUT_DIR = "data/crawled/splitted-v3"

os.makedirs(OUTPUT_DIR, exist_ok=True)

subdirs = [
  os.path.join(DATASET_DIR, d)
  for d in os.listdir(DATASET_DIR)
  if os.path.isdir(os.path.join(DATASET_DIR, d))
]

# Initialize an empty DataFrame to store all URLs
all_urls_df = pd.DataFrame()
all_urls_df = pd.read_csv('data/crawled/combined_urls.csv')
print(len(all_urls_df))


# # Read and combine all CSV files into a single DataFrame
# for subdir in subdirs:
#   csv_files = [
#     os.path.join(subdir, f)
#     for f in os.listdir(subdir)
#     if f.endswith('.csv')
#   ]

#   for csv_file in csv_files:
#     # Read the CSV file
#     df = pd.read_csv(csv_file)

#     # Filter out rows where 'root_page' contains '.vn/'
#     filtered_df = df[~df['root_page'].str.contains(r'\.vn/', na=False)]

#     # Append the filtered DataFrame to the combined DataFrame
#     all_urls_df = pd.concat([all_urls_df, filtered_df], ignore_index=True)

# Split the combined DataFrame into chunks of 12000 rows
for chunk_start in range(0, len(all_urls_df), 12000):
  chunk_end = min(chunk_start + 12000, len(all_urls_df))
  chunk_df = all_urls_df.iloc[chunk_start:chunk_end]
  output_file = os.path.join(
    OUTPUT_DIR, f"urls_{chunk_start + 1}_{chunk_end}.csv"
  )
  chunk_df.to_csv(output_file, index=False)

  print(f"Processed chunk {chunk_start + 1} to {chunk_end} and saved to {output_file}")

# all_urls_df.to_csv('all_urls.csv', index=False)
