import json
from flask import Flask
from backend.app.features.dashboard_summary.api import bp as summary_bp

def test_summary_contract():
    app = Flask(__name__)
    app.register_blueprint(summary_bp)
    client = app.test_client()
    rv = client.get("/api/v1/dashboard/summary")
    assert rv.status_code == 200
    data = json.loads(rv.data)
    assert "lastResumeScore" in data
    assert "interviewAverage" in data
    assert "lastKeywordMatchScore" in data
    assert "totals" in data and set(data["totals"]) == {"resumes","interviews","matches"}
    assert "updatedAt" in data
