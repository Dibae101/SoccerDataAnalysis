#!/bin/bash

# Elevate if not root
if [ "$EUID" -ne 0 ]; then
  echo "🔒 Switching to root..."
  exec sudo "$0" "$@"
fi

echo "🔁 Switching to Ubuntu user and starting services..."

# Apache Doris Frontend
echo "🚀 Starting Apache Doris FE (Frontend) on port 8030..."
/home/ubuntu/apache-doris-2.1.8.1-bin-x64/fe/bin/start_fe.sh --daemon
echo "✅ Doris Frontend running at: http://18.223.11.133:8030"

# Superset
echo "🚀 Starting Apache Superset on port 8088..."
cd /home/ubuntu/superset_project || exit

# Optional: activate virtual environment if not already
source superset-venv/bin/activate

# Run with Gunicorn (production-ready)
nohup gunicorn --bind 0.0.0.0:8088 --workers 5 --timeout 120 "superset.app:create_app()" > gunicorn.log 2>&1 &

echo "✅ Superset running at: http://18.223.11.133:8088"
