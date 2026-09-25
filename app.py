"""
Web Chu Chay Cho Video - server Flask.

Nguoi dung tai video len + nhap chu -> server (Render) dung FFmpeg
dong chu hoat hinh vao video -> nguoi dung tai ket qua ve.
Máy yếu cũng chạy được vi moi viec nang deu o phía server.
"""

from __future__ import annotations

import os
import re
import uuid

from flask import Flask, jsonify, render_template, request, send_file

from renderer import engine, presets

app = Flask(__name__)

MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", 250))
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024

ALLOWED_EXT = {
    "mp4", "mov", "webm", "mkv", "avi", "m4v", "3gp", "ts", "flv", "wmv", "mpg", "mpeg",
}
HEX_RE = re.compile(r"^#?[0-9a-fA-F]{6}$")

FONTS = list(presets.FONT_FILES.keys())
POSITIONS = [("top", "Tren cung"), ("middle", "Giua"), ("bottom", "Duoi cung")]
MAX_TEXT = 160


def _clamp(val, lo, hi, default):
    try:
        v = float(val)
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, v))


@app.get("/")
def index():
    return render_template(
        "index.html",
        presets=presets.PRESET_INFO,
        fonts=FONTS,
        positions=POSITIONS,
        max_upload_mb=MAX_UPLOAD_MB,
        max_text=MAX_TEXT,
    )


@app.get("/api/health")
def health():
    return jsonify({"ok": True, "ffmpeg": bool(engine.FFMPEG)})


@app.post("/api/render")
def render():
    f = request.files.get("video")
    if not f or not f.filename:
        return jsonify({"error": "Ban chua chon file video"}), 400

    ext = f.filename.rsplit(".", 1)[-1].lower() if "." in f.filename else ""
    if ext not in ALLOWED_EXT:
        return jsonify({"error": f"Dinh dang .{ext or '?'} khong duoc ho tro. Hay dung mp4/mov/webm..."}), 400

    text = (request.form.get("text") or "").strip()
    if not text:
        return jsonify({"error": "Ban chua nhap noi dung chu"}), 400
    if len(text) > MAX_TEXT:
        return jsonify({"error": f"Chu qua dai (toi da {MAX_TEXT} ky tu)"}), 400

    params = {
        "text": text,
        "preset": request.form.get("preset", "pop") if request.form.get("preset", "pop") in presets._PRESETS else "pop",
        "font": request.form.get("font", "Be Vietnam Pro") if request.form.get("font", "Be Vietnam Pro") in FONTS else FONTS[0],
        "size": _clamp(request.form.get("size"), 3, 14, 6.5),
        "duration": _clamp(request.form.get("duration"), 0.5, 10, 3.0),
        "color": request.form.get("color", "#FFFFFF") if HEX_RE.match(request.form.get("color") or "") else "#FFFFFF",
        "highlight": request.form.get("highlight", "#FFE933") if HEX_RE.match(request.form.get("highlight") or "") else "#FFE933",
        "position": request.form.get("position", "middle") if request.form.get("position", "middle") in dict(POSITIONS) else "middle",
    }

    fname = uuid.uuid4().hex + "." + ext
    path = os.path.join(engine.UPLOAD_DIR, fname)
    f.save(path)  # werkzeug ghi ra dia, khong giu trong RAM
    if os.path.getsize(path) == 0:
        os.remove(path)
        return jsonify({"error": "File rong, thu lai"}), 400

    job_id = engine.submit(path, params)
    return jsonify({"job_id": job_id})


@app.get("/api/status/<job_id>")
def status(job_id):
    job = engine.get(job_id)
    if not job:
        return jsonify({"error": "Khong tim thay cong viec"}), 404
    return jsonify(job)


@app.get("/api/download/<job_id>")
def download(job_id):
    path = engine.output_path(job_id)
    if not path or not os.path.exists(path):
        return jsonify({"error": "File khong con tren server (da tu dong xoa sau 3 tieng)"}), 410
    return send_file(path, mimetype="video/mp4", as_attachment=True,
                     download_name="video-chu-chay.mp4")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
