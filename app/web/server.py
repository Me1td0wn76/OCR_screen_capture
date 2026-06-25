"""Local Flask server hosting the setup wizard and settings page.

Binds to 127.0.0.1 on a free port and runs in a background daemon thread. The
pages are shown inside a native pywebview window (no browser), so the server is
only ever consumed by the embedded WebView on localhost.
"""
from __future__ import annotations

import logging
import socket
import threading
from typing import Any

from flask import Flask, jsonify, redirect, request, send_from_directory, url_for

from ..paths import web_dir

log = logging.getLogger(__name__)


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class WebServer:
    def __init__(self, controller):
        self.c = controller
        self.host = "127.0.0.1"
        self.port = _find_free_port()
        self._dl_lock = threading.Lock()
        self._dl: dict[str, Any] = {"status": "idle", "language": None, "done": 0, "total": 0}

        base = web_dir()
        self.app = Flask(
            __name__,
            static_folder=str(base / "static"),
        )
        # Built Svelte SPA (app/web/static/dist/index.html). The /setup and
        # /settings routes both return it; the front-end decides which view to
        # render from the URL path.
        self._dist = base / "static" / "dist"
        logging.getLogger("werkzeug").setLevel(logging.WARNING)
        self._register_routes()

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def start(self) -> None:
        threading.Thread(target=self._serve, name="web-server", daemon=True).start()

    def _serve(self) -> None:
        self.app.run(host=self.host, port=self.port, threaded=True,
                     debug=False, use_reloader=False)

    def _register_routes(self) -> None:
        app = self.app
        c = self.c

        @app.route("/")
        def index():
            if c.cfg.get("setup_completed") and c._current_model_available():
                return redirect(url_for("settings_page"))
            return redirect(url_for("setup_page"))

        @app.route("/setup")
        def setup_page():
            return send_from_directory(self._dist, "index.html")

        @app.route("/settings")
        def settings_page():
            return send_from_directory(self._dist, "index.html")

        @app.route("/api/status")
        def api_status():
            return jsonify(c.get_status())

        @app.route("/api/settings", methods=["POST"])
        def api_settings():
            c.apply_settings(request.get_json(force=True) or {})
            return jsonify({"ok": True, "status": c.get_status()})

        @app.route("/api/setup", methods=["POST"])
        def api_setup():
            data = request.get_json(force=True) or {}
            c.complete_setup(data.get("language", "japan"), data.get("model_dir") or None)
            return jsonify({"ok": True, "status": c.get_status()})

        @app.route("/api/download", methods=["POST"])
        def api_download():
            data = request.get_json(force=True) or {}
            language = data.get("language", "japan")
            if data.get("model_dir"):
                c.apply_settings({"model_dir": data["model_dir"]})
            with self._dl_lock:
                if self._dl["status"] == "running":
                    return jsonify({"ok": False, "error": "別のダウンロードが進行中です"}), 409
                self._dl = {"status": "running", "language": language, "done": 0, "total": 0}
            threading.Thread(target=self._run_download, args=(language,),
                             name="model-dl", daemon=True).start()
            return jsonify({"ok": True})

        @app.route("/api/download/status")
        def api_download_status():
            with self._dl_lock:
                return jsonify(dict(self._dl))

        @app.route("/api/action/<name>", methods=["POST"])
        def api_action(name: str):
            actions = {
                "ocr_clipboard": c.manual_ocr_from_clipboard,
                "speak_last": c.speak_last,
                "translate_last": c.translate_last,
            }
            fn = actions.get(name)
            if not fn:
                return jsonify({"ok": False, "error": "unknown action"}), 404
            fn()
            return jsonify({"ok": True, "last_text": c.last_text})

    def _run_download(self, language: str) -> None:
        def progress(done: int, total: int) -> None:
            with self._dl_lock:
                self._dl["done"] = done
                self._dl["total"] = total
        try:
            self.c.download_model(language, progress)
            self.c.ocr.reload()
            with self._dl_lock:
                self._dl["status"] = "done"
        except Exception as e:
            log.exception("model download failed")
            with self._dl_lock:
                self._dl["status"] = "error"
                self._dl["error"] = str(e)
