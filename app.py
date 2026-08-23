"""Portfolio site server, sized for Azure App Service (Linux, Python).

The pages are static HTML, CSS, JS and SVG. Their content comes from a small
JSON store on the persistent volume, so every section can be edited at /admin
without touching code or redeploying. See content_schema.py for the collections.

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

from flask import Flask, Response, jsonify, request, send_from_directory, session
from werkzeug.utils import secure_filename

from content_schema import SCHEMA, SEPARATE_FILES

ROOT = os.path.dirname(os.path.abspath(__file__))

# /home is the persistent volume on App Service; the site directory is replaced
# on every deployment, so nothing editable may live there.
if os.path.isdir("/home") and os.access("/home", os.W_OK):
    DATA_DIR = os.environ.get("DATA_DIR", "/home/data")
else:
    DATA_DIR = os.environ.get("DATA_DIR", os.path.join(ROOT, "data", "store"))

UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
CONTENT_FILE = os.path.join(DATA_DIR, "content.json")
CERTS_FILE = os.path.join(DATA_DIR, "certifications.json")
CONTENT_SEED = os.path.join(ROOT, "data", "content.seed.json")
CERTS_SEED = os.path.join(ROOT, "data", "certifications.seed.json")

ALLOWED_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".pdf"}
MAX_UPLOAD_BYTES = 8 * 1024 * 1024
MAX_FIELD_LEN = 6000

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
# Keep the schema in the order it is declared so the admin menu reads Home first.
app.json.sort_keys = False

app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")

PAGES = ("index", "education", "experience", "projects", "certifications", "contact")

_failures = {}


# --------------------------------------------------------------------------
# Storage
# --------------------------------------------------------------------------

def _ensure_store():
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    if not os.path.isfile(CERTS_FILE) and os.path.isfile(CERTS_SEED):
        shutil.copyfile(CERTS_SEED, CERTS_FILE)
    if not os.path.isfile(CONTENT_FILE) and os.path.isfile(CONTENT_SEED):
        shutil.copyfile(CONTENT_SEED, CONTENT_FILE)


def _read_json(path, fallback):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return fallback


def _write_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def load_collection(name):
    _ensure_store()
    if name in SEPARATE_FILES:
        data = _read_json(CERTS_FILE, [])
        return data if isinstance(data, list) else []
    content = _read_json(CONTENT_FILE, {})
    items = content.get(name, []) if isinstance(content, dict) else []
    return items if isinstance(items, list) else []


def save_collection(name, items):
    _ensure_store()
    if name in SEPARATE_FILES:
        _write_json(CERTS_FILE, items)
        return
    content = _read_json(CONTENT_FILE, {})
    if not isinstance(content, dict):
        content = {}
    content[name] = items
    _write_json(CONTENT_FILE, content)


def load_all():
    return {name: load_collection(name) for name in SCHEMA}


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------

def _slug(value):
    value = re.sub(r"[^a-z0-9]+", "-", (value or "").lower()).strip("-")
    return value[:40] or uuid.uuid4().hex[:8]


def clean_item(collection, form, existing=None):
    """Build an item from submitted form data. Returns (item, error)."""
    spec = SCHEMA[collection]
    item = dict(existing or {})

    for field in spec["fields"]:
        name = field["name"]
        if field["type"] == "file":
            continue
        if name not in form and existing is not None:
            continue

        raw = (form.get(name) or "").strip()
        if len(raw) > MAX_FIELD_LEN:
            return None, "%s is too long." % field["label"]

        if field["type"] == "lines":
            item[name] = [line.strip() for line in raw.splitlines() if line.strip()]
        elif field["type"] == "select":
            options = field.get("options", [])
            item[name] = raw if raw in options else (options[0] if options else raw)
        elif field["type"] == "url":
            if raw and not raw.startswith(("http://", "https://")):
                return None, "%s must start with http:// or https://" % field["label"]
            item[name] = raw
        else:
            item[name] = raw

        if field.get("required") and not item.get(name):
            return None, "%s is required." % field["label"]

    return item, None


def _store_upload(collection, item, upload):
    ext = os.path.splitext(upload.filename)[1].lower()
    if ext not in ALLOWED_EXT:
        return "Allowed file types: PNG, JPG, WEBP, GIF, PDF."
    _ensure_store()
    stored = secure_filename(item["id"] + ext)
    upload.save(os.path.join(UPLOAD_DIR, stored))
    item["file"] = "/uploads/" + stored
    return None


# --------------------------------------------------------------------------
# Auth
# --------------------------------------------------------------------------

def admin_enabled():
    return bool(ADMIN_PASSWORD)


def is_admin():
    return session.get("admin") is True


def require_admin():
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
    return count >= 5 and (time.time() - last) < 300


# --------------------------------------------------------------------------
# Content API
# --------------------------------------------------------------------------

@app.route("/api/content")
def api_content():
    return jsonify(content=load_all(), admin=is_admin(), adminEnabled=admin_enabled())


@app.route("/api/schema")
def api_schema():
    return jsonify(schema=SCHEMA, admin=is_admin(), adminEnabled=admin_enabled())


@app.route("/api/content/<collection>")
def api_collection(collection):
    if collection not in SCHEMA:
        return jsonify(error="Unknown collection."), 404
    return jsonify(items=load_collection(collection))


@app.route("/api/content/<collection>", methods=["POST"])
def api_create(collection):
    denied = require_admin()
    if denied:
        return denied
    if collection not in SCHEMA:
        return jsonify(error="Unknown collection."), 404

    spec = SCHEMA[collection]
    items = load_collection(collection)
    if spec.get("single") and items:
        return jsonify(error="This section holds a single entry - edit the existing one."), 400

    item, error = clean_item(collection, request.form)
    if error:
        return jsonify(error=error), 400

    item["id"] = _slug(item.get(spec["title_field"], collection)) + "-" + uuid.uuid4().hex[:4]
    item["added"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    upload = request.files.get("file")
    if upload and upload.filename:
        error = _store_upload(collection, item, upload)
        if error:
            return jsonify(error=error), 400

    items.append(item)
    save_collection(collection, items)
    return jsonify(item=item), 201


@app.route("/api/content/<collection>/<item_id>", methods=["PUT", "POST"])
def api_update(collection, item_id):
    denied = require_admin()
    if denied:
        return denied
    if collection not in SCHEMA:
        return jsonify(error="Unknown collection."), 404

    items = load_collection(collection)
    for index, existing in enumerate(items):
        if existing.get("id") != item_id:
            continue

        item, error = clean_item(collection, request.form, existing)
        if error:
            return jsonify(error=error), 400

        upload = request.files.get("file")
        if upload and upload.filename:
            error = _store_upload(collection, item, upload)
            if error:
                return jsonify(error=error), 400

        items[index] = item
        save_collection(collection, items)
        return jsonify(item=item)

    return jsonify(error="No entry with that id."), 404


@app.route("/api/content/<collection>/<item_id>", methods=["DELETE"])
def api_delete(collection, item_id):
    denied = require_admin()
    if denied:
        return denied
    if collection not in SCHEMA:
        return jsonify(error="Unknown collection."), 404

    items = load_collection(collection)
    remaining = [i for i in items if i.get("id") != item_id]
    if len(remaining) == len(items):
        return jsonify(error="No entry with that id."), 404

    for item in items:
        if item.get("id") == item_id and item.get("file"):
            path = os.path.join(UPLOAD_DIR, os.path.basename(item["file"]))
            if os.path.isfile(path):
                os.remove(path)

    save_collection(collection, remaining)
    return jsonify(ok=True)


@app.route("/api/content/<collection>/<item_id>/move", methods=["POST"])
def api_move(collection, item_id):
    denied = require_admin()
    if denied:
        return denied
    if collection not in SCHEMA:
        return jsonify(error="Unknown collection."), 404

    direction = (request.get_json(silent=True) or {}).get("direction", "up")
    items = load_collection(collection)
    for index, item in enumerate(items):
        if item.get("id") != item_id:
            continue
        target = index - 1 if direction == "up" else index + 1
        if target < 0 or target >= len(items):
            return jsonify(ok=True)
        items[index], items[target] = items[target], items[index]
        save_collection(collection, items)
        return jsonify(ok=True)

    return jsonify(error="No entry with that id."), 404


# Kept so anything pointing at the old endpoint keeps working.
@app.route("/api/certifications")
def api_certifications():
    return jsonify(
        categories=SCHEMA["certifications"]["fields"][3]["options"],
        items=load_collection("certifications"),
        admin=is_admin(),
        adminEnabled=admin_enabled(),
    )


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
# Static site
# --------------------------------------------------------------------------

_ASSET_RE = re.compile(r'(assets/(?:css|js)/[\w.-]+\.(?:css|js))"')


def asset_version():
    """Stamp asset URLs with a build id so a deployment never serves stale CSS or JS."""
    newest = 0
    for folder in ("assets/css", "assets/js"):
        directory = os.path.join(ROOT, folder)
        if not os.path.isdir(directory):
            continue
        for name in os.listdir(directory):
            try:
                newest = max(newest, os.path.getmtime(os.path.join(directory, name)))
            except OSError:
                pass
    return str(int(newest))


def _send(relpath):
    if relpath.endswith(".html"):
        with open(os.path.join(ROOT, relpath), "r", encoding="utf-8") as handle:
            markup = handle.read()
        markup = _ASSET_RE.sub(lambda m: m.group(1) + '?v=' + asset_version() + chr(34), markup)
        response = Response(markup, mimetype="text/html")
        response.headers["Cache-Control"] = "no-cache"
        return response

    response = send_from_directory(ROOT, relpath)
    if relpath.startswith("assets/"):
        # Safe to cache hard: the URLs carry a version stamp.
        response.headers["Cache-Control"] = "public, max-age=604800"
    else:
        response.headers["Cache-Control"] = "no-cache"
    return response


@app.route("/")
def home():
    return _send("index.html")


@app.route("/healthz")
def healthz():
    return {"status": "ok", "certifications": len(load_collection("certifications"))}


@app.route("/uploads/<path:name>")
def uploaded_file(name):
    safe = secure_filename(name)
    if not safe or not os.path.isfile(os.path.join(UPLOAD_DIR, safe)):
        return _not_found(None)
    response = send_from_directory(UPLOAD_DIR, safe)
    response.headers["Cache-Control"] = "public, max-age=86400"
    return response


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
