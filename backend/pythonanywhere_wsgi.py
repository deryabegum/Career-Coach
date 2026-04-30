import os
import sys

PROJECT_ROOT = "/home/YOUR_PYTHONANYWHERE_USERNAME/Career-Coach"
BACKEND_ROOT = os.path.join(PROJECT_ROOT, "backend")

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

os.environ.setdefault("SECRET_KEY", "replace-me")
os.environ.setdefault("JWT_SECRET_KEY", "replace-me-too")
os.environ.setdefault("DATABASE_PATH", f"{BACKEND_ROOT}/instance/app.db")
os.environ.setdefault("UPLOAD_DIR", f"{BACKEND_ROOT}/instance/uploads")
os.environ.setdefault("FRONTEND_ORIGIN", "https://your-vercel-project.vercel.app")

from app import create_app  # noqa: E402

application = create_app()
