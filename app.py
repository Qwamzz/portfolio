"""Minimal static-file server for the portfolio, sized for Azure App Service (Linux, Python).

App Service runs this with gunicorn (see the startup command in DEPLOY.md), which needs a
WSGI callable named `app`. Everything else is plain static HTML, CSS, JS and SVG.
"""

import mimetypes
import os

from flask import Flask, Response, send_from_directory

ROOT = os.path.dirname(os.path.abspath(__file__))

# Some Windows registries report the wrong type for these; be explicit.
mimetypes.add_type("image/svg+xml", ".svg")
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("application/javascript", ".js")

app = Flask(__name__, static_folder=None)

# Pages that may be reached without the .html suffix.
PAGES = ("index", "education", "experience", "projects", "certifications", "contact")


def _send(relpath):
    response = send_from_directory(ROOT, relpath)
    if relpath.startswith("assets/"):
        response.headers["Cache-Control"] = "public, max-age=86400"
    else:
        response.headers["Cache-Control"] = "no-cache"
    return response


@app.route("/")
def home():
    return _send("index.html")


@app.route("/healthz")
def healthz():
    return {"status": "ok"}


@app.route("/<path:path>")
def static_files(path):
    candidate = os.path.normpath(os.path.join(ROOT, path))
    # Never serve anything outside the site directory.
    if not candidate.startswith(ROOT):
        return _not_found(None)

    if os.path.isfile(candidate):
        return _send(path)

    # Allow /projects as well as /projects.html
    if path.rstrip("/") in PAGES and os.path.isfile(candidate.rstrip(os.sep) + ".html"):
        return _send(path.rstrip("/") + ".html")

    return _not_found(None)


@app.errorhandler(404)
def _not_found(_error):
    body = (
        "<!doctype html><meta charset='utf-8'>"
        "<title>Page not found</title>"
        "<style>body{font-family:Segoe UI,Arial,sans-serif;background:#edf7fe;color:#0b2545;"
        "display:flex;min-height:100vh;align-items:center;justify-content:center;text-align:center}"
        "a{color:#1573c4}</style>"
        "<div><h1>404</h1><p>That page does not exist.</p>"
        "<p><a href='/'>Back to the portfolio</a></p></div>"
    )
    return Response(body, status=404, mimetype="text/html")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    app.run(host="0.0.0.0", port=port, debug=False)
