from flask import Blueprint, session, redirect, request, url_for

admin_blu = Blueprint("admin", __name__, url_prefix="/admin")
from . import views


def check_admin():
    # 保证只有管理员才能进入
    is_admin = session.get("is_admin", False)
    if not is_admin and not request.url.endswith(url_for("admin.login")):
        return redirect("/")

