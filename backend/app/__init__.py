from flask import Flask
from flask_cors import CORS
import os

from .extensions import bcrypt
from flask_jwt_extended import JWTManager


def create_app():
    app = Flask(__name__)

    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev"),
        JWT_SECRET_KEY=os.environ.get("JWT_SECRET_KEY", os.environ.get("SECRET_KEY", "dev")),
        MAX_CONTENT_LENGTH=10 * 1024 * 1024,  # 10MB
        UPLOAD_FOLDER=os.path.join(os.path.dirname(__file__), "..", "instance", "uploads"),
        DATABASE=os.path.join(os.path.dirname(__file__), "..", "instance", "app.db"),
        ALLOWED_EXTS={"pdf", "docx"},
        ALLOWED_MIMES={
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        },
        JSON_SORT_KEYS=False,
    )

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # CORS and extensions
    CORS(app, resources={r"/api/*": {"origins": "*", "supports_credentials": True}})
    bcrypt.init_app(app)
    JWTManager(app)

    # Blueprints
    # main_bp (from main.py) contains /login, /register, /resume/upload
    from .main import bp as main_bp
    app.register_blueprint(main_bp, url_prefix="/api")

    from .db import init_app as init_db
    init_db(app)

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

    return app
