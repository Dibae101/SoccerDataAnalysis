import pandas as pd
import requests
import base64

# Config
doris_fe_host = "18.223.11.133"
doris_be_host = "18.190.149.212" 
doris_db = "Org_datasets"
table_name = "club_names"
csv_url = "https://data-sources-soccerdataanalysis.s3.us-east-1.amazonaws.com/club_names.csv"
local_csv_path = "club_names.csv"
doris_user = "root"
doris_password = ""

# Download CSV
r = requests.get(csv_url)
with open(local_csv_path, "wb") as f:
    f.write(r.content)

df = pd.read_csv(local_csv_path)
print("CSV Columns:", df.columns.tolist())

# Doris endpoints
fe_api = f"http://{doris_fe_host}:8030/api"
be_api = f"http://{doris_be_host}:8040/api"

# Helper to encode basic auth
def get_auth_header():
    token = base64.b64encode(f"{doris_user}:{doris_password}".encode()).decode()
    return {
        "Authorization": f"Basic {token}"
    }

# Step 1: Create database if not exists
def create_database():
    headers = get_auth_header()
    headers["Content-Type"] = "application/json"
    stmt = f"CREATE DATABASE IF NOT EXISTS {doris_db}"
    res = requests.post(f"{fe_api}/query/default_cluster/information_schema", headers=headers, json={"stmt": stmt})
    print("Create DB Response:", res.status_code, res.text)

# Step 2: Create table (specify types manually)
def create_table():
    headers = get_auth_header()
    headers["Content-Type"] = "application/json"
    
    # Sample schema assuming the CSV has columns like ['club_name', 'country', 'founded_year']
    stmt = f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        club_name VARCHAR(100),
        country VARCHAR(50),
        founded_year INT
    )
    DUPLICATE KEY(club_name)
    DISTRIBUTED BY HASH(club_name) BUCKETS 1
    PROPERTIES ("replication_num" = "1");
    """
    res = requests.post(f"{fe_api}/query/default_cluster/{doris_db}", headers=headers, json={"stmt": stmt})
    print("Create Table Response:", res.status_code, res.text)

# Step 3: Load data using stream load
def stream_load():
    headers = get_auth_header()
    headers.update({
        "Expect": "100-continue",
        "format": "csv",
        "column_separator": ",",
        "label": f"{table_name}_upload"
    })

    with open(local_csv_path, "rb") as f:
        res = requests.put(f"{be_api}/{doris_db}/{table_name}/_stream_load", headers=headers, data=f)
        print("Stream Load Response:", res.status_code, res.text)

def main():
    create_database()
    create_table()
    stream_load()

if __name__ == "__main__":
    main()