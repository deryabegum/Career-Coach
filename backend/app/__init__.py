from datetime import timedelta

from flask import Flask, jsonify
from flask_cors import CORS
import os

from .extensions import bcrypt, jwt


def create_app():
    app = Flask(__name__)

    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev"),
        JWT_SECRET_KEY=os.environ.get(
            "JWT_SECRET_KEY",
            os.environ.get("SECRET_KEY", "dev"),
        ),
        MAX_CONTENT_LENGTH=10 * 1024 * 1024,  # 10MB
        UPLOAD_FOLDER=os.path.join(
            os.path.dirname(__file__),
            "..",
            "instance",
            "uploads",
        ),
        DATABASE=os.path.join(
            os.path.dirname(__file__),
            "..",
            "instance",
            "app.db",
        ),
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

    # CORS and extensions
    CORS(app, resources={r"/api/*": {"origins": "*", "supports_credentials": True}})
    bcrypt.init_app(app)
    jwt.init_app(app)

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

    # Career Resources routes (/api/v1/resources/*)
    from .features.resources.api import bp as resources_bp
    app.register_blueprint(resources_bp)

    return app
