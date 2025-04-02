import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
from http.server import SimpleHTTPRequestHandler, HTTPServer
from urllib.parse import unquote, urlparse, parse_qs


df = pd.read_csv("master_football_data.csv")

def normalize_team(name):
    aliases = {
        "Real Madrid CF": "Real Madrid",
        "FC Barcelona": "Barcelona",
        "Man United": "Manchester United",
        "Man Utd": "Manchester United",
        "FC Bayern": "Bayern Munich",
        "Paris Saint-Germain": "PSG",
    }
    return aliases.get(name, name)


df["HomeTeam"] = df["HomeTeam"].apply(normalize_team)
df["AwayTeam"] = df["AwayTeam"].apply(normalize_team)
df["Date"] = pd.to_datetime(df["Date"])


def get_result(row):
    if row["HomeScore"] > row["AwayScore"]:
        return row["HomeTeam"]
    elif row["HomeScore"] < row["AwayScore"]:
        return row["AwayTeam"]
    else:
        return "Draw"


df["Winner"] = df.apply(get_result, axis=1)

# List of unique team names
teams = sorted(set(df["HomeTeam"]) | set(df["AwayTeam"]))

# Create dropdown page with GET form
option_tags = "\n".join(
    [f'<option value="{team.replace(" ", "_")}">{team}</option>' for team in teams]
)
html_dropdown = f"""
<html>
<head><title>Interactive Head-to-Head Analysis</title></head>
<body>
    <h2>Head-to-Head Team Comparison</h2>
    <form method="get" action="matchup.html">
        <label for="team1">Select Team 1:</label>
        <select name="team1">{option_tags}</select>
        <label for="team2">Select Team 2:</label>
        <select name="team2">{option_tags}</select>
        <button type="submit">View Analysis</button>
    </form>
</body>
</html>
"""

with open("index.html", "w") as f:
    f.write(html_dropdown)


class CustomHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed_url = urlparse(self.path)
        if parsed_url.path == "/matchup.html":
            params = parse_qs(parsed_url.query)
            team1 = unquote(params.get("team1", [""])[0].replace("_", " "))
            team2 = unquote(params.get("team2", [""])[0].replace("_", " "))

            h2h = df[
                ((df["HomeTeam"] == team1) & (df["AwayTeam"] == team2))
                | ((df["HomeTeam"] == team2) & (df["AwayTeam"] == team1))
            ].copy()

            if h2h.empty:
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(
                    f"<html><body><h2>No match data for {team1} vs {team2}</h2><a href='index.html'>Back</a></body></html>".encode()
                )
                return

            # Bar chart
            win_counts = h2h["Winner"].value_counts().reset_index()
            win_counts.columns = ["Team", "Wins"]
            bar_fig = px.bar(
                win_counts,
                x="Team",
                y="Wins",
                color="Team",
                title=f"{team1} vs {team2} - Total Wins",
            )
            bar_html = bar_fig.to_html(include_plotlyjs="cdn", full_html=False)

            # Line chart
            h2h_sorted = h2h.sort_values("Date")
            h2h_sorted["Counter"] = 1
            h2h_sorted["RunningWins"] = h2h_sorted.groupby("Winner")["Counter"].cumsum()
            line_fig = go.Figure()
            for team in h2h_sorted["Winner"].unique():
                if team != "Draw":
                    data = h2h_sorted[h2h_sorted["Winner"] == team]
                    line_fig.add_trace(
                        go.Scatter(
                            x=data["Date"],
                            y=data["RunningWins"],
                            mode="lines+markers",
                            name=team,
                        )
                    )
            line_fig.update_layout(
                title="Cumulative Wins Over Time",
                xaxis_title="Date",
                yaxis_title="Wins",
            )
            line_html = line_fig.to_html(include_plotlyjs="cdn", full_html=False)

            # Respond with embedded page
            full_html = f"""
            <html><head><title>{team1} vs {team2}</title></head><body>
            <h2>{team1} vs {team2} - Head-to-Head Analysis</h2>
            {bar_html}
            {line_html}
            <br><a href='index.html'>Back</a>
            </body></html>
            """

            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(full_html.encode())
        else:
            super().do_GET()


PORT = 8080
os.chdir(".")
httpd = HTTPServer(("", PORT), CustomHandler)
print(f"Serving at http://localhost:{PORT}/index.html")
httpd.serve_forever()
