import pandas as pd
import plotly.graph_objs as go
import http.server
import socketserver
import threading
import os

# === Configuration ===
PORT = 8081
HTML_FILE = "match_results_graph.html"

# === Load and clean the CSV ===
df = pd.read_csv("master_football_data.csv")

df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
df.dropna(subset=["Date", "HomeTeam", "AwayTeam", "HomeScore", "AwayScore"], inplace=True)

# === Derive Result Column (Home Perspective) ===
def get_result(row):
    if row["HomeScore"] > row["AwayScore"]:
        return "Win"
    elif row["HomeScore"] < row["AwayScore"]:
        return "Loss"
    else:
        return "Draw"

df["Result"] = df.apply(get_result, axis=1)

# === Group and Summarize Data ===
summary = df.groupby(["Date", "Result"]).size().unstack(fill_value=0).reset_index()

# === Create Plotly Graph ===
trace_win = go.Scatter(x=summary["Date"], y=summary.get("Win", 0),
                       mode="lines+markers", name="Wins", line=dict(color="green"))

trace_loss = go.Scatter(x=summary["Date"], y=summary.get("Loss", 0),
                        mode="lines+markers", name="Losses", line=dict(color="red"))

trace_draw = go.Scatter(x=summary["Date"], y=summary.get("Draw", 0),
                        mode="lines+markers", name="Draws", line=dict(color="blue"))

layout = go.Layout(
    title="Home Match Outcomes Over Time",
    xaxis=dict(title="Date"),
    yaxis=dict(title="Number of Matches"),
    template="plotly_white",
)

fig = go.Figure(data=[trace_win, trace_loss, trace_draw], layout=layout)
fig.write_html(HTML_FILE)
print(f"[✓] HTML graph generated: {HTML_FILE}")

# === Serve the HTML File on Port 8081 ===
def serve_html():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))  # Serve from current dir
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", PORT), handler) as httpd:
        print(f"[✓] Serving at http://0.0.0.0:{PORT}/{HTML_FILE}")
        httpd.serve_forever()

# Start server in main thread
serve_html()