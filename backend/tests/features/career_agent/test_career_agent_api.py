"""
Integration tests for the career agent API (run, list, get detail).
Uses a temporary SQLite DB and mocks AIHelper to avoid external API calls.
compute_lightweight_match is left unmocked since it is pure Python with no
external dependencies.
"""
import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from backend.app import create_app


SAMPLE_RESUME_TEXT = (
    "Jane Doe. Built and shipped a Python data pipeline. Automated reporting with SQL. "
    "Led a small team and improved report turnaround by 30 percent. "
    "Skills: Python, SQL, Data Analysis, Communication."
)

SAMPLE_JOB_DESCRIPTION = (
    "We are looking for a Data Analyst with strong Python and SQL skills, experience with "
    "dashboards, and familiarity with machine learning and cloud infrastructure."
)

SAMPLE_COVER_LETTER = {
    "cover_letter": "Dear Hiring Manager,\n\nI built a Python pipeline...\n\nThank you.",
    "highlighted_strengths": ["python", "sql"],
    "evaluator": {"provider": "gemini", "method": "llm_draft"},
}

SAMPLE_PREP_PLAN = {
    "focus_areas": [
        {"keyword": "machine", "why_it_matters": "Core to the role.", "how_to_prepare": "Review basics."},
    ],
    "questions": [{"id": "q1", "prompt": "Tell me about a data project.", "tags": ["technical"]}],
    "evaluator": {"provider": "gemini", "method": "llm_gap_analysis"},
}

SAMPLE_RESUME_EVAL = {
    "score": 72,
    "summary": "Solid resume with clear impact.",
    "details": {"suggestions": ["Add a projects section."]},
}


def _run_schema(conn, schema_path: str):
    with open(schema_path) as f:
        conn.executescript(f.read())
    conn.commit()


@pytest.fixture
def app():
    """Create app with a temporary database and run schema."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    app = create_app()
    app.config["TESTING"] = True
    app.config["DATABASE"] = path
    schema_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "database", "schema.sql"
    )
    with app.app_context():
        from backend.app.db import get_db
        with app.test_request_context():
            conn = get_db()
            _run_schema(conn, schema_path)
    yield app
    try:
        os.unlink(path)
    except Exception:
        pass


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_headers(client):
    """Register a test user, login, return headers with Bearer token."""
    client.post(
        "/api/v1/auth/register",
        data=json.dumps({
            "email": "careeragent@test.com",
            "password": "testpass123",
            "name": "Jane Doe",
        }),
        content_type="application/json",
    )
    rv = client.post(
        "/api/v1/auth/login",
        data=json.dumps({
            "email": "careeragent@test.com",
            "password": "testpass123",
        }),
        content_type="application/json",
    )
    assert rv.status_code == 200
    data = json.loads(rv.data)
    token = data.get("accessToken")
    assert token
    return {"Authorization": f"Bearer {token}"}


def _insert_resume(app, email, resume_text):
    """Insert a resume row directly, bypassing file upload/parsing."""
    with app.app_context():
        from backend.app.db import get_db
        with app.test_request_context():
            conn = get_db()
            user_row = conn.execute(
                "SELECT id FROM users WHERE email = ?", (email,)
            ).fetchone()
            parsed = {
                "sections": [{"name": "full_content", "content": resume_text}],
                "extracted_data": {
                    "name": "Jane Doe",
                    "skills": ["Python", "SQL"],
                    "work_experience": [{"company": "Acme", "role": "Analyst"}],
                },
            }
            conn.execute(
                "INSERT INTO resumes (user_id, file_path, parsed_json) VALUES (?, ?, ?)",
                (user_row["id"], "/tmp/fake.pdf", json.dumps(parsed)),
            )
            conn.commit()


def _mock_ai_helper():
    mock_instance = MagicMock()
    mock_instance.scoreResume.return_value = SAMPLE_RESUME_EVAL
    mock_instance.generateCoverLetter.return_value = SAMPLE_COVER_LETTER
    mock_instance.generateInterviewPrepPlan.return_value = SAMPLE_PREP_PLAN
    return mock_instance


def test_run_agent_unauthorized(client):
    """POST /run without a token returns 401."""
    rv = client.post(
        "/api/v1/career-agent/run",
        data=json.dumps({"job_description": "x"}),
        content_type="application/json",
    )
    assert rv.status_code == 401


@patch("backend.app.features.career_agent.service.AIHelper")
def test_run_agent_requires_job_description(MockAIHelper, client, auth_headers):
    MockAIHelper.return_value = _mock_ai_helper()
    rv = client.post(
        "/api/v1/career-agent/run",
        data=json.dumps({"role": "Data Analyst", "company": "Acme"}),
        content_type="application/json",
        headers=auth_headers,
    )
    assert rv.status_code == 400


@patch("backend.app.features.career_agent.service.AIHelper")
def test_run_agent_without_resume_returns_404(MockAIHelper, client, auth_headers):
    MockAIHelper.return_value = _mock_ai_helper()
    rv = client.post(
        "/api/v1/career-agent/run",
        data=json.dumps({
            "job_description": SAMPLE_JOB_DESCRIPTION,
            "role": "Data Analyst",
            "company": "Acme",
        }),
        content_type="application/json",
        headers=auth_headers,
    )
    assert rv.status_code == 404


@patch("backend.app.features.career_agent.service.AIHelper")
def test_run_agent_full_contract(MockAIHelper, client, app, auth_headers):
    """Full run: resume analysis -> gap analysis -> cover letter -> prep plan, then list/detail."""
    MockAIHelper.return_value = _mock_ai_helper()
    _insert_resume(app, "careeragent@test.com", SAMPLE_RESUME_TEXT)

    rv = client.post(
        "/api/v1/career-agent/run",
        data=json.dumps({
            "job_description": SAMPLE_JOB_DESCRIPTION,
            "role": "Data Analyst",
            "company": "Acme",
        }),
        content_type="application/json",
        headers=auth_headers,
    )
    assert rv.status_code == 201
    data = json.loads(rv.data)

    assert "run_id" in data
    assert [s["step"] for s in data["steps"]] == [
        "load_resume",
        "score_resume",
        "gap_analysis",
        "plan_adjustment",
        "draft_cover_letter",
        "build_interview_prep",
    ]
    assert data["resume_analysis"]["score"] == 72
    assert data["cover_letter"]["cover_letter"] == SAMPLE_COVER_LETTER["cover_letter"]
    assert data["interview_prep"]["questions"][0]["id"] == "q1"
    assert "match_analysis" in data and "missing_keywords" in data["match_analysis"]
    assert isinstance(data["decisions"], list) and data["decisions"]

    list_rv = client.get("/api/v1/career-agent/runs", headers=auth_headers)
    assert list_rv.status_code == 200
    runs = json.loads(list_rv.data)["runs"]
    assert len(runs) == 1
    assert runs[0]["id"] == data["run_id"]
    assert runs[0]["resume_score"] == 72

    detail_rv = client.get(f"/api/v1/career-agent/runs/{data['run_id']}", headers=auth_headers)
    assert detail_rv.status_code == 200
    detail = json.loads(detail_rv.data)
    assert detail["role"] == "Data Analyst"
    assert detail["company"] == "Acme"
    assert len(detail["steps"]) == 6
    assert detail["cover_letter"]["cover_letter"] == SAMPLE_COVER_LETTER["cover_letter"]


@patch("backend.app.features.career_agent.service.AIHelper")
def test_get_run_not_found(MockAIHelper, client, auth_headers):
    """Fetching a run id that doesn't exist (or isn't owned by the user) returns 404."""
    MockAIHelper.return_value = _mock_ai_helper()
    rv = client.get("/api/v1/career-agent/runs/99999", headers=auth_headers)
    assert rv.status_code == 404
