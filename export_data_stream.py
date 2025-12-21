import pandas as pd
import json
import sys
import os

# Define the path to the Parquet file
# Assuming this script is run from the `fitsdb` directory
parquet_file_path = 'fits_data.parquet'

# If this script is called from a different directory (e.g., ../backend),
# we need to adjust the path relative to the script's location.
# Let's make it robust by resolving the absolute path of the parquet file.
script_dir = os.path.dirname(__file__)
absolute_parquet_file_path = os.path.join(script_dir, parquet_file_path)


try:
    # Read the Parquet file
    df = pd.read_parquet(absolute_parquet_file_path)

    # Stream each row as a JSON object to stdout
    # df.to_json(sys.stdout, orient='records', lines=True) would be more efficient,
    # but iterrows ensures each record is a standalone JSON object on a new line.
    # For now, let's stick to iterrows to match the previous streaming intent.
    for index, row in df.iterrows():
        json_record = row.to_json()
        sys.stdout.write(json_record + '\n')

except FileNotFoundError:
    sys.stderr.write(json.dumps({"error": f"Parquet file not found at {absolute_parquet_file_path}"}) + '\n')
    sys.exit(1)
except Exception as e:
    sys.stderr.write(json.dumps({"error": f"Error reading Parquet file: {str(e)}"}) + '\n')
    sys.exit(1)
