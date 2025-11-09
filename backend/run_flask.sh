#!/bin/bash
# Backend Flask app'i çalıştırmak için script

cd "$(dirname "$0")"
source venv/bin/activate
export PYTHONPATH=/Users/selimmaral/Desktop/Career-Coach:$PYTHONPATH
export FLASK_APP=app
export FLASK_ENV=development

echo "🚀 Starting Flask backend..."
echo "📍 Backend will run on: http://localhost:5000"
echo "📋 Registered blueprints: main, dashboard_summary, auth, keywords, mock_interview"
echo ""

flask run
