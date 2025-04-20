import pandas as pd
import dash
from dash import dcc, html, Input, Output
import plotly.graph_objects as go

# Load and clean the CSV
df = pd.read_csv("master_football_data.csv")

df["Date"] = pd.to_datetime(df["Date"], format="%Y-%m-%d", errors="coerce")
df = df.dropna(subset=["Date"])

df["Year"] = df["Date"].dt.year

# Set up Dash app
app = dash.Dash(__name__)
server = app.server  

years = sorted(df["Year"].dropna().unique())

app.layout = html.Div([
    html.H1("Football Match Results Timeline"),
    html.Div([
        html.Label("Select Start Year:"),
        dcc.Dropdown(
            id="start-year",
            options=[{"label": str(year), "value": year} for year in years],
            value=years[0]
        )
    ], style={"width": "48%", "display": "inline-block"}),

    html.Div([
        html.Label("Select End Year:"),
        dcc.Dropdown(
            id="end-year",
            options=[{"label": str(year), "value": year} for year in years],
            value=years[-1]
        )
    ], style={"width": "48%", "display": "inline-block"}),

    dcc.Graph(id="timeline-graph")
])

@app.callback(
    Output("timeline-graph", "figure"),
    Input("start-year", "value"),
    Input("end-year", "value")
)
def update_graph(start_year, end_year):
    filtered = df[(df["Year"] >= start_year) & (df["Year"] <= end_year)]

    grouped = filtered.groupby(["Date", "Result"]).size().unstack(fill_value=0).reset_index()

    fig = go.Figure()

    if "Home" in grouped:
        fig.add_trace(go.Scatter(
            x=grouped["Date"], y=grouped["Home"],
            mode="lines+markers", name="Home Win",
            line=dict(color="green")
        ))

    if "Away" in grouped:
        fig.add_trace(go.Scatter(
            x=grouped["Date"], y=grouped["Away"],
            mode="lines+markers", name="Away Win",
            line=dict(color="red")
        ))

    if "Draw" in grouped:
        fig.add_trace(go.Scatter(
            x=grouped["Date"], y=grouped["Draw"],
            mode="lines+markers", name="Draw",
            line=dict(color="blue")
        ))

    fig.update_layout(
        title=f"Match Results from {start_year} to {end_year}",
        xaxis_title="Match Date",
        yaxis_title="Number of Matches",
        hovermode="x unified",
        template="plotly_white"
    )

    return fig

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)