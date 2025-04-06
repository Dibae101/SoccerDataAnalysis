#!/bin/bash

# Elevate if not root
if [ "$EUID" -ne 0 ]; then
  echo "🔒 Switching to root..."
  exec sudo "$0" "$@"
fi

echo "Switching to Ubuntu user and starting services..."

# Apache Doris Frontend
echo "Starting Apache Doris FE (Frontend) on port 8030..."
/home/ubuntu/apache-doris-2.1.8.1-bin-x64/fe/bin/start_fe.sh --daemon

# Superset: activate virtualenv & launch
echo "Activating Superset virtual environment..."
source /home/ubuntu/superset_project/superset-venv/bin/activate

echo "Launching Superset via Gunicorn on port 8088..."
nohup gunicorn --bind 0.0.0.0:8088 --workers 5 --timeout 120 "superset.app:create_app()" > /home/ubuntu/superset_project/gunicorn.log 2>&1 &

echo ""
echo "Doris Frontend running at: http://18.223.11.133:8030"
echo "Apache Superset available at: http://18.223.11.133:8088"