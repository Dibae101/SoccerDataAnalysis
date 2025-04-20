import csv
import mysql.connector

config = {
    'host': '18.223.11.133',
    'port': 9030,
    'user': 'root',
    'password': '', 
    'database': 'master_football_data'
}

output_csv_path = 'cleaned_results_export.csv'

try:
    conn = mysql.connector.connect(**config)
    cursor = conn.cursor()

    # Run SELECT query
    query = "SELECT * FROM all_results"
    cursor.execute(query)

    # Fetch column names
    columns = [desc[0] for desc in cursor.description]

    # Fetch all data
    rows = cursor.fetchall()

    # Write to CSV
    with open(output_csv_path, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(columns)
        writer.writerows(rows)

    print(f"Exported to {output_csv_path}")

except Exception as e:
    print(f"Failed to export: {e}")

finally:
    if 'cursor' in locals():
        cursor.close()
    if 'conn' in locals() and conn.is_connected():
        conn.close()