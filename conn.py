import sqlite3
import pandas as pd

# Connect to SQLite
db_file = "database.sqlite"
conn = sqlite3.connect(db_file)
cursor = conn.cursor()

# Get all table names from SQLite
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

# convert SQLite types to Doris types
def convert_sqlite_type(sqlite_type, is_first_column=False):
    sqlite_type = sqlite_type.upper()

    if "INT" in sqlite_type:
        return "BIGINT"
    elif "CHAR" in sqlite_type or "TEXT" in sqlite_type:
        return "VARCHAR"  
    elif "REAL" in sqlite_type or "DOUBLE" in sqlite_type or "FLOAT" in sqlite_type:
        if is_first_column:
            return "DECIMAL(18,2)"  
        else:
            return "DOUBLE"
    elif "BLOB" in sqlite_type:
        return "LARGE_OBJECT"
    else:
        return "VARCHAR"  


for table_name in tables:
    table = table_name[0]
    schema_query = f"PRAGMA table_info({table})"
    df_schema = pd.read_sql_query(schema_query, conn)

    column_defs = []
    for _, row in df_schema.iterrows():
        col_name = row["name"]
        col_type = convert_sqlite_type(row["type"])
        column_defs.append(f"{col_name} {col_type}")

    # Set the first column as the distribution key
    distribution_key = df_schema.iloc[0]["name"]

    create_table_sql = f"""
    CREATE TABLE IF NOT EXISTS {table} (
        {", ".join(column_defs)}
    ) ENGINE=OLAP
    DISTRIBUTED BY HASH({distribution_key}) BUCKETS 10
    PROPERTIES ("replication_num" = "1");
    """

    print(f"Run this in Doris:\n{create_table_sql}\n")

conn.close()
