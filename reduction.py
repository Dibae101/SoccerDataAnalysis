import pandas as pd

df = pd.read_csv("master_football_data.csv")  # or use pd.read_excel("your_file.xlsx")

header_like_values = ["Date", "HomeTeam", "AwayTeam", "Result"]

# Drop rows where the first 3+ columns look like header labels
df_cleaned = df[
    ~(df.iloc[:, 0].astype(str).str.strip().str.lower() == "date")
    & ~(df.iloc[:, 1].astype(str).str.strip().str.lower() == "hometeam")
    & ~(df.iloc[:, 2].astype(str).str.strip().str.lower() == "awayteam")
    & ~(df.iloc[:, 5].astype(str).str.strip().str.lower() == "result")
]

# === Reset index and export cleaned file ===
df_cleaned = df_cleaned.reset_index(drop=True)
df_cleaned.to_csv("master_football_data.csv", index=False)

print("Cleaned data saved as master football data.csv")
