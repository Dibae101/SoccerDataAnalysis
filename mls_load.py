import os
import pandas as pd
import requests
import boto3
from io import StringIO
from datetime import datetime
import base64

bucket_name = 'data-sources-soccerdataanalysis'
raw_prefix = 'MLS/'
transformed_prefix = 'transformed_MLS/'
local_dir = 'transformed_MLS'
os.makedirs(local_dir, exist_ok=True)

# Doris Config
doris_fe_host = '18.223.11.133'
doris_be_host = '18.190.149.212'
doris_fe_http_port = 8030
doris_be_http_port = 8040
doris_user = 'root'
doris_password = ''
doris_db = 'MLS_Match_History'
doris_table = 'MLS_Results'

#  boto3 S3 client
s3 = boto3.client('s3')

def parse_date(day_str, date_str):
    try:
        dt = datetime.strptime(date_str.strip(), '%B %d')
        year = 2008  # Default, or extract from filename if needed
        return dt.replace(year=year).strftime('%Y-%m-%d')
    except Exception as e:
        print(f"Date parsing error: {date_str} - {e}")
        return None

def transform_dataframe(df):
    transformed = []
    for _, row in df.iterrows():
        if len(row) < 5:
            continue
        day, date_str, home_team, score_str, away_team = row[:5]
        date = parse_date(day, date_str)
        if not date:
            continue
        try:
            home_score, away_score = map(int, score_str.strip().split('-'))
        except:
            continue
        result = 'Draw'
        if home_score > away_score:
            result = 'Home'
        elif home_score < away_score:
            result = 'Away'
        transformed.append({
            "Date": date,
            "HomeTeam": home_team.strip(),
            "AwayTeam": away_team.strip(),
            "HomeScore": home_score,
            "AwayScore": away_score,
            "Result": result
        })
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
    print(f'Create DB: {response.status_code} - {response.text}')

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
    print(f'Create Table: {response.status_code} - {response.text}')

def stream_load_to_doris(csv_path, label):
    url = f'http://{doris_be_host}:{doris_be_http_port}/api/{doris_db}/{doris_table}/_stream_load'
    auth = base64.b64encode(f'{doris_user}:{doris_password}'.encode()).decode()
    headers = {
        'Authorization': f'Basic {auth}',
        'Expect': '100-continue',
        'format': 'csv',
        'column_separator': ',',
        'label': label[:128]  
    }
    with open(csv_path, 'rb') as f:
        data = f.read()
    response = requests.put(url, headers=headers, data=data)
    print(f"Doris upload {label}: {response.status_code} - {response.text}")

# === MAIN WORKFLOW ===
def main():
    print("🔧 Creating Doris DB and Table...")
    create_doris_db()
    create_doris_table()

    print("Listing CSV files in S3...")
    files = list_csv_files()

    for key in files:
        print(f"\n Processing: {key}")
        obj = s3.get_object(Bucket=bucket_name, Key=key)

        # Decode safely
        try:
            raw_csv = obj['Body'].read().decode('utf-8')
        except UnicodeDecodeError:
            print("UTF-8 decode failed, using latin1 fallback...")
            raw_csv = obj['Body'].read().decode('latin1', errors='replace')

        # Parse DataFrame
        try:
            df = pd.read_csv(StringIO(raw_csv))
        except Exception as e:
            print(f"Skipping unreadable file: {key} - {e}")
            continue

        # Validate structure: must have exactly 5 columns, no player/metadata files
        if df.shape[1] != 5 or not set(df.columns).intersection({'day', 'date', 'home_team', 'result', 'away_team'}):
            print(f"Skipping irrelevant or malformed file: {key}")
            continue

        transformed_df = transform_dataframe(df)
        if transformed_df.empty:
            print(f"Skipping empty transformed result: {key}")
            continue

        # Save transformed CSV locally
        filename = os.path.basename(key)
        safe_label = os.path.splitext(filename)[0].replace('.', '_').replace(' ', '_')
        local_path = os.path.join(local_dir, filename)
        transformed_df.to_csv(local_path, index=False)

        # Upload to S3
        s3.upload_file(local_path, bucket_name, f'{transformed_prefix}{filename}')
        print(f"Uploaded transformed CSV to S3: {transformed_prefix}{filename}")

        # Upload to Doris
        stream_load_to_doris(local_path, safe_label)

    print("\nAll files processed successfully.")

if __name__ == '__main__':
    main()