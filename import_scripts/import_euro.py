import sqlite3
import pandas as pd
import boto3
import requests
import base64
import os
import io

# Configuration
sqlite_url = "https://data-sources-soccerdataanalysis.s3.us-east-1.amazonaws.com/european_soccer.sqlite"
sqlite_file = "european_soccer.sqlite"
doris_fe_host = "18.223.11.133"
doris_be_host = "18.190.149.212"
doris_http_port = 8040
doris_user = "root"
doris_password = ""
doris_db = "Org_datasets"
be_api_base_url = f"http://{doris_be_host}:{doris_http_port}/api/{doris_db}"

# Download SQLite if not present
if not os.path.exists(sqlite_file):
    r = requests.get(sqlite_url)
    with open(sqlite_file, 'wb') as f:
        f.write(r.content)

# Connect to SQLite
conn = sqlite3.connect(sqlite_file)
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

# Doris Stream Load
def stream_load(table_name, df):
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False, sep='\t')
    auth_str = f"{doris_user}:{doris_password}"
    encoded_auth = base64.b64encode(auth_str.encode()).decode()
    headers = {
        'Expect': '100-continue',
        'Authorization': f'Basic {encoded_auth}',
        'label': f'{table_name}_upload',
        'column_separator': '\\t',
        'format': 'csv'
    }
    url = f"{be_api_base_url}/{table_name}/_stream_load"
    response = requests.put(url, headers=headers, data=csv_buffer.getvalue().encode('utf-8'))
    print(f"Uploaded table '{table_name}':", response.status_code, response.text[:200])

# Doris Table Creation
def create_doris_table(table_name, df):
    auth_str = f"{doris_user}:{doris_password}"
    encoded_auth = base64.b64encode(auth_str.encode()).decode()
    columns = []
    for col in df.columns:
        if pd.api.types.is_integer_dtype(df[col]):
            col_type = "INT"
        elif pd.api.types.is_float_dtype(df[col]):
            col_type = "DOUBLE"
        else:
            col_type = "STRING"
        columns.append(f"`{col}` {col_type}")
    col_def = ", ".join(columns)
    stmt = (
        f"CREATE TABLE IF NOT EXISTS {doris_db}.{table_name} "
        f"({col_def}) "
        f"DISTRIBUTED BY HASH(`{df.columns[0]}`) BUCKETS 1 "
        f"PROPERTIES('replication_num'='1');"
    )
    sql_url = f"http://{doris_fe_host}:8030/api/query/default_cluster/{doris_db}"
    headers = {
        'Authorization': f'Basic {encoded_auth}',
        'Content-Type': 'application/json'
    }
    response = requests.post(sql_url, headers=headers, json={"stmt": stmt})
    print(f"Created table '{table_name}':", response.status_code, response.text[:200])

# Process Each Table
for (table,) in tables:
    df = pd.read_sql_query(f"SELECT * FROM `{table}`", conn)
    if df.empty:
        continue
    df.columns = [c.strip().replace(" ", "_").replace("-", "_") for c in df.columns]
    create_doris_table(table, df)
    stream_load(table, df)

conn.close()