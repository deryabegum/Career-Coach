# backend/app/__init__.py
from flask import Flask
from flask_cors import CORS
import os

def create_app():
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY","dev"),
        MAX_CONTENT_LENGTH=10 * 1024 * 1024,  # 10MB
        UPLOAD_FOLDER=os.path.join(os.path.dirname(__file__), "..", "instance", "uploads"),
        DATABASE=os.path.join(os.path.dirname(__file__), "..", "instance", "app.db"),
        ALLOWED_EXTS={"pdf","docx"},
        ALLOWED_MIMES={
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        },
        JSON_SORT_KEYS=False,
    )
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    from .main import bp as main_bp
    app.register_blueprint(main_bp, url_prefix="/api")

    from .db import init_app as init_db
    init_db(app)


    from .features.dashboard_summary.api import bp as dashboard_summary_bp
    app.register_blueprint(dashboard_summary_bp)   # bp has url_prefix="/api/v1/dashboard"

    return app
