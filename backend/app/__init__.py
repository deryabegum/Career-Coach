from datetime import timedelta
from flask import Flask, jsonify
from flask_cors import CORS
from werkzeug.exceptions import RequestEntityTooLarge
import os

from .extensions import bcrypt, jwt, limiter


def create_app():
    app = Flask(__name__)
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    default_upload_dir = os.path.join(base_dir, "instance", "uploads")
    default_database_path = os.path.join(base_dir, "instance", "app.db")

    # Fail loudly if a real secret has not been set in production
    _jwt_secret = os.environ.get("JWT_SECRET_KEY") or os.environ.get("SECRET_KEY")
    if not _jwt_secret:
        import warnings
        warnings.warn(
            "JWT_SECRET_KEY is not set — using insecure default. "
            "Set JWT_SECRET_KEY in your environment before deploying.",
            stacklevel=2,
        )
        _jwt_secret = "dev-change-me"

    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-change-me"),
        JWT_SECRET_KEY=_jwt_secret,
        MAX_CONTENT_LENGTH=10 * 1024 * 1024,  # 10MB
        UPLOAD_FOLDER=os.environ.get("UPLOAD_DIR", default_upload_dir),
        DATABASE=os.environ.get("DATABASE_PATH", default_database_path),
        ALLOWED_EXTS={"pdf", "docx"},
        ALLOWED_MIMES={
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        },
        JSON_SORT_KEYS=False,
        # JWT expiry config
        JWT_ACCESS_TOKEN_EXPIRES=timedelta(minutes=30),
        JWT_REFRESH_TOKEN_EXPIRES=timedelta(days=7),
    )

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(os.path.dirname(app.config["DATABASE"]), exist_ok=True)

    raw_cors_origins = os.environ.get("CORS_ORIGINS") or os.environ.get("FRONTEND_ORIGIN") or "*"
    cors_origins = (
        [origin.strip() for origin in raw_cors_origins.split(",") if origin.strip()]
        if raw_cors_origins != "*"
        else "*"
    )

    # CORS and extensions
    CORS(
        app,
        resources={r"/api/*": {"origins": cors_origins}},
        supports_credentials=True,
    )
    bcrypt.init_app(app)
    jwt.init_app(app)
    limiter.init_app(app)

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"}), 200

    # JWT Error Handlers
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify(
            {
                "error": "Token has expired",
                "message": "Your session has expired. Please log in again.",
            }
        ), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify(
            {
                "error": "Invalid token",
                "message": "Your session is invalid. Please log in again.",
            }
        ), 401

    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify(
            {
                "error": "Authorization required",
                "message": "Please log in to access this resource.",
            }
        ), 401

    @jwt.needs_fresh_token_loader
    def token_not_fresh_callback(jwt_header, jwt_payload):
        return jsonify(
            {
                "error": "Fresh token required",
                "message": "Please log in again.",
            }
        ), 401

    # Blueprints
    from .main import bp as main_bp
    app.register_blueprint(main_bp, url_prefix="/api")

    from .db import init_app as init_db, ensure_db_initialized, get_db
    init_db(app)
    with app.app_context():
        ensure_db_initialized()
        # Migration: ensure job_applications table exists for existing databases
        _db = get_db()
        _db.execute("""
            CREATE TABLE IF NOT EXISTS job_applications (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                company_name TEXT    NOT NULL,
                applied_date TEXT    NOT NULL,
                stage        TEXT    NOT NULL DEFAULT 'applied',
                field        TEXT    NOT NULL DEFAULT '',
                created_at   TEXT    NOT NULL DEFAULT (datetime('now'))
            )
        """)
        _interview_cols = {
            row[1] for row in _db.execute("PRAGMA table_info(interviews)").fetchall()
        }
        if "user_id" not in _interview_cols:
            _db.execute(
                "ALTER TABLE interviews ADD COLUMN user_id INTEGER REFERENCES users(id)"
            )
        if "submitted_at" not in _interview_cols:
            _db.execute("ALTER TABLE interviews ADD COLUMN submitted_at TEXT")
        if "average_score" not in _interview_cols:
            _db.execute("ALTER TABLE interviews ADD COLUMN average_score REAL")
        if "total_score" not in _interview_cols:
            _db.execute("ALTER TABLE interviews ADD COLUMN total_score REAL")
        if "questions_json" not in _interview_cols:
            _db.execute("ALTER TABLE interviews ADD COLUMN questions_json TEXT")
        _db.commit()
        # Migration: add user_id to interviews table if missing
        interviews_cols = {row[1] for row in _db.execute("PRAGMA table_info(interviews)").fetchall()}
        if "user_id" not in interviews_cols:
            _db.execute("ALTER TABLE interviews ADD COLUMN user_id INTEGER")
            _db.commit()

    # Dashboard summary routes (/api/v1/dashboard/summary)
    from .features.dashboard_summary.api import bp as dashboard_summary_bp
    app.register_blueprint(dashboard_summary_bp)

    # Auth routes (/api/v1/auth/register and /login)
    from .features.jwt_auth.api import bp as auth_bp
    app.register_blueprint(auth_bp)

    # Keywords routes (/api/keywords/match)
    from .features.keywords.api import bp as keywords_bp
    app.register_blueprint(keywords_bp)

    # Mock Interview routes (/api/v1/mock-interview/*)
    from .features.mock_interview.api import bp as mock_interview_bp
    app.register_blueprint(mock_interview_bp)

    # Career Resources routes (/api/v1/resources/*)
    from .features.resources.api import bp as resources_bp
    app.register_blueprint(resources_bp)

    # Return JSON for 413 (file too large) instead of HTML
    @app.errorhandler(RequestEntityTooLarge)
    def handle_request_entity_too_large(e):
        max_mb = app.config.get("MAX_CONTENT_LENGTH", 10 * 1024 * 1024) // (1024 * 1024)
        return jsonify({"error": f"File too large. Maximum size is {max_mb} MB."}), 413
    # Progress routes (/api/v1/progress/me)
    from .features.progress.api import bp as progress_bp
    app.register_blueprint(progress_bp)

    # Job Applications routes (/api/v1/applications/*)
    from .features.job_applications.api import bp as applications_bp
    app.register_blueprint(applications_bp)

    return app
