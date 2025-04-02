import sqlite3
import requests
import base64

# === CONFIG ===
sqlite_db_file = "database.sqlite"
doris_fe_host = "18.223.11.133"
doris_db_name = "soccer"
user = "root"
password = ""


def get_sqlite_tables(db_file):
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()
    return [t for t in tables if not t.startswith("sqlite_")]


def get_sqlite_table_data(db_file, table_name):
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {table_name}")
    rows = cursor.fetchall()
    cursor.execute(f"PRAGMA table_info({table_name})")
    sqlite_cols = [col[1] for col in cursor.fetchall()]
    conn.close()
    return sqlite_cols, rows


def get_doris_table_columns(table_name):
    auth = base64.b64encode(f"{user}:{password}".encode()).decode()
    headers = {"Authorization": f"Basic {auth}"}
    url = f"http://{doris_fe_host}:8030/api/{doris_db_name}"
    desc_sql = f"DESC `{table_name}`"
    res = requests.post(url, headers=headers, data={"stmt": desc_sql})
    print('Response from doris sql table ',res)
    if res.status_code != 200 or "doesn't exist" in res.text:
        return None
    lines = res.text.strip().split("\n")
    doris_cols = []
    for line in lines:
        print(f'doris line!!!!!', line)
        if line.startswith("|"):
            parts = [x.strip() for x in line.strip().split("|") if x.strip()]
            print(('lines parts---------',parts))
            if parts:
                doris_cols.append(parts[0])
    return doris_cols


def load_to_doris(matched_cols, matched_data, table_name):
    if not matched_cols or not matched_data:
        print(f"⚠️ Skipping {table_name}: no matching data to load")
        return

    auth_token = base64.b64encode(f"{user}:{password}".encode()).decode()
    stream_url = (
        f"http://{doris_fe_host}:8030/api/{doris_db_name}/{table_name}/_stream_load"
    )
    headers = {
        "Authorization": f"Basic {auth_token}",
        "Content-Type": "application/octet-stream",
    }

    header = ",".join(matched_cols) + "\n"
    rows = (
        "\n".join(
            [
                ",".join([str(val) if val is not None else "\\N" for val in row])
                for row in matched_data
            ]
        )
        + "\n"
    )
    payload = header + rows

    res = requests.post(stream_url, headers=headers, data=payload.encode("utf-8"))
    print(f"[STREAM LOAD] {table_name}: {res.status_code}")
    print(res.text)


def run():
    tables = get_sqlite_tables(sqlite_db_file)
    print(f"📦 Found {len(tables)} table(s) in SQLite")

    for table in tables:
        print(f"\n🚀 Processing table: {table}")
        sqlite_cols, data = get_sqlite_table_data(sqlite_db_file, table)
        doris_cols = get_doris_table_columns(table)

        if doris_cols is None:
            print(f"Doris table `{table}` not found, skipping...")
            continue

        # Match column names
        matched_cols = [col for col in sqlite_cols if col in doris_cols]
        matched_indexes = [sqlite_cols.index(col) for col in matched_cols]
        matched_data = [[row[i] for i in matched_indexes] for row in data]

        print(f"Matching columns: {matched_cols}")
        print(f"Rows to load: {len(matched_data)}")

        load_to_doris(matched_cols, matched_data, table)

run()
