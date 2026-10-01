"""Portfolio site server, sized for Azure App Service (Linux, Python).

Pages are rendered on the server from Jinja templates in templates/, filled
from a small JSON store on the persistent volume, so every section can be
edited at /admin without touching code or redeploying. See content_schema.py
for the collections.

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

from flask import Flask, Response, jsonify, render_template, request, send_from_directory, session
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.utils import secure_filename

import content_fixes
from content_schema import CERT_CATEGORIES, EXPERIENCE_GROUPS, SCHEMA, SEPARATE_FILES

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

app = Flask(__name__, static_folder=None, template_folder=os.path.join(ROOT, "templates"))
# App Service terminates TLS in front of gunicorn and forwards the original scheme and host.
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
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


def _seed_content():
    seed = _read_json(CONTENT_SEED, {})
    return seed if isinstance(seed, dict) else {}


def load_collection(name):
    _ensure_store()
    if name in SEPARATE_FILES:
        data = _read_json(CERTS_FILE, [])
        return data if isinstance(data, list) else []

    content = _read_json(CONTENT_FILE, {})
    if not isinstance(content, dict):
        content = {}
    seed = _seed_content().get(name, [])

    # A collection added after the store was created falls back to the seed.
    if name not in content:
        return seed if isinstance(seed, list) else []

    items = content.get(name)
    if not isinstance(items, list):
        return []

    # Fields added later are filled from the matching seed entry, but anything
    # already stored - including a value deliberately left blank - wins.
    seed_by_id = {entry.get("id"): entry for entry in seed if isinstance(entry, dict)}
    merged = []
    for item in items:
        defaults = seed_by_id.get(item.get("id"))
        merged.append({**defaults, **item} if defaults else item)
    return content_fixes.apply(name, merged)


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


def _raw_load(name):
    _ensure_store()
    if name in SEPARATE_FILES:
        data = _read_json(CERTS_FILE, [])
        return data if isinstance(data, list) else []
    content = _read_json(CONTENT_FILE, {})
    items = content.get(name, []) if isinstance(content, dict) else []
    return items if isinstance(items, list) else []


try:
    content_fixes.run_migrations(_raw_load, save_collection, os.path.join(DATA_DIR, "migrations.json"))
except OSError:
    pass  # a read-only or missing volume must not stop the site from serving


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


def _file_fields(collection):
    return [f["name"] for f in SCHEMA[collection]["fields"] if f["type"] == "file"]


def _store_uploads(collection, item):
    """Save any uploaded files for this item. Returns an error message or None."""
    for field in _file_fields(collection):
        upload = request.files.get(field)
        if not upload or not upload.filename:
            continue
        ext = os.path.splitext(upload.filename)[1].lower()
        if ext not in ALLOWED_EXT:
            return "Allowed file types: PNG, JPG, WEBP, GIF, PDF."
        _ensure_store()
        previous = item.get(field)
        stored = secure_filename("%s-%s-%s%s" % (item["id"], field, uuid.uuid4().hex[:6], ext))
        upload.save(os.path.join(UPLOAD_DIR, stored))
        item[field] = "/uploads/" + stored
        _remove_upload(previous)
    return None


def _remove_upload(url):
    if not url or not str(url).startswith("/uploads/"):
        return
    path = os.path.join(UPLOAD_DIR, os.path.basename(url))
    if os.path.isfile(path):
        os.remove(path)


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

    error = _store_uploads(collection, item)
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

        error = _store_uploads(collection, item)
        if error:
            return jsonify(error=error), 400

        # "Remove" ticks on file fields clear the stored file.
        for field in _file_fields(collection):
            if request.form.get("remove_" + field) == "1" and not request.files.get(field):
                _remove_upload(item.get(field))
                item[field] = ""

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
        if item.get("id") == item_id:
            for field in _file_fields(collection):
                _remove_upload(item.get(field))

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
        categories=CERT_CATEGORIES,
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
    return _render("admin.html", "admin")


# --------------------------------------------------------------------------
# Pages
# --------------------------------------------------------------------------

PAGE_TEMPLATES = {
    "education": "Education",
    "experience": "Experience",
    "projects": "Projects",
    "certifications": "Certifications",
    "contact": "Contact",
}


def asset_version():
    """Build id for asset URLs, so a deployment never serves stale CSS or JS."""
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


@app.context_processor
def _template_globals():
    version = asset_version()
    root = request.url_root.rstrip("/")
    path = request.path
    if path.endswith(".html"):
        path = "/" if path == "/index.html" else path[:-5]
    return {
        "asset": lambda p: "/assets/%s?v=%s" % (p, version),
        "absolute": lambda p: root + p,
        "canonical": root + path,
        "year": datetime.now(timezone.utc).year,
    }


@app.template_filter("slug")
def _slug_filter(text):
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")


@app.template_filter("paragraphs")
def _paragraphs(text):
    return [chunk.strip() for chunk in re.split(r"\n\s*\n", text or "") if chunk.strip()]


def _grouped(items, key, order):
    groups = {}
    for item in items:
        groups.setdefault(item.get(key) or order[-1], []).append(item)
    names = [name for name in order if name in groups]
    names += [name for name in groups if name not in names]
    return [(name, groups[name]) for name in names]


def _render(template, page):
    content = load_all()
    intro = next((p for p in content.get("pages", []) if p.get("page") == PAGE_TEMPLATES.get(page)), {})
    html = render_template(
        template,
        page=page,
        c=content,
        profile=(content.get("profile") or [{}])[0],
        contact=(content.get("contact") or [{}])[0],
        intro=intro,
        experience_groups=_grouped(content.get("experience", []), "group", EXPERIENCE_GROUPS),
        cert_groups=_grouped(content.get("certifications", []), "category", CERT_CATEGORIES),
    )
    response = Response(html, mimetype="text/html")
    response.headers["Cache-Control"] = "no-cache"
    return response


@app.route("/")
@app.route("/index.html")
def home():
    return _render("index.html", "home")


@app.route("/<slug>")
def page(slug):
    key = slug[:-5] if slug.endswith(".html") else slug
    if key not in PAGE_TEMPLATES:
        return _not_found(None)
    return _render(key + ".html", key)


@app.route("/assets/<path:path>")
def assets(path):
    response = send_from_directory(os.path.join(ROOT, "assets"), path)
    # Safe to cache hard: page markup stamps every CSS/JS URL with a version.
    response.headers["Cache-Control"] = "public, max-age=604800"
    return response


CSP = "; ".join([
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self' https://fonts.googleapis.com 'unsafe-inline'",
    "font-src https://fonts.gstatic.com",
    "img-src 'self' data:",
    "connect-src 'self'",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
])


@app.after_request
def _security_headers(response):
    response.headers.setdefault("Content-Security-Policy", CSP)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    if request.is_secure:
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response


@app.route("/robots.txt")
def robots():
    lines = [
        "User-agent: *",
        "Disallow: /admin",
        "Disallow: /api/",
        "Sitemap: %s/sitemap.xml" % request.url_root.rstrip("/"),
    ]
    return Response("\n".join(lines) + "\n", mimetype="text/plain")


@app.route("/sitemap.xml")
def sitemap():
    root = request.url_root.rstrip("/")
    urls = [root + "/"] + [root + "/" + key for key in PAGE_TEMPLATES]
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    lines += ["  <url><loc>%s</loc></url>" % url for url in urls]
    lines.append("</urlset>")
    return Response("\n".join(lines) + "\n", mimetype="application/xml")


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


@app.errorhandler(413)
def _too_large(_error):
    return jsonify(error="That file is larger than 8 MB."), 413


@app.errorhandler(404)
def _not_found(_error):
    try:
        html = render_template("404.html", page="404", profile={}, contact={})
    except Exception:  # never let the error page itself fail
        html = "<!doctype html><title>Not found</title><p>That page does not exist. <a href='/'>Home</a></p>"
    return Response(html, status=404, mimetype="text/html")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    app.run(host="0.0.0.0", port=port, debug=False)
