import os
import sqlite3
import uuid

from pathlib import Path
from datetime import datetime
from functools import wraps

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, send_file, abort
)

from werkzeug.security import (
    check_password_hash, generate_password_hash
)

from werkzeug.utils import secure_filename


# --------------------------------------------------
# 1. PROJECT CONFIGURATION
# --------------------------------------------------

BASE = Path(__file__).resolve().parent

DB = BASE / "csc_center.db"
PRIVATE_UPLOADS = BASE / "private_uploads"
AD_UPLOADS = BASE / "static" / "uploads"

PRIVATE_UPLOADS.mkdir(exist_ok=True)
AD_UPLOADS.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "change-this-secret-before-deployment"
)

app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")

ADMIN_PASSWORD = os.environ.get(
    "ADMIN_PASSWORD", "ChangeMe123!"
)

ADMIN_PASSWORD_HASH = generate_password_hash(ADMIN_PASSWORD)

# Admin credentials ni app.config dictionary lo kuda store chestam
app.config["ADMIN_USERNAME"] = ADMIN_USERNAME
app.config["ADMIN_PASSWORD_HASH"] = ADMIN_PASSWORD_HASH


# --------------------------------------------------
# 2. FILE EXTENSIONS
# --------------------------------------------------

DOC_EXTENSIONS = {
    "xlsx", "xls", "csv", "doc", "docx",
    "pdf", "jpg", "jpeg", "png", "xml"
}

IMAGE_EXTENSIONS = {
    "jpg", "jpeg", "png", "gif", "webp"
}


# --------------------------------------------------
# 3. WEBSITE IMAGES AND DEFAULT URLS
# --------------------------------------------------

CSC_LOGO_URL = (
    "https://encrypted-tbn0.gstatic.com/images?"
    "q=tbn:ANd9GcShW-eFwiUUhEuaaFrI_0vhpqTkniwUZx9r7gJkVVyKSA&s=10"
)

AYYAPPA_IMAGE_URL = (
    "https://encrypted-tbn0.gstatic.com/images?"
    "q=tbn:ANd9GcT18pw-1bMoVXvqOPWmj_LZTmgN-cWoHN537EBsnYSD2g&s=10"
)

DEFAULT_AD_IMAGE = (
    "https://yt3.ggpht.com/ecAIFcwvtmjzhsjD-c6TCS-kihUCWlLAPxFjQKHyodeMCRMQyyVk9poipKIDMN1DpvQqjIxGzcYIeQ=s800-c-fcrop64=1,00000000ffffffff-rw-nd-v1"
)

DEFAULT_AD_LINK = (
    "https://vinaytechhouse.com/data-analytics-course-in-hyderabad/"
)


# --------------------------------------------------
# 4. DATABASE CONNECTION
# --------------------------------------------------

def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


# --------------------------------------------------
# 5. DATABASE INITIALIZATION
# --------------------------------------------------

def init_db():

    with db() as conn:

        conn.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_name TEXT NOT NULL,
                mobile TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                application_id INTEGER NOT NULL,
                original_name TEXT NOT NULL,
                stored_name TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        defaults = {
            "ad_image": DEFAULT_AD_IMAGE,
            "ad_link": DEFAULT_AD_LINK,
            "ad_title": "Data Analytics Course in Hyderabad",
            "ad_description": "Explore course details and training information.",
            "csc_logo": CSC_LOGO_URL,
            "csc_logo_width": "90",
            "csc_logo_height": "65"
        }

        for key, value in defaults.items():

            conn.execute(
                """
                INSERT OR IGNORE INTO settings(key, value)
                VALUES(?, ?)
                """,
                (key, value)
            )


# --------------------------------------------------
# 6. SETTINGS FUNCTIONS
# --------------------------------------------------

def get_settings():

    with db() as conn:

        rows = conn.execute(
            "SELECT key, value FROM settings"
        ).fetchall()

    return {
        row["key"]: row["value"]
        for row in rows
    }


def set_setting(key, value):

    with db() as conn:

        conn.execute("""
            INSERT INTO settings(key, value)
            VALUES(?, ?)
            ON CONFLICT(key)
            DO UPDATE SET value = excluded.value
        """, (key, value))


# --------------------------------------------------
# 7. ADMIN LOGIN PROTECTION
# --------------------------------------------------

def admin_required(view):

    @wraps(view)
    def wrapped(*args, **kwargs):

        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login"))

        return view(*args, **kwargs)

    return wrapped


# --------------------------------------------------
# 8. FILE VALIDATION
# --------------------------------------------------

def allowed_file(filename, extensions):

    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in extensions
    )


# --------------------------------------------------
# 9. STUDENT HOME PAGE AND FORM
# --------------------------------------------------

@app.route("/", methods=["GET", "POST"])
def home():

    if request.method == "POST":

        name = request.form.get(
            "student_name", ""
        ).strip()

        documents = [
            f for f in request.files.getlist("documents")
            if f and f.filename
        ]

        if not name:

            flash("Enter student name.", "error")
            return redirect(url_for("home"))

        if not documents:

            flash("Please choose at least one document.", "error")
            return redirect(url_for("home"))

        if any(
            not allowed_file(f.filename, DOC_EXTENSIONS)
            for f in documents
        ):

            flash(
                "Unsupported file format. Please check the allowed formats.",
                "error"
            )

            return redirect(url_for("home"))

        saved_paths = []

        try:

            with db() as conn:

                cursor = conn.execute(
                    """
                    INSERT INTO applications
                    (student_name, mobile, created_at)
                    VALUES (?, ?, ?)
                    """,
                    (
                        name,
                        "",
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    )
                )

                application_id = cursor.lastrowid

                for file in documents:

                    original = secure_filename(
                        file.filename
                    ) or "document"

                    stored = (
                        uuid.uuid4().hex + "_" + original
                    )

                    destination = PRIVATE_UPLOADS / stored

                    file.save(destination)

                    saved_paths.append(destination)

                    conn.execute(
                        """
                        INSERT INTO documents
                        (application_id, original_name, stored_name)
                        VALUES (?, ?, ?)
                        """,
                        (application_id, original, stored)
                    )

        except Exception:

            for path in saved_paths:

                if path.exists():
                    path.unlink()

            raise

        return render_template(
            "success.html",
            application_id=application_id
        )

    return render_template(
        "index.html",
        settings=get_settings(),
        csc_logo_url=CSC_LOGO_URL,
        ayyappa_image_url=AYYAPPA_IMAGE_URL
    )


# --------------------------------------------------
# 10. PRIVATE ADMIN LOGIN URL
# --------------------------------------------------

@app.route(
    "/kmr-secure-panel-77",
    methods=["GET", "POST"]
)
def admin_login():

    if session.get("admin_logged_in"):

        return redirect(url_for("dashboard"))

    if request.method == "POST":

        username = request.form.get("username", "")
        password = request.form.get("password", "")

        if (
            username == ADMIN_USERNAME
            and check_password_hash(
                ADMIN_PASSWORD_HASH, password
            )
        ):

            session.clear()
            session["admin_logged_in"] = True

            return redirect(url_for("dashboard"))

        flash(
            "Incorrect username or password.",
            "error"
        )

    return render_template("login.html")


# --------------------------------------------------
# 11. ADMIN LOGOUT
# --------------------------------------------------

@app.route("/admin/logout")
@admin_required
def admin_logout():

    session.clear()

    return redirect(url_for("home"))


# --------------------------------------------------
# 12. ADMIN DASHBOARD
# --------------------------------------------------

@app.route("/admin")
@admin_required
def dashboard():

    q = request.args.get("q", "").strip()

    with db() as conn:

        if q:

            applications = conn.execute(
                """
                SELECT * FROM applications
                WHERE student_name LIKE ?
                ORDER BY id DESC
                """,
                (f"%{q}%",)
            ).fetchall()

        else:

            applications = conn.execute(
                """
                SELECT * FROM applications
                ORDER BY id DESC
                """
            ).fetchall()

        documents = conn.execute(
            "SELECT * FROM documents ORDER BY id DESC"
        ).fetchall()

        total = conn.execute(
            "SELECT COUNT(*) FROM applications"
        ).fetchone()[0]

    docs_by_app = {}

    for doc in documents:

        docs_by_app.setdefault(
            doc["application_id"], []
        ).append(doc)

    return render_template(
        "dashboard.html",
        applications=applications,
        docs_by_app=docs_by_app,
        total=total,
        q=q
    )

@app.route("/admin/change-password", methods=["GET", "POST"])
@admin_required
def change_password():

    if request.method == "POST":

        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        settings = get_settings()
        saved_hash = settings.get("admin_password_hash", "")

        if not saved_hash or not check_password_hash(
            saved_hash, current_password
        ):
            flash("Current password is incorrect.", "error")
            return redirect(url_for("change_password"))

        if len(new_password) < 10:
            flash("Password must be at least 10 characters.", "error")
            return redirect(url_for("change_password"))

        if new_password != confirm_password:
            flash("New passwords do not match.", "error")
            return redirect(url_for("change_password"))

        set_setting(
            "admin_password_hash",
            generate_password_hash(new_password)
        )

        session.clear()

        flash("Password changed successfully. Login again.", "success")
        return redirect(url_for("admin_login"))

    return render_template("change_password.html")
# --------------------------------------------------
# 13. ADVERTISEMENT MANAGEMENT
# --------------------------------------------------

@app.route(
    "/admin/advertisement",
    methods=["GET", "POST"]
)
@admin_required
def advertisement():

    if request.method == "POST":

        title = request.form.get(
            "ad_title", ""
        ).strip()

        description = request.form.get(
            "ad_description", ""
        ).strip()

        link = request.form.get(
            "ad_link", ""
        ).strip()

        image = request.files.get("ad_image")

        if not title or not link:

            flash(
                "Advertisement title and URL are required.",
                "error"
            )

            return redirect(url_for("advertisement"))

        if not link.startswith(("https://", "http://")):

            flash(
                "Enter a valid URL starting with http:// or https://.",
                "error"
            )

            return redirect(url_for("advertisement"))

        set_setting("ad_title", title)
        set_setting("ad_description", description)
        set_setting("ad_link", link)

        if image and image.filename:

            if not allowed_file(
                image.filename, IMAGE_EXTENSIONS
            ):

                flash(
                    "Ad image must be JPG, JPEG, PNG or WEBP.",
                    "error"
                )

                return redirect(url_for("advertisement"))

            filename = (
                uuid.uuid4().hex
                + "_"
                + (secure_filename(image.filename) or "ad-image")
            )

            image.save(AD_UPLOADS / filename)

            set_setting(
                "ad_image",
                url_for(
                    "static",
                    filename="uploads/" + filename
                )
            )

        flash(
            "Advertisement updated successfully.",
            "success"
        )

        return redirect(url_for("advertisement"))

    return render_template(
        "advertisement.html",
        settings=get_settings()
    )


# --------------------------------------------------
# 14. PRIVATE DOCUMENT DOWNLOAD
# --------------------------------------------------

@app.route("/admin/document/<int:doc_id>")
@admin_required
def download_document(doc_id):

    with db() as conn:

        doc = conn.execute(
            "SELECT * FROM documents WHERE id = ?",
            (doc_id,)
        ).fetchone()

    if not doc:
        abort(404)

    path = PRIVATE_UPLOADS / doc["stored_name"]

    if not path.is_file():
        abort(404)

    return send_file(
        path,
        as_attachment=True,
        download_name=doc["original_name"]
    )


# --------------------------------------------------
# 15. DELETE STUDENT APPLICATION
# --------------------------------------------------

@app.route(
    "/admin/delete/<int:app_id>",
    methods=["POST"]
)
@admin_required
def delete_application(app_id):

    with db() as conn:

        docs = conn.execute(
            """
            SELECT stored_name FROM documents
            WHERE application_id = ?
            """,
            (app_id,)
        ).fetchall()

        conn.execute(
            "DELETE FROM documents WHERE application_id = ?",
            (app_id,)
        )

        conn.execute(
            "DELETE FROM applications WHERE id = ?",
            (app_id,)
        )

    for doc in docs:

        path = PRIVATE_UPLOADS / doc["stored_name"]

        if path.exists():
            path.unlink()

    flash(
        "Application deleted.",
        "success"
    )

    return redirect(url_for("dashboard"))


# --------------------------------------------------
# 16. FILE SIZE ERROR
# --------------------------------------------------

@app.errorhandler(413)
def too_large(_error):

    return (
        "Upload too large. Maximum request size is 25 MB.",
        413
    )


# --------------------------------------------------
# 17. INITIALIZE DATABASE
# --------------------------------------------------

init_db()


# --------------------------------------------------
# 18. RUN LOCAL SERVER
# --------------------------------------------------

if __name__ == "__main__":

    app.run(debug=True)