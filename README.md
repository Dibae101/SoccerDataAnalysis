# ⚽ Soccer Data ETL & Analytics Pipeline using Apache Doris

## 📌 Overview

This project demonstrates an end-to-end ETL pipeline that extracts soccer data from various sources, transforms, loads it into [Apache Doris](https://doris.apache.org/), and visualizes insights through interactive dashboards.

---

## 🧩 Data Sources

- **Kaggle Soccer SQLite DB**  
  https://www.kaggle.com/datasets/hugomathien/soccer/data  
  *(Uploaded to S3 as `database.sqlite`)*

- **Football.co.uk CSVs**  
  https://football-data.co.uk/

- **GitHub UEFA JSON Player Data**  
  https://github.com/jokecamp/FootballData

- **MLS Match Data**  
  https://data-sources-soccerdataanalysis.s3.us-east-1.amazonaws.com/MLS/

---

## 🖥 Apache Doris Setup

### ✅ Frontend Setup

- Updated `limits.conf`, disabled swap
- Installed Java JDK, Python, GCC
- Edited `fe.conf` for `meta_dir` and `priority_networks`
- Started Doris Frontend  
  → `http://<FE_IP>:8030` (user: `root`, password: blank)

### ✅ Backend Setup

- Configured `JAVA_HOME`, `priority_networks`, `storage_root_path`
- Created `disk1` and `disk2` for data storage
- Set `ulimit`, `vm.max_map_count`
- Started Doris Backend
- Registered BE node to Doris FE:
  ```sql
  ALTER SYSTEM ADD BACKEND "<BE_PRIVATE_IP>:9050";
  ```

---

## 📦 ETL Process

### ✅ Extract
- Loaded SQLite DB from S3
- Recursively scanned and filtered CSVs from:
  - `FootballData-master/`
  - `github_sourced_data/`
  - `MLS/` 

### ✅ Transform
- Cleaned columns (removed “Cross”/XML-like noise)
- Fuzzy-matched columns to standard schema:
  ```
  ["date", "home_team", "away_team", "home_score", "away_score", "stadium", "result", "match_id"]
  ```
- Unified formats (e.g. "FC Barcelona" → "Barcelona")
- Generated standardized master dataset: `master_football_data.csv`

### ✅ Load
- Created Doris DBs per dataset (e.g. `Germany_Bundesliga_1965`)
- Loaded filtered CSVs into respective DBs using Doris Stream Load
- Created master DB: `master_football_data`
  - Merged data from MLS, Euro, Football.co.uk
- Created `cleaned_results` table with validated rows

---

## 🔍 Team Name Mapping

- Script to standardize team name variants:
  - e.g., `MANU`, `Man Utd`, `Manchester United` → `Manchester United`
- Used fuzzy matching & common alias dictionary

---

## 📈 Visualizations

### ✅ Win/Loss/Draw Timeline

- **Interactive Line Graph** using Plotly (HTML)
- Displays home results per day, color-coded:
  - Green → Win
  - Red → Loss
  - Blue → Draw

```bash
python3 plot_team_analysis.py
python3 -m http.server 8080
```

Open `http://<public-ip>:8080/match_results_graph.html`

### ✅ Year Range Dropdown (Dash)

- Dash-based web app to select `Start Year` and `End Year`
- Dynamically updates timeline graph

```bash
python3 dash_timeline.py
# Open http://<ec2-ip>:8080
```

---

## 🔐 Doris Authentication Fix

If stream loading fails due to access:
```sql
-- Run in Doris FE
GRANT ALL ON soccer.* TO 'root'@'%';
GRANT LOAD_PRIV ON soccer.* TO 'root'@'%';
```

Ensure you connect **directly to the BE node** for stream loading:
```python
# Stream Load URL
http://<BE_IP>:8040/api/{database}/{table}/_stream_load
```

---

## ✅ What We Built

- ✔ Loaded multi-source soccer data to Doris
- ✔ Cleaned, normalized & mapped key columns
- ✔ Handled reserved keywords in Doris
- ✔ Built interactive dashboards
- ✔ Deployed on EC2 with public IP access
- ✔ Unified all data into `master_football_data.cleaned_results`

---
