"""
Integration tests for the mock interview API (create session, feedback, submit).
Uses a temporary SQLite DB and mocks AIHelper to avoid external API calls.
"""
import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from backend.app import create_app


FIXTURE_QUESTIONS = [
    {"id": "q1", "prompt": "Describe a technical win.", "tags": ["technical"]},
    {"id": "q2", "prompt": "How do you work with others?", "tags": ["behavioral"]},
]

SAMPLE_FEEDBACK = {
    "summary": "Good use of the STAR method.",
    "strengths": ["Clear situation", "Specific actions"],
    "suggestions": ["Add more metrics"],
    "overall_score": 75.0,
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
            "email": "mockinterview@test.com",
            "password": "testpass123",
            "name": "Test User",
        }),
        content_type="application/json",
    )
    rv = client.post(
        "/api/v1/auth/login",
        data=json.dumps({
            "email": "mockinterview@test.com",
            "password": "testpass123",
        }),
        content_type="application/json",
    )
    assert rv.status_code == 200
    data = json.loads(rv.data)
    token = data.get("accessToken")
    assert token
    return {"Authorization": f"Bearer {token}"}


@patch(
    "backend.app.features.mock_interview.api.build_question_set",
    return_value=FIXTURE_QUESTIONS,
)
def test_create_session_contract(mock_bq, client, auth_headers):
    """POST /api/v1/mock-interview/sessions returns 201 and session_id."""
    rv = client.post(
        "/api/v1/mock-interview/sessions",
        data=json.dumps({"role": "Software Engineer", "company": "Acme"}),
        content_type="application/json",
        headers=auth_headers,
    )
    assert rv.status_code == 201
    data = json.loads(rv.data)
    assert "session_id" in data
    assert data.get("role") == "Software Engineer"
    assert data.get("company") == "Acme"
    assert len(data.get("questions") or []) == 2


@patch(
    "backend.app.features.mock_interview.api.build_question_set",
    return_value=FIXTURE_QUESTIONS,
)
def test_create_session_unauthorized(mock_bq, client):
    """POST sessions without token returns 401."""
    rv = client.post(
        "/api/v1/mock-interview/sessions",
        data=json.dumps({"role": "SWE", "company": "Co"}),
        content_type="application/json",
    )
    assert rv.status_code == 401


@patch("backend.app.features.mock_interview.api.AIHelper")
def test_feedback_contract(MockAIHelper, client, auth_headers):
    """POST /api/v1/mock-interview/feedback returns 200 and feedback object."""
    mock_instance = MagicMock()
    mock_instance.generateInterviewFeedback.return_value = {**SAMPLE_FEEDBACK}
    MockAIHelper.return_value = mock_instance

    rv = client.post(
        "/api/v1/mock-interview/feedback",
        data=json.dumps({
            "session_id": 1,
            "question_prompt": "Tell me about a challenge.",
            "answer_text": "I led a project that had tight deadlines.",
            "role": "SWE",
            "company": "Acme",
        }),
        content_type="application/json",
        headers=auth_headers,
    )
    assert rv.status_code == 200
    data = json.loads(rv.data)
    assert data.get("summary") == SAMPLE_FEEDBACK["summary"]
    assert "strengths" in data
    assert "suggestions" in data


@patch("backend.app.features.mock_interview.api.AIHelper")
def test_feedback_validation(MockAIHelper, client, auth_headers):
    """POST feedback with missing answer_text or question_prompt returns 400."""
    rv = client.post(
        "/api/v1/mock-interview/feedback",
        data=json.dumps({
            "session_id": 1,
            "question_prompt": "Q?",
            "answer_text": "",
            "role": "",
            "company": "",
        }),
        content_type="application/json",
        headers=auth_headers,
    )
    assert rv.status_code == 400
    data = json.loads(rv.data)
    assert "error" in data

    rv2 = client.post(
        "/api/v1/mock-interview/feedback",
        data=json.dumps({
            "session_id": 1,
            "answer_text": "Some answer",
            "role": "",
            "company": "",
        }),
        content_type="application/json",
        headers=auth_headers,
    )
    assert rv2.status_code == 400


@patch(
    "backend.app.features.mock_interview.api.build_question_set",
    return_value=FIXTURE_QUESTIONS,
)
@patch("backend.app.features.mock_interview.service.AIHelper")
def test_submit_contract(MockServiceAI, mock_bq, client, auth_headers):
    """Create session, then POST submit returns 200 with feedback and scores."""
    mock_instance = MagicMock()
    mock_instance.generateInterviewFeedback.return_value = {**SAMPLE_FEEDBACK}
    MockServiceAI.return_value = mock_instance

    cr = client.post(
        "/api/v1/mock-interview/sessions",
        data=json.dumps({"role": "SWE", "company": "Acme"}),
        content_type="application/json",
        headers=auth_headers,
    )
    assert cr.status_code == 201
    session_id = json.loads(cr.data)["session_id"]

    answers = {
        "q1": {"answer": "I implemented a cache to reduce latency.", "prompt": "Describe a technical win."},
        "q2": {"answer": "I collaborated with design and product.", "prompt": "How do you work with others?"},
    }

    rv = client.post(
        "/api/v1/mock-interview/submit",
        data=json.dumps({
            "session_id": session_id,
            "answers": answers,
            "role": "SWE",
            "company": "Acme",
        }),
        content_type="application/json",
        headers=auth_headers,
    )
    assert rv.status_code == 200
    data = json.loads(rv.data)
    assert "session_id" in data
    assert data["session_id"] == session_id
    assert "feedback" in data
    assert "average_score" in data
    assert "total_score" in data
    assert "questions_answered" in data
    assert data["questions_answered"] == 2
    assert "q1" in data["feedback"]
    assert "q2" in data["feedback"]


@patch("backend.app.features.mock_interview.api.AIHelper")
def test_submit_validation(MockAIHelper, client, auth_headers):
    """POST submit without session_id or answers returns 400."""
    rv = client.post(
        "/api/v1/mock-interview/submit",
        data=json.dumps({"answers": {"q1": "a1"}, "role": "", "company": ""}),
        content_type="application/json",
        headers=auth_headers,
    )
    assert rv.status_code == 400
    data = json.loads(rv.data)
    assert "error" in data

    rv2 = client.post(
        "/api/v1/mock-interview/submit",
        data=json.dumps({"session_id": 1, "role": "", "company": ""}),
        content_type="application/json",
        headers=auth_headers,
    )
    assert rv2.status_code == 400


@patch("backend.app.features.mock_interview.service.AIHelper")
def test_submit_nonexistent_session(MockServiceAI, client, auth_headers):
    """POST submit with invalid session_id returns 404."""
    mock_instance = MagicMock()
    MockServiceAI.return_value = mock_instance

    rv = client.post(
        "/api/v1/mock-interview/submit",
        data=json.dumps({
            "session_id": 99999,
            "answers": {"q1": {"answer": "Yes", "prompt": "Q?"}},
            "role": "",
            "company": "",
        }),
        content_type="application/json",
        headers=auth_headers,
    )
    assert rv.status_code == 404
    data = json.loads(rv.data)
    assert "error" in data


@patch(
    "backend.app.features.mock_interview.api.build_question_set",
    return_value=FIXTURE_QUESTIONS,
)
@patch("backend.app.features.mock_interview.service.AIHelper")
def test_list_and_get_session_history(MockServiceAI, mock_bq, client, auth_headers):
    """After submit, GET /sessions lists row and GET /sessions/:id returns detail."""
    mock_instance = MagicMock()
    mock_instance.generateInterviewFeedback.return_value = {**SAMPLE_FEEDBACK}
    MockServiceAI.return_value = mock_instance

    cr = client.post(
        "/api/v1/mock-interview/sessions",
        data=json.dumps({"role": "SWE", "company": "Acme"}),
        content_type="application/json",
        headers=auth_headers,
    )
    session_id = json.loads(cr.data)["session_id"]

    client.post(
        "/api/v1/mock-interview/submit",
        data=json.dumps({
            "session_id": session_id,
            "answers": {
                "q1": {"answer": "Answer one", "prompt": "Describe a technical win."},
            },
            "role": "SWE",
            "company": "Acme",
        }),
        content_type="application/json",
        headers=auth_headers,
    )

    lst = client.get("/api/v1/mock-interview/sessions", headers=auth_headers)
    assert lst.status_code == 200
    sessions = json.loads(lst.data)["sessions"]
    assert len(sessions) >= 1
    row = next(s for s in sessions if s["id"] == session_id)
    assert row["answer_count"] == 1
    assert row.get("submitted_at") is not None

    detail_rv = client.get(
        f"/api/v1/mock-interview/sessions/{session_id}",
        headers=auth_headers,
    )
    assert detail_rv.status_code == 200
    detail = json.loads(detail_rv.data)
    assert detail["id"] == session_id
    assert len(detail["items"]) == 1
    assert detail["items"][0]["qid"] == "q1"
    assert detail["items"][0]["feedback"].get("summary") == SAMPLE_FEEDBACK["summary"]
