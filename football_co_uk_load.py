import os
import pandas as pd
import requests
import boto3
from io import StringIO
from datetime import datetime
import base64
import re

bucket_name = 'data-sources-soccerdataanalysis'
raw_prefix = 'football-data.co.uk/'
doris_db = 'football_co_uk'
doris_table = 'football_co_Results'
transformed_prefix = f'{doris_db}/'
local_dir = doris_db
os.makedirs(local_dir, exist_ok=True)

# Doris Config
doris_fe_host = '18.223.11.133'
doris_be_host = '18.190.149.212'
doris_fe_http_port = 8030
doris_be_http_port = 8040
doris_user = 'root'
doris_password = ''

#  boto3 S3 client
s3 = boto3.client('s3')

def sanitize_label(label):
    return re.sub(r'[^a-zA-Z0-9_\-]', '_', label)

def safe_format_date(value):
    try:
        if pd.isna(value):
            return None
        return datetime.strptime(str(value), '%d/%m/%y').strftime('%Y-%m-%d')
    except Exception:
        return None

def transform_ftr_dataframe(df):
    transformed = []
    for _, row in df.iterrows():
        date = safe_format_date(row.get('Date'))
        if not date:
            continue
        try:
            home_team = str(row['HomeTeam']).strip()
            away_team = str(row['AwayTeam']).strip()
            home_score = int(row['FTHG'])
            away_score = int(row['FTAG'])
            ftr = str(row['FTR']).strip().upper()

            result = 'Draw'
            if ftr == 'H':
                result = 'Home'
            elif ftr == 'A':
                result = 'Away'

            transformed.append({
                "Date": date,
                "HomeTeam": home_team,
                "AwayTeam": away_team,
                "HomeScore": home_score,
                "AwayScore": away_score,
                "Result": result
            })
        except Exception as e:
            print(f"⚠️ Row transformation error: {e}")
            continue
    return pd.DataFrame(transformed)

def list_csv_files():
    paginator = s3.get_paginator('list_objects_v2')
    page_iterator = paginator.paginate(Bucket=bucket_name, Prefix=raw_prefix)
    files = []
    for page in page_iterator:
        for obj in page.get('Contents', []):
            key = obj['Key']
            if key.endswith('.csv'):
                files.append(key)
    return files

def create_doris_db():
    url = f'http://{doris_fe_host}:{doris_fe_http_port}/api/query/default_cluster/information_schema'
    auth = base64.b64encode(f'{doris_user}:{doris_password}'.encode()).decode()
    headers = {'Authorization': f'Basic {auth}', 'Content-Type': 'application/json'}
    stmt = f'CREATE DATABASE IF NOT EXISTS {doris_db}'
    response = requests.post(url, headers=headers, json={"stmt": stmt})
    print(f'Doris DB creation: {response.status_code} - {response.text}')

def create_doris_table():
    url = f'http://{doris_fe_host}:{doris_fe_http_port}/api/query/default_cluster/{doris_db}'
    auth = base64.b64encode(f'{doris_user}:{doris_password}'.encode()).decode()
    headers = {'Authorization': f'Basic {auth}', 'Content-Type': 'application/json'}
    stmt = f'''
        CREATE TABLE IF NOT EXISTS {doris_table} (
            Date VARCHAR,
            HomeTeam STRING,
            AwayTeam STRING,
            HomeScore INT,
            AwayScore INT,
            Result STRING
        )
        DISTRIBUTED BY HASH(Date) BUCKETS 1
        PROPERTIES("replication_num" = "1");
    '''
    response = requests.post(url, headers=headers, json={"stmt": stmt})
    print(f'Doris Table creation: {response.status_code} - {response.text}')

def stream_load_to_doris(csv_path, label):
    url = f'http://{doris_be_host}:{doris_be_http_port}/api/{doris_db}/{doris_table}/_stream_load'
    auth = base64.b64encode(f'{doris_user}:{doris_password}'.encode()).decode()
    headers = {
        'Authorization': f'Basic {auth}',
        'Expect': '100-continue',
        'format': 'csv',
        'column_separator': ',',
        'label': sanitize_label(label)[:128]
    }
    with open(csv_path, 'rb') as f:
        data = f.read()
    response = requests.put(url, headers=headers, data=data)
    print(f"Doris upload {label}: {response.status_code} - {response.text}")

# === main function ===
def main():
    print("🔧 Setting up Doris...")
    create_doris_db()
    create_doris_table()

    print("Listing FTR-format CSV files in S3...")
    files = list_csv_files()

    for key in files:
        print(f"\n Processing: {key}")
        obj = s3.get_object(Bucket=bucket_name, Key=key)

        # Decode safely
        try:
            raw_csv = obj['Body'].read().decode('utf-8')
        except UnicodeDecodeError:
            print(" UTF-8 decode failed, using latin1 fallback...")
            raw_csv = obj['Body'].read().decode('latin1', errors='replace')

        try:
            df = pd.read_csv(StringIO(raw_csv))
        except Exception as e:
            print(f"Skipping unreadable file: {key} - {e}")
            continue

        expected_cols = {'Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG', 'FTR'}
        if not expected_cols.issubset(set(df.columns)):
            print(f"Skipping file with unexpected structure: {key}")
            continue

        transformed_df = transform_ftr_dataframe(df)
        if transformed_df.empty:
            print(f"Skipping empty transformed result: {key}")
            continue

        filename = os.path.basename(key)
        safe_label = sanitize_label(os.path.splitext(filename)[0])
        local_path = os.path.join(local_dir, filename)
        transformed_df.to_csv(local_path, index=False)

        # Upload to S3 
        s3.upload_file(local_path, bucket_name, f'{transformed_prefix}{filename}')
        print(f" Uploaded to S3: {transformed_prefix}{filename}")

        # Upload to Doris
        stream_load_to_doris(local_path, safe_label)

    print("\n All FTR-format files processed successfully.")

if __name__ == '__main__':
    main()