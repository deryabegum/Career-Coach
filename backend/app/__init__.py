# backend/app/__init__.py
from flask import Flask
from flask_cors import CORS
import os
from .extensions import bcrypt

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
    
    CORS(app, resources={r"/api/*": {"origins": "*", "supports_credentials": True}})

    # Init extensions here
    bcrypt.init_app(app)

    # Register Blueprints
    # main_bp (from main.py) contains /login, /register, /resume/upload
    from .main import bp as main_bp
    app.register_blueprint(main_bp, url_prefix="/api") 

    from .db import init_app as init_db
    init_db(app)

    # dashboard_summary_bp contains the required /api/v1/dashboard/summary route
    from .features.dashboard_summary.api import bp as dashboard_summary_bp
    
    app.register_blueprint(dashboard_summary_bp)   

    from .features.jwt_auth.api import bp as auth_bp
    app.register_blueprint(auth_bp)  # exposes /api/v1/auth/register and /login
    
    return app
