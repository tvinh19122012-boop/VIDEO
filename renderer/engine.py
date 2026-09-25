"""
Bộ xử lý video: hàng đợi công việc + FFmpeg đốt phụ đề hoạt ảnh vào video.

Toàn bộ việc nặng (decode/encode video) chạy trên server trong luồng nền,
người dùng chỉ cần hỏi tiến độ (poll) rồi tải kết quả ve.
"""

from __future__ import annotations

import json
import logging
import os
import queue
import re
import shutil
import subprocess
import threading
import time
import uuid

from . import presets

log = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
FONTS_DIR = os.path.join(BASE_DIR, "static", "fonts")
for d in (UPLOAD_DIR, OUTPUT_DIR):
    os.makedirs(d, exist_ok=True)

# ---------------------------------------------------------------------------
# Tim ffmpeg/ffprobe: uu tien ban cai trong he thong (Docker/Render),
# fallback sang ban di kem imageio-ffmpeg khi chay local khong co ffmpeg.
# ---------------------------------------------------------------------------
FFMPEG = shutil.which("ffmpeg")
FFPROBE = shutil.which("ffprobe")
if not FFMPEG:
    try:
        import imageio_ffmpeg

        FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
        FFPROBE = imageio_ffmpeg.get_ffprobe_exe()
    except Exception:  # pragma: no cover
        pass

MAX_JOB_SECONDS = int(os.environ.get("MAX_JOB_SECONDS", 900))  # 15 phut/job
FILE_TTL = int(os.environ.get("FILE_TTL", 3 * 3600))           # giu file 3 tieng

# job_id -> dict trang thai
_JOBS: dict[str, dict] = {}
_LOCK = threading.Lock()
_QUEUE: "queue.Queue[str]" = queue.Queue()


# ---------------------------------------------------------------------------
# Tien ich
# ---------------------------------------------------------------------------
def _probe_ffmpeg(path: str) -> dict:
    """Dự phòng: đọc thông tin video bằng chính ffmpeg -i (khi không có ffprobe)"""
    if not FFMPEG:
        raise RuntimeError("Không tìm thấy ffmpeg/ffprobe trên server")
    p = subprocess.run(
        [FFMPEG, "-hide_banner", "-i", path],
        capture_output=True, text=True, timeout=180,
    )
    text = p.stderr or ""

    m = re.search(r"Duration:\s*(\d+):(\d{2}):(\d{2}(?:\.\d+)?)", text)
    duration = 0.0
    if m:
        duration = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))

    rot = 0
    mrot = re.search(r"rotation of (-?\d+(?:\.\d+)?) degrees", text)
    if mrot:
        rot = int(float(mrot.group(1))) % 360

    width = height = 0
    has_audio = False
    for line in text.splitlines():
        if "Stream" not in line:
            continue
        if "Video:" in line and not width:
            mm = re.search(r"(\d{2,5})x(\d{2,5})", line)
            if mm:
                width, height = int(mm.group(1)), int(mm.group(2))
        elif "Audio:" in line:
            has_audio = True

    if abs(rot) in (90, 270):
        width, height = height, width
    if not width or not height:
        raise RuntimeError("File không có luồng video hợp lệ")
    return {"width": width, "height": height, "duration": duration, "has_audio": has_audio}


def _probe(path: str) -> dict:
    """Đọc thông tin video (thử ffprobe trước, không được thì dùng ffmpeg)"""
    if FFPROBE:
        try:
            return _probe_json(path)
        except Exception:  # noqa: BLE001
            pass
    return _probe_ffmpeg(path)


def _probe_json(path: str) -> dict:
    """Doc thong tin video bang ffprobe"""
    cmd = [
        FFPROBE, "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", path,
    ]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if out.returncode != 0:
        raise RuntimeError("Khong doc duoc file video (co the dinh dang khong ho tro)")
    data = json.loads(out.stdout or "{}")

    width = height = 0
    duration = 0.0
    has_audio = False
    for st in data.get("streams", []):
        if st.get("codec_type") == "video" and not width:
            w, h = int(st.get("width") or 0), int(st.get("height") or 0)
            # Video quay doc con ghi metadata xoay -> doi lai cho khop hien thi
            rot = 0
            for sd in st.get("side_data_list") or []:
                if "rotation" in sd:
                    try:
                        rot = int(float(sd["rotation"])) % 360
                    except (TypeError, ValueError):
                        rot = 0
            if abs(rot) in (90, 270):
                w, h = h, w
            width, height = w, h
        elif st.get("codec_type") == "audio":
            has_audio = True
    try:
        duration = float(data.get("format", {}).get("duration") or 0)
    except (TypeError, ValueError):
        duration = 0.0
    if not width or not height:
        raise RuntimeError("File khong co luong video hop le")
    return {"width": width, "height": height, "duration": duration, "has_audio": has_audio}


def _run_ffmpeg(inp: str, ass_path: str, out: str, total: float, on_progress) -> None:
    """Chay ffmpeg, doc tien do tu -progress pipe:1"""
    vf = f"subtitles=filename='{ass_path}':fontsdir='{FONTS_DIR}'"
    cmd = [
        FFMPEG, "-y", "-hide_banner", "-nostdin", "-loglevel", "error",
        "-i", inp,
        "-map", "0:v:0", "-map", "0:a:0?",
        "-vf", vf,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
        "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.1",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        "-progress", "pipe:1",
        "-f", "mp4", out,
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    started = time.time()
    try:
        for raw in proc.stdout:
            line = raw.strip()
            if line.startswith("out_time_ms=") or line.startswith("out_time_us="):
                try:
                    key, val = line.split("=", 1)
                    secs = int(val) / (1000 if key.endswith("_ms") else 1_000_000)
                    if total > 0:
                        on_progress(min(97.0, secs / total * 100.0))
                except ValueError:
                    pass
            if time.time() - started > MAX_JOB_SECONDS:
                proc.kill()
                raise RuntimeError("Video qua dai/nang, server xu ly khong kip. Hay thu video ngan hon.")
        proc.wait(timeout=60)
    finally:
        if proc.poll() is None:
            proc.kill()
    if proc.returncode != 0:
        err = (proc.stderr.read() or "")[-800:]
        raise RuntimeError(f"FFmpeg loi: {err or 'khong ro nguyen nhan'}")
    if not os.path.exists(out) or os.path.getsize(out) == 0:
        raise RuntimeError("Khong tao duoc file ket qua")


# ---------------------------------------------------------------------------
# Worker xu ly tuan tu (Render free chi co 1 CPU/512MB nen lam lan luot cho chac)
# ---------------------------------------------------------------------------
def _process(job: dict) -> None:
    inp = job["input_path"]
    try:
        info = _probe(inp)
        dur_req = float(job["params"]["duration"])
        # Khong de chu chay qua thoi luong video
        max_dur = max(0.4, (info["duration"] or dur_req) - 0.05)
        dur = min(dur_req, max_dur)

        ass_text = presets.build_ass(
            job["params"]["text"],
            width=info["width"],
            height=info["height"],
            duration=dur,
            preset=job["params"]["preset"],
            font=job["params"]["font"],
            size=job["params"]["size"],
            color=job["params"]["color"],
            highlight=job["params"]["highlight"],
            position=job["params"]["position"],
        )
        ass_path = os.path.join(OUTPUT_DIR, job["id"] + ".ass")
        with open(ass_path, "w", encoding="utf-8") as f:
            f.write(ass_text)

        out = os.path.join(OUTPUT_DIR, job["id"] + ".mp4")
        job["status"] = "processing"
        job["progress"] = 1.0

        _run_ffmpeg(
            inp, ass_path, out, info["duration"] or dur,
            lambda p: job.__setitem__("progress", p),
        )

        job["status"] = "done"
        job["progress"] = 100.0
        job["output"] = out
        job["download_url"] = f"/api/download/{job['id']}"
    except Exception as e:  # noqa: BLE001
        log.exception("job %s failed", job["id"])
        job["status"] = "error"
        job["error"] = str(e)
    finally:
        # Don file tai len ngay sau khi xu ly xong de tiet kiem dung luong
        try:
            if inp and os.path.exists(inp):
                os.remove(inp)
        except OSError:
            pass
        job["input_path"] = None


def _worker_loop() -> None:
    while True:
        job_id = _QUEUE.get()
        with _LOCK:
            job = _JOBS.get(job_id)
        if job:
            _process(job)
        _QUEUE.task_done()


def _cleanup_loop() -> None:
    """Xoa file cu trong uploads/outputs va job da xu ly xong lau roi"""
    while True:
        time.sleep(600)
        now = time.time()
        for folder in (UPLOAD_DIR, OUTPUT_DIR):
            try:
                for name in os.listdir(folder):
                    p = os.path.join(folder, name)
                    try:
                        if os.path.isfile(p) and now - os.path.getmtime(p) > FILE_TTL:
                            os.remove(p)
                    except OSError:
                        pass
            except OSError:
                pass
        with _LOCK:
            stale = [k for k, v in _JOBS.items()
                     if now - v.get("created", now) > FILE_TTL]
            for k in stale:
                _JOBS.pop(k, None)


threading.Thread(target=_worker_loop, daemon=True).start()
threading.Thread(target=_cleanup_loop, daemon=True).start()


# ---------------------------------------------------------------------------
# API noi bo cho Flask
# ---------------------------------------------------------------------------
def submit(saved_path: str, params: dict) -> str:
    job_id = uuid.uuid4().hex[:16]
    job = {
        "id": job_id,
        "status": "queued",
        "progress": 0.0,
        "error": None,
        "output": None,
        "download_url": None,
        "input_path": saved_path,
        "params": params,
        "created": time.time(),
    }
    with _LOCK:
        _JOBS[job_id] = job
    _QUEUE.put(job_id)
    return job_id


def get(job_id: str):
    with _LOCK:
        job = _JOBS.get(job_id)
        if not job:
            return None
        return {k: job.get(k) for k in ("id", "status", "progress", "error", "download_url")}


def output_path(job_id: str):
    with _LOCK:
        job = _JOBS.get(job_id)
    if not job or job.get("status") != "done":
        return None
    return job.get("output")
