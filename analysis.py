import pandas as pd

df = pd.read_csv("master_football_data.csv")

# HOME TEAM ANALYSIS
home_stats = df.groupby("HomeTeam").agg(
    home_games=("HomeTeam", "count"),
    home_wins=("Result", lambda x: (x == "Home").sum()),
    home_draws=("Result", lambda x: (x == "Draw").sum()),
    home_losses=("Result", lambda x: (x == "Away").sum()),
)
home_stats["home_win_rate"] = home_stats["home_wins"] / home_stats["home_games"]
home_stats["home_loss_rate"] = home_stats["home_losses"] / home_stats["home_games"]


# AWAY TEAM ANALYSIS
away_stats = df.groupby("AwayTeam").agg(
    away_games=("AwayTeam", "count"),
    away_wins=("Result", lambda x: (x == "Away").sum()),
    away_draws=("Result", lambda x: (x == "Draw").sum()),
    away_losses=("Result", lambda x: (x == "Home").sum()),
)
away_stats["away_win_rate"] = away_stats["away_wins"] / away_stats["away_games"]
away_stats["away_loss_rate"] = away_stats["away_losses"] / away_stats["away_games"]

# Merge stats
team_stats = home_stats.merge(
    away_stats, left_index=True, right_index=True, how="outer"
).fillna(0)

# Compute overall totals
team_stats["total_games"] = team_stats["home_games"] + team_stats["away_games"]
team_stats["total_wins"] = team_stats["home_wins"] + team_stats["away_wins"]
team_stats["total_losses"] = team_stats["home_losses"] + team_stats["away_losses"]
team_stats["total_draws"] = team_stats["home_draws"] + team_stats["away_draws"]
team_stats["overall_win_rate"] = team_stats["total_wins"] / team_stats["total_games"]
team_stats["overall_loss_rate"] = team_stats["total_losses"] / team_stats["total_games"]

# Sort by overall win rate
team_stats = team_stats.sort_values(by="overall_win_rate", ascending=False)

print('print top 10 teams', team_stats.head(10))
team_stats.to_csv("team_home_away_analysis.csv")
print("Saved to team_home_away_analysis.csv")
