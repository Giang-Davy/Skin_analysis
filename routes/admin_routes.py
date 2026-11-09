import os
from functools import wraps

from flask import Blueprint, abort, redirect, render_template, request, session

from db.mysql import get_connection
from routes.auth_routes import require_jwt_auth

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")
EVENT_TYPES = (
    "login_success",
    "login_failed",
    "logout",
    "registration",
    "account_deleted",
    "data_exported",
    "image_uploaded",
    "image_deleted",
    "images_deleted",
    "image_organization_changed",
    "caption_edited",
    "album_created",
    "album_renamed",
    "album_deleted",
    "tag_created",
    "tag_renamed",
    "tag_deleted",
)


def _configured_admins():
    return {
        username.strip().casefold()
        for username in os.environ.get("ADMIN_USERNAMES", "").split(",")
        if username.strip()
    }


def require_admin(view_func):
    @wraps(view_func)
    @require_jwt_auth
    def wrapped_view(*args, **kwargs):
        username = session.get("username", "")
        if not username or username.casefold() not in _configured_admins():
            abort(403)
        return view_func(*args, **kwargs)

    return wrapped_view


@admin_bp.route("/logs")
@require_admin
def logs():
    event_type = request.args.get("event_type", "")
    if event_type not in EVENT_TYPES:
        event_type = ""

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        if event_type:
            cursor.execute(
                """
                SELECT id, event_type, actor_user_id, actor_username, details, created_at
                FROM event_logs
                WHERE event_type = %s
                ORDER BY created_at DESC, id DESC
                LIMIT 200
                """,
                (event_type,),
            )
        else:
            cursor.execute(
                """
                SELECT id, event_type, actor_user_id, actor_username, details, created_at
                FROM event_logs
                ORDER BY created_at DESC, id DESC
                LIMIT 200
                """
            )
        events = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

    return render_template(
        "admin_logs.html",
        events=events,
        event_types=EVENT_TYPES,
        selected_event_type=event_type,
    )
