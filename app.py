"""Portfolio site server, sized for Azure App Service (Linux, Python).

Mostly it serves static HTML, CSS, JS and SVG. On top of that it keeps the
certifications list in a JSON file so new certificates can be added through
/admin without editing any code or redeploying.

App Service runs this with gunicorn (see DEPLOY.md), which needs a WSGI
callable named `app`.
"""

import hmac
import json
import mimetypes
import os
import re
import secrets
import shutil
import time
import uuid
from datetime import datetime, timezone

from flask import (Flask, Response, jsonify, request, send_from_directory,
                   session)
from werkzeug.utils import secure_filename

ROOT = os.path.dirname(os.path.abspath(__file__))

# /home is the persistent volume on App Service; anything written to the site
# directory is replaced on the next deployment.
if os.path.isdir("/home") and os.access("/home", os.W_OK):
    DATA_DIR = os.environ.get("DATA_DIR", "/home/data")
else:
    DATA_DIR = os.environ.get("DATA_DIR", os.path.join(ROOT, "data", "store"))

UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
CERTS_FILE = os.path.join(DATA_DIR, "certifications.json")
SEED_FILE = os.path.join(ROOT, "data", "certifications.seed.json")

ALLOWED_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".pdf"}
CATEGORIES = ["Microsoft", "Cloud & Cloud Native", "Security & Standards", "Other"]
MAX_UPLOAD_BYTES = 8 * 1024 * 1024

mimetypes.add_type("image/svg+xml", ".svg")
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("application/javascript", ".js")

app = Flask(__name__, static_folder=None)
app.config.update(
    MAX_CONTENT_LENGTH=MAX_UPLOAD_BYTES,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("WEBSITE_HOSTNAME") is not None,
)
# A generated key logs the admin out on restart, which is an acceptable default;
# set SECRET_KEY in the app settings to keep sessions across restarts.
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")

PAGES = ("index", "education", "experience", "projects", "certifications", "contact")

# Crude in-process throttle so the login form cannot be hammered.
_failures = {}


# --------------------------------------------------------------------------
# Storage
# --------------------------------------------------------------------------

def _ensure_store():
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    if not os.path.isfile(CERTS_FILE) and os.path.isfile(SEED_FILE):
        shutil.copyfile(SEED_FILE, CERTS_FILE)


def load_certifications():
    _ensure_store()
    try:
        with open(CERTS_FILE, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, list) else []
    except (OSError, ValueError):
        return []


def save_certifications(items):
    _ensure_store()
    tmp = CERTS_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(items, handle, indent=2, ensure_ascii=False)
    os.replace(tmp, CERTS_FILE)


def _slug(value):
    value = re.sub(r"[^a-z0-9]+", "-", (value or "").lower()).strip("-")
    return value[:48] or uuid.uuid4().hex[:8]


# --------------------------------------------------------------------------
# Auth helpers
# --------------------------------------------------------------------------

def admin_enabled():
    return bool(ADMIN_PASSWORD)


def is_admin():
    return session.get("admin") is True


def require_admin():
    """Return an error response when the caller may not write, else None."""
    if not admin_enabled():
        return jsonify(error="Admin is disabled. Set ADMIN_PASSWORD to enable it."), 503
    if not is_admin():
        return jsonify(error="Not signed in."), 401
    return None


def _throttled(key):
    record = _failures.get(key)
    if not record:
        return False
    count, last = record
    if count < 5:
        return False
    return (time.time() - last) < 300


# --------------------------------------------------------------------------
# Static site
# --------------------------------------------------------------------------

def _send(relpath):
    response = send_from_directory(ROOT, relpath)
    if relpath.startswith("assets/"):
        response.headers["Cache-Control"] = "public, max-age=3600"
    else:
        response.headers["Cache-Control"] = "no-cache"
    return response


@app.route("/")
def home():
    return _send("index.html")


@app.route("/healthz")
def healthz():
    return {"status": "ok", "certifications": len(load_certifications())}


@app.route("/uploads/<path:name>")
def uploaded_file(name):
    safe = secure_filename(name)
    if not safe or not os.path.isfile(os.path.join(UPLOAD_DIR, safe)):
        return _not_found(None)
    response = send_from_directory(UPLOAD_DIR, safe)
    response.headers["Cache-Control"] = "public, max-age=86400"
    return response


# --------------------------------------------------------------------------
# Certifications API
# --------------------------------------------------------------------------

@app.route("/api/certifications")
def api_certifications():
    return jsonify(
        categories=CATEGORIES,
        items=load_certifications(),
        admin=is_admin(),
        adminEnabled=admin_enabled(),
    )


@app.route("/api/certifications", methods=["POST"])
def api_add_certification():
    denied = require_admin()
    if denied:
        return denied

    form = request.form
    name = (form.get("name") or "").strip()
    if not name:
        return jsonify(error="A certification name is required."), 400

    category = form.get("category") or CATEGORIES[-1]
    if category not in CATEGORIES:
        category = CATEGORIES[-1]

    item = {
        "id": _slug(form.get("code") or name) + "-" + uuid.uuid4().hex[:4],
        "name": name[:160],
        "code": (form.get("code") or "").strip()[:12] or "CERT",
        "issuer": (form.get("issuer") or "").strip()[:80],
        "category": category,
        "note": (form.get("note") or "").strip()[:120],
        "url": (form.get("url") or "").strip()[:400],
        "added": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }

    if item["url"] and not item["url"].startswith(("http://", "https://")):
        return jsonify(error="The credential link must start with http:// or https://"), 400

    upload = request.files.get("file")
    if upload and upload.filename:
        ext = os.path.splitext(upload.filename)[1].lower()
        if ext not in ALLOWED_EXT:
            return jsonify(error="Allowed file types: PNG, JPG, WEBP, GIF, PDF."), 400
        _ensure_store()
        stored = item["id"] + ext
        upload.save(os.path.join(UPLOAD_DIR, stored))
        item["file"] = "/uploads/" + stored

    items = load_certifications()
    items.append(item)
    save_certifications(items)
    return jsonify(item=item), 201


@app.route("/api/certifications/<cert_id>", methods=["DELETE"])
def api_delete_certification(cert_id):
    denied = require_admin()
    if denied:
        return denied

    items = load_certifications()
    remaining = [c for c in items if c.get("id") != cert_id]
    if len(remaining) == len(items):
        return jsonify(error="No certification with that id."), 404

    for cert in items:
        if cert.get("id") == cert_id and cert.get("file"):
            path = os.path.join(UPLOAD_DIR, os.path.basename(cert["file"]))
            if os.path.isfile(path):
                os.remove(path)

    save_certifications(remaining)
    return jsonify(ok=True)


# --------------------------------------------------------------------------
# Admin session
# --------------------------------------------------------------------------

@app.route("/api/admin/session")
def api_admin_session():
    return jsonify(admin=is_admin(), adminEnabled=admin_enabled())


@app.route("/api/admin/login", methods=["POST"])
def api_admin_login():
    if not admin_enabled():
        return jsonify(error="Admin is disabled. Set ADMIN_PASSWORD to enable it."), 503

    key = request.remote_addr or "unknown"
    if _throttled(key):
        return jsonify(error="Too many attempts. Try again in a few minutes."), 429

    supplied = (request.get_json(silent=True) or {}).get("password", "")
    if hmac.compare_digest(str(supplied), ADMIN_PASSWORD):
        _failures.pop(key, None)
        session["admin"] = True
        session.permanent = False
        return jsonify(admin=True)

    count = _failures.get(key, (0, 0))[0] + 1
    _failures[key] = (count, time.time())
    return jsonify(error="Incorrect password."), 401


@app.route("/api/admin/logout", methods=["POST"])
def api_admin_logout():
    session.clear()
    return jsonify(admin=False)


@app.route("/admin")
def admin_page():
    return _send("admin.html")


# --------------------------------------------------------------------------
# Catch-all and errors
# --------------------------------------------------------------------------

@app.route("/<path:path>")
def static_files(path):
    candidate = os.path.normpath(os.path.join(ROOT, path))
    if not candidate.startswith(ROOT):
        return _not_found(None)

    if os.path.isfile(candidate):
        return _send(path)

    if path.rstrip("/") in PAGES and os.path.isfile(candidate.rstrip(os.sep) + ".html"):
        return _send(path.rstrip("/") + ".html")

    return _not_found(None)


@app.errorhandler(413)
def _too_large(_error):
    return jsonify(error="That file is larger than 8 MB."), 413


@app.errorhandler(404)
def _not_found(_error):
    body = (
        "<!doctype html><meta charset='utf-8'>"
        "<title>Page not found</title>"
        "<style>body{font-family:Segoe UI,Arial,sans-serif;background:#0d0b1a;color:#edeaff;"
        "display:flex;min-height:100vh;align-items:center;justify-content:center;text-align:center}"
        "a{color:#19e3c0}</style>"
        "<div><h1>404</h1><p>That page does not exist.</p>"
        "<p><a href='/'>Back to the portfolio</a></p></div>"
    )
    return Response(body, status=404, mimetype="text/html")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    app.run(host="0.0.0.0", port=port, debug=False)
