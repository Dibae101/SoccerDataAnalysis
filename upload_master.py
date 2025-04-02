import pandas as pd
import requests
import base64
import boto3
from io import StringIO

# === Doris Config ===
doris_fe_host = '18.223.11.133'
doris_fe_http_port = 8030
doris_user = 'root'
doris_password = ''
doris_db = 'master_football_data'
doris_table = 'all_results'
doris_url = f'http://{doris_fe_host}:{doris_fe_http_port}/api/query/default_cluster/{doris_db}'

# === S3 Config ===
s3_bucket = 'data-sources-soccerdataanalysis'
s3_key = 'master_db/master_football_data.csv'

def fetch_from_doris():
    stmt = f"SELECT * FROM {doris_table};"
    auth = base64.b64encode(f"{doris_user}:{doris_password}".encode()).decode()
    headers = {
        "Authorization": f"Basic {auth}",
        "Content-Type": "application/json"
    }

    print("Querying Doris FE API...")
    response = requests.post(doris_url, headers=headers, json={"stmt": stmt})

    if response.status_code != 200:
        raise Exception(f"Doris query failed: {response.status_code} - {response.text}")

    result = response.json()

    # Handle the 'meta + data' style result set
    if "data" not in result or "data" not in result["data"] or "meta" not in result["data"]:
        raise Exception(f"Unexpected Doris response structure: {result}")

    rows = result["data"]["data"]
    columns = [col["name"] for col in result["data"]["meta"]]

    df = pd.DataFrame(rows, columns=columns)
    return df

def upload_to_s3(df):
    if df.empty:
        print(" DataFrame is empty. Skipping S3 upload.")
        return

    csv_buffer = StringIO()
    df.to_csv(csv_buffer, index=False)

    print(" Uploading to S3...")
    s3 = boto3.client('s3')
    s3.put_object(
        Bucket=s3_bucket,
        Key=s3_key,
        Body=csv_buffer.getvalue(),
        ContentType='text/csv'
    )
    print(f" Uploaded to s3://{s3_bucket}/{s3_key}")

def main():
    print("📥 Fetching data from Doris...")
    df = fetch_from_doris()
    print(f" Retrieved {len(df)} rows and {len(df.columns)} columns")

    upload_to_s3(df)

if __name__ == '__main__':
    main()