import pandas as pd
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv
import json

# --- Database Configuration ---
load_dotenv()
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

print("Starting data export...")
try:
    engine = create_engine(DATABASE_URL)
    with engine.connect() as connection:
        # Corrected table name from 'fits_file' to 'fits_files'
        df = pd.read_sql_table('fits_files', connection) 
    
    # Parquet doesn't support JSONB directly. Convert to a valid JSON string.
    if 'header_dump' in df.columns:
        df['header_dump'] = df['header_dump'].apply(json.dumps)

    # Convert any timezone-aware datetime columns to timezone-naive
    # This avoids potential issues when reading the parquet file in different environments
    for col in df.select_dtypes(include=['datetimetz']).columns:
        df[col] = df[col].dt.tz_localize(None)
        
    # Export the dataframe to a parquet file
    df.to_parquet('fits_data.parquet', index=False, version='1.0')
    
    print(f"Successfully exported {len(df)} rows to fits_data.parquet")
    print("You can now modify 'app.py' to read from this file instead of the database.")

except Exception as e:
    print(f"An error occurred during export: {e}")
    print("Please ensure your .env file is correctly configured and the database is running.")
