import sqlite3
import pandas as pd


sqlite_path = "euro_soccer_db.sqlite"  
output_csv = "transformed_euro_matches.csv"

conn = sqlite3.connect(sqlite_path)

# Load match data with only required columns
matches_df = pd.read_sql_query(
    """
    SELECT 
        date,
        home_team_api_id,
        away_team_api_id,
        home_team_goal,
        away_team_goal
    FROM Match
""",
    conn,
)

# Load team mapping: team_api_id → club_name
club_df = pd.read_sql_query(
    "SELECT team_api_id, team_long_name AS club_name FROM Team", conn
)
conn.close()

# Mapping dict
team_id_to_name = dict(zip(club_df["team_api_id"], club_df["club_name"]))   

matches_df["HomeTeam"] = matches_df["home_team_api_id"].map(team_id_to_name)
matches_df["AwayTeam"] = matches_df["away_team_api_id"].map(team_id_to_name)

matches_df["Date"] = pd.to_datetime(matches_df["date"]).dt.date     # Date format

matches_df["HomeScore"] = matches_df["home_team_goal"]
matches_df["AwayScore"] = matches_df["away_team_goal"]


# Based on score determine result
def get_result(row):
    if row["HomeScore"] > row["AwayScore"]:
        return "Home"
    elif row["HomeScore"] < row["AwayScore"]:
        return "Away"
    else:
        return "Draw"


matches_df["Result"] = matches_df.apply(get_result, axis=1)

final_df = matches_df[
    ["Date", "HomeTeam", "AwayTeam", "HomeScore", "AwayScore", "Result"]
]

final_df = final_df.dropna(subset=["HomeTeam", "AwayTeam"])

def clean_club_names_trim_after_comma(df):
    for col in ["HomeTeam", "AwayTeam"]:
        df[col] = df[col].apply(lambda x: x.split(",")[0] if isinstance(x, str) else x)
    return df

# Export to CSV
final_df = clean_club_names_trim_after_comma(final_df)
final_df.to_csv(output_csv, index=False)
print(f"Transformed data saved to: {output_csv}")
