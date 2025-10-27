from flask_jwt_extended import get_jwt_identity

def _current_user_id() -> int:
    uid = get_jwt_identity()
    if uid is None:
        # Callers should be protected by @jwt_required() so this shouldn't happen.
        raise PermissionError("No JWT identity found")
    return int(uid)