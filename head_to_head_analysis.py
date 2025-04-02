import pandas as pd

df = pd.read_csv("master_football_data.csv")

TEAM_ALIASES = {
    "Real Madrid": ["Real Madrid", "Real Madrid CF", "RM"],
    "Barcelona": ["Barcelona", "FC Barcelona", "Barça"],
    "Manchester United": ["Manchester United", "Man United", "Man Utd"],
    "Bayern Munich": ["Bayern Munich", "FC Bayern"],
    "PSG": ["PSG", "Paris Saint-Germain"],
    # Add more as needed
}

# Normalize names in dataset using reverse alias lookup
alias_lookup = {}
for canonical, aliases in TEAM_ALIASES.items():
    for name in aliases:
        alias_lookup[name.lower()] = canonical

def normalize_team_name(name):
    return alias_lookup.get(name.lower(), name)

df["HomeTeam"] = df["HomeTeam"].apply(normalize_team_name)
df["AwayTeam"] = df["AwayTeam"].apply(normalize_team_name)

# Head to head analysis
def head_to_head_analysis(team1, team2):
    team1 = normalize_team_name(team1)
    team2 = normalize_team_name(team2)
    # Filter matches where these two teams played each other
    h2h = df[
        ((df["HomeTeam"] == team1) & (df["AwayTeam"] == team2))
        | ((df["HomeTeam"] == team2) & (df["AwayTeam"] == team1))
    ].copy()

    if h2h.empty:
        print(f"No matches found between {team1} and {team2}")
        return

    # Determine winner for display
    def outcome(row):
        if row["Result"] == "Home":
            return row["HomeTeam"]
        elif row["Result"] == "Away":
            return row["AwayTeam"]
        else:
            return "Draw"

    h2h["Winner"] = h2h.apply(outcome, axis=1)
    h2h["Score"] = h2h["HomeScore"].astype(str) + " - " + h2h["AwayScore"].astype(str)

    print(f"\n🔍 Head-to-Head: {team1} vs {team2}")
    print(f"Total Matches: {len(h2h)}")

    # Result summary
    result_counts = h2h["Winner"].value_counts()
    print("\nWin Summary:")
    for team, count in result_counts.items():
        print(f"{team}: {count} wins")

    print("\nMatch History:")
    print(
        h2h[["Date", "HomeTeam", "AwayTeam", "Score", "Winner"]].sort_values(by="Date")
    )

head_to_head_analysis("Real Madrid", "FC Barcelona")
