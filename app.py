
import os
import sqlite3
import uuid
from pathlib import Path
from functools import wraps
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, abort
)
from werkzeug.utils import secure_filename

BASE = Path(__file__).resolve().parent
UPLOAD_FOLDER = BASE / "static" / "uploads"
DB_FILE = BASE / "data" / "skins.db"

UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
DB_FILE.parent.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret")
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

def connect():
    con = sqlite3.connect(DB_FILE)
    con.row_factory = sqlite3.Row
    return con

with connect() as con:
    con.execute("""
        CREATE TABLE IF NOT EXISTS skins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hero TEXT NOT NULL,
            skin_name TEXT NOT NULL,
            image_url TEXT NOT NULL,
            download_url TEXT NOT NULL
        )
    """)

def allowed_file(filename):
    return (
        "." in filename and
        filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("admin"))
        return fn(*args, **kwargs)
    return wrapper

@app.route("/")
def index():
    with connect() as con:
        skins = con.execute(
            "SELECT * FROM skins ORDER BY id DESC"
        ).fetchall()
    return render_template("index.html", skins=skins)

@app.route("/admin")
def admin():
    return render_template("admin.html")

@app.route("/admin/login", methods=["POST"])
def admin_login():
    password = os.environ.get("ADMIN_PASSWORD", "")
    if password and request.form.get("password") == password:
        session["admin"] = True
        return redirect(url_for("admin"))
    return "Sai mật khẩu hoặc chưa cài ADMIN_PASSWORD trên Render.", 401

@app.route("/admin/upload", methods=["POST"])
@admin_required
def upload_skin():
    hero = request.form.get("hero", "").strip()
    skin_name = request.form.get("skin_name", "").strip()
    download_url = request.form.get("download_url", "").strip()
    image = request.files.get("image")

    if not hero or not skin_name or not download_url or not image:
        abort(400, "Vui lòng nhập đầy đủ thông tin.")

    if not download_url.startswith(("https://", "http://")):
        abort(400, "Link tải không hợp lệ.")

    if not image.filename or not allowed_file(image.filename):
        abort(400, "Chỉ chấp nhận ảnh PNG, JPG, JPEG hoặc WEBP.")

    extension = secure_filename(image.filename).rsplit(".", 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{extension}"
    image.save(UPLOAD_FOLDER / filename)

    image_url = f"/static/uploads/{filename}"

    with connect() as con:
        con.execute(
            """INSERT INTO skins (hero, skin_name, image_url, download_url)
               VALUES (?, ?, ?, ?)""",
            (hero, skin_name, image_url, download_url)
        )

    return redirect(url_for("admin"))

@app.route("/admin/delete/<int:skin_id>", methods=["POST"])
@admin_required
def delete_skin(skin_id):
    with connect() as con:
        skin = con.execute(
            "SELECT image_url FROM skins WHERE id = ?", (skin_id,)
        ).fetchone()

        if skin:
            image_path = BASE / skin["image_url"].lstrip("/")
            if image_path.exists() and UPLOAD_FOLDER in image_path.parents:
                image_path.unlink()
            con.execute("DELETE FROM skins WHERE id = ?", (skin_id,))

    return redirect(url_for("admin"))

@app.route("/admin/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.errorhandler(413)
def too_large(error):
    return "Ảnh quá lớn. Vui lòng chọn ảnh dưới 10 MB.", 413

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000))
    )
