# Render chạy file này để dựng server (có FFmpeg + font sẵn)
FROM python:3.12-slim

# FFmpeg (có libass để đốt chữ hoạt hình) + fontconfig để nhận diện font
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    fontconfig \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Copy font vào hệ thống và đăng ký cho fontconfig/libass
RUN mkdir -p /usr/share/fonts/truetype/appfonts \
    && cp static/fonts/*.ttf /usr/share/fonts/truetype/appfonts/ \
    && fc-cache -f >/dev/null 2>&1 || true

# Render tự cấp cổng qua biến môi trường PORT
ENV PORT=10000
EXPOSE 10000

# 1 worker + nhiều thread: vừa đủ cho gói free (512MB RAM)
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:$PORT --timeout 600 --workers 1 --threads 8 --max-requests 500 app:app"]
