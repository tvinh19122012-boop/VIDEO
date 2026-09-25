r"""
Sinh file phụ đề .ASS chứa hoạt ảnh chữ kiểu CapCut.

Nguyên lý: mỗi "kiểu chữ động" (preset) được mô tả bằng các thẻ hoạt ảnh của
libass (\t, \fad, \move, \fscx, \frz, \blur ...). FFmpeg sẽ "đốt" (burn) lớp
phụ đề này vào video trên server, nên máy yếu cũng chạy được.
"""

from __future__ import annotations

import os

from PIL import ImageFont

# ---------------------------------------------------------------------------
# Cấu hình font (font được gói sẵn trong repo, không phụ thuộc internet)
# ---------------------------------------------------------------------------
FONTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "fonts"
)

FONT_FILES = {
    "Be Vietnam Pro": "be-vietnam-pro-800.ttf",
    "Baloo 2": "baloo-2-800.ttf",
    "Montserrat": "montserrat-900.ttf",
}

# Vị trí chữ trên khung hình (tỷ lệ % chiều cao)
POSITIONS = {"top": 0.17, "middle": 0.50, "bottom": 0.83}

# Danh sách kiểu chữ động hiển thị trên giao diện
PRESET_INFO = [
    {"id": "pop", "name": "Nảy vào", "icon": "🫧", "desc": "Chữ nảy từ nhỏ phóng to rồi khựng lại"},
    {"id": "words", "name": "Từng chữ nảy", "icon": "✨", "desc": "Chữ hiện dần từng từ, từ mới phổng lên + đổi màu"},
    {"id": "type", "name": "Gõ chữ", "icon": "⌨️", "desc": "Chữ được gõ ra từng ký tự như đánh máy"},
    {"id": "slide", "name": "Trượt lên", "icon": "⬆️", "desc": "Cả câu trượt từ dưới lên kèm mờ dần"},
    {"id": "spin", "name": "Xoay vào", "icon": "🌀", "desc": "Chữ xoay nghiêng rồi ngay ngắn lại"},
    {"id": "zoom", "name": "Phóng to", "icon": "🔍", "desc": "Chữ phóng to nhẹ rồi đứng yên"},
    {"id": "glow", "name": "Mờ phát sáng", "icon": "💡", "desc": "Chữ từ mờ sương hiện rõ, viền phát sáng"},
]


def _ts(sec: float) -> str:
    """Đổi giây -> định dạng thời gian ASS H:MM:SS.cc"""
    sec = max(0.0, float(sec))
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec - h * 3600 - m * 60
    return f"{h}:{m:02d}:{s:05.2f}"


def _color(hex_str: str, alpha: int = 0) -> str:
    """'#RRGGBB' -> màu ASS dạng &HAABBGGRR"""
    h = (hex_str or "").lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        h = "FFFFFF"
    try:
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    except ValueError:
        r, g, b = 255, 255, 255
    return f"&H{alpha:02X}{b:02X}{g:02X}{r:02X}"


def _escape(text: str) -> str:
    """Loại ký tự phá vỡ cú pháp ASS"""
    return (
        (text or "")
        .replace("{", "(")
        .replace("}", ")")
        .replace("\r", "")
        .strip()
    )


def _ov(tags: str) -> str:
    """Gói 1 khối thẻ hoạt ảnh inline của ASS"""
    return "{" + tags + "}"


class _Ctx:
    """Thông tin dùng chung cho tất cả preset"""

    def __init__(self, width, height, font, size_pct, color, highlight, position):
        self.w = max(2, int(width))
        self.h = max(2, int(height))
        self.x = self.w / 2.0
        self.y = self.h * POSITIONS.get(position, 0.5)
        # Cỡ chữ tính theo chiều cao video (1920 = 100%)
        self.fs = max(14, round(self.h * float(size_pct) / 100.0))
        self.base = _color(color)
        self.hl = _color(highlight)
        self.outline = max(2, round(self.fs * 0.085))
        self.shadow = max(1, round(self.fs * 0.05))
        self.spacing = round(self.fs * 0.02)
        self.margin = round(min(self.w, self.h) * 0.04)
        self.font = font
        self.font_path = os.path.join(FONTS_DIR, FONT_FILES.get(font, FONT_FILES["Be Vietnam Pro"]))

    def measure(self, text: str):
        """Đo bề rộng chữ bằng chính font sẽ render (dùng cho preset 'từng chữ')"""
        try:
            f = ImageFont.truetype(self.font_path, self.fs)
            return f.getlength(text)
        except Exception:
            return None


# ---------------------------------------------------------------------------
# Các preset hoạt ảnh. Mỗi hàm trả về list các "dòng phụ đề":
#   {"start": giây, "end": giây, "text": nội dung (đã có thẻ inline), "layer": số}
# ---------------------------------------------------------------------------

def _p_pop(text, t0, t1, c: _Ctx):
    # Phóng từ 30% -> 115% -> 100% (nảy), kèm mờ đầu vào
    o = (
        f"\\an5\\pos({c.x:.0f},{c.y:.0f})\\fscx30\\fscy30\\blur6"
        f"\\t(0,220,\\fscx115\\fscy115\\blur0)\\t(220,440,\\fscx100\\fscy100)"
    )
    return [{"start": t0, "end": t1, "text": _ov(o) + text, "layer": 1}]


def _p_slide(text, t0, t1, c: _Ctx):
    dist = round(c.h * 0.16)
    o = f"\\an5\\move({c.x:.0f},{c.y + dist:.0f},{c.x:.0f},{c.y:.0f},0,420)"
    return [{"start": t0, "end": t1, "text": _ov(o) + text, "layer": 1}]


def _p_zoom(text, t0, t1, c: _Ctx):
    o = (
        f"\\an5\\pos({c.x:.0f},{c.y:.0f})\\fscx55\\fscy55\\blur5"
        f"\\t(0,300,\\fscx108\\fscy108\\blur0)\\t(300,540,\\fscx100\\fscy100)"
    )
    return [{"start": t0, "end": t1, "text": _ov(o) + text, "layer": 1}]


def _p_spin(text, t0, t1, c: _Ctx):
    o = (
        f"\\an5\\pos({c.x:.0f},{c.y:.0f})\\frz-20\\fscx40\\fscy40"
        f"\\t(0,400,\\frz0\\fscx112\\fscy112)\\t(400,640,\\fscx100\\fscy100)"
    )
    return [{"start": t0, "end": t1, "text": _ov(o) + text, "layer": 1}]


def _p_glow(text, t0, t1, c: _Ctx):
    o = (
        f"\\an5\\pos({c.x:.0f},{c.y:.0f})\\blur14\\be1"
        f"\\t(0,520,\\blur0)\\t(0,520,\\be0)"
    )
    return [{"start": t0, "end": t1, "text": _ov(o) + text, "layer": 1}]


def _p_type(text, t0, t1, c: _Ctx):
    """Gõ từng ký tự: mỗi bước hiển thị text[:i], có con trỏ nhấp nháy"""
    n = len(text)
    if n == 0:
        return []
    delay = max(0.035, min(0.11, (t1 - t0) * 0.5 / n))
    out = []
    for i in range(1, n + 1):
        s = t0 + (i - 1) * delay
        e = t0 + i * delay if i < n else t1
        cursor = "▕" if i < n else ""
        o = f"\\an5\\pos({c.x:.0f},{c.y:.0f})"
        out.append({"start": s, "end": e, "text": _ov(o) + text[:i] + cursor, "layer": i + 1})
    return out


def _p_words(text, t0, t1, c: _Ctx):
    """
    Từng chữ nảy + tô màu (kiểu phụ đề Hormozi/CapCut).
    Chữ cũ giữ nguyên vị trí (neo trái), chữ mới phổng to và đổi màu nổi bật.
    """
    words = text.split()
    if not words:
        return []
    step = max(0.18, min(0.65, (t1 - t0) * 0.6 / len(words)))
    full = " ".join(words)
    w = c.measure(full)
    if not w:
        w = len(full) * c.fs * 0.55
    x0 = c.x - w / 2.0  # canh cho cả câu nằm giữa khung
    pop = f"\\c{c.hl}\\fscx125\\fscy125\\t(0,150,\\fscx100\\fscy100)"
    out = []
    for i, word in enumerate(words):
        s = t0 + i * step
        e = t0 + (i + 1) * step if i < len(words) - 1 else t1
        o = f"\\an4\\pos({x0:.0f},{c.y:.0f})"
        body = (" ".join(words[:i]) + " " if i else "") + _ov(pop) + word
        out.append({"start": s, "end": e, "text": _ov(o) + body, "layer": i + 1})
    return out


_PRESETS = {
    "pop": _p_pop,
    "slide": _p_slide,
    "zoom": _p_zoom,
    "spin": _p_spin,
    "glow": _p_glow,
    "type": _p_type,
    "words": _p_words,
}


# ---------------------------------------------------------------------------
# Hàm chính: dựng nguyên file .ASS
# ---------------------------------------------------------------------------

def build_ass(
    text: str,
    *,
    width: int,
    height: int,
    duration: float,
    preset: str = "pop",
    font: str = "Be Vietnam Pro",
    size: float = 6.5,
    color: str = "#FFFFFF",
    highlight: str = "#FFE933",
    position: str = "middle",
) -> str:
    """Trả về nội dung file .ASS (UTF-8)"""

    # Tách theo dòng do người dùng xuống dòng -> mỗi dòng chiếm 1 khoảng thời gian
    raw_lines = [ln for ln in (text or "").replace("\r", "").split("\n")]
    lines = [_escape(ln) for ln in raw_lines]
    lines = [ln for ln in lines if ln]
    if not lines:
        lines = [""]

    c = _Ctx(width, height, font, size, color, highlight, position)
    dur = max(0.4, float(duration))
    per = dur / len(lines)

    fn = _PRESETS.get(preset, _p_pop)

    events = []
    for li, line in enumerate(lines):
        t0 = li * per
        t1 = t0 + per
        events.extend(fn(line, t0, t1, c))

    header = f"""[Script Info]
; Sinh bởi Video Text Web
Title: Animated text overlay
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709
PlayResX: {c.w}
PlayResY: {c.h}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Main,{c.font},{c.fs},{c.base},&H000000FF,&H00101010,&H96000000,-1,0,0,0,100,100,{c.spacing},0,1,{c.outline},{c.shadow},5,{c.margin},{c.margin},{c.margin},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    body = "".join(
        f"Dialogue: {ev['layer']},{_ts(ev['start'])},{_ts(ev['end'])},Main,,0,0,0,,{ev['text']}\n"
        for ev in events
    )
    return header + body
