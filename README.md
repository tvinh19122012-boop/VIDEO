# 🎬 Web Chữ Chạy Cho Video

Web app giúp bạn **tải video lên → gõ chữ → chữ động kiểu CapCut → tải video về**.

> **Máy yếu vẫn dùng được:** toàn bộ việc render (giải mã + ghép chữ + encode video)
> đều chạy trên **server Render**, máy bạn chỉ việc mở trình duyệt.
> Đúng như yêu cầu: gõ "Chào Các Bạn" → chữ to, font đẹp, có hoạt ảnh 2–3 giây.

---

## ✨ Tính năng

| | |
|---|---|
| **7 kiểu chữ động** | Nảy vào · Từng chữ nảy (+đổi màu) · Gõ chữ · Trượt lên · Xoay vào · Phóng to · Mờ phát sáng |
| **3 font tiếng Việt đẹp** | Be Vietnam Pro · Baloo 2 · Montserrat (đậm, có đủ dấu) |
| **Tuỳ chỉnh** | Cỡ chữ · màu chữ · màu chữ nổi bật · vị trí (trên/giữa/dưới) · thời gian hiện 1–8 giây |
| **Xem thử trước** | Hoạt ảnh chạy thử ngay trên trình duyệt trước khi render |
| **Nhiều dòng chữ** | Xuống dòng = nhiều câu hiện lần lượt |
| **Giữ nguyên âm thanh** | Video gốc có tiếng gì thì video mới có tiếng đó |

Hoạt ảnh được dựng bằng thư viện **ASS/libass của FFmpeg** → mượt, nhẹ, không cần cài
thêm phần mềm gì trên máy bạn.

---

## 📁 Cấu trúc thư mục

```
video-text-web/
├── app.py                  # Server Flask (API nhận video, trả kết quả)
├── renderer/
│   ├── presets.py          # Sinh hoạt ảnh chữ (file .ASS kiểu CapCut)
│   └── engine.py           # Hàng đợi job + gọi FFmpeg render
├── static/
│   ├── style.css           # Giao diện (tối, đẹp, dùng tốt trên điện thoại)
│   ├── app.js              # Logic web + bộ xem thử hoạt ảnh
│   └── fonts/              # 3 font tiếng Việt (đóng gói sẵn trong repo)
├── templates/
│   └── index.html          # Giao diện người dùng
├── uploads/                # Tạm: video người dùng tải lên (tự xoá)
├── outputs/                # Tạm: video kết quả (tự xoá sau 3 tiếng)
├── Dockerfile              # Cài FFmpeg + font, chạy được trên Render
├── render.yaml             # Cấu hình deploy 1-click cho Render
├── requirements.txt        # Thư viện Python cần thiết
└── .gitignore
```

---

## 🚀 CÁCH LÀM TỪNG BƯỚC

### Bước 1 — Đưa code lên GitHub

**Cách A: kéo-thả trên web (dễ nhất, không cần cài gì)**

1. Vào https://github.com → đăng nhập → nút **+** góc trên phải → **New repository**.
2. Đặt tên repo, ví dụ `video-text-web` → chọn **Public** → **Create repository**.
3. Trong repo vừa tạo, bấm **add file → Upload files**.
4. Kéo **toàn bộ** thư mục `video-text-web` (giữ nguyên các thư mục con
   `renderer/`, `static/`, `templates/`, `static/fonts/`) vào khung upload.
   ⚠️ Phải kéo cả thư mục `static/fonts` chứa 3 file `.ttf`, thiếu font là web sẽ lỗi chữ.
5. Bấm **Commit changes**.

**Cách B: dùng lệnh git** (nếu bạn quen)

```bash
cd video-text-web
git init
git add .
git commit -m "Web chu chay cho video"
git branch -M main
git remote add origin https://github.com/TEN-BAN/video-text-web.git
git push -u origin main
```

### Bước 2 — Deploy lên Render (miễn phí)

1. Vào https://render.com → đăng nhập (nên chọn **Sign in with GitHub**).
2. Góc trên phải bấm **New +** → chọn **Blueprint**.
3. Chọn repo `video-text-web` vừa tạo → Render tự đọc file `render.yaml`.
4. Bấm **Apply**. Render sẽ:
   - cài FFmpeg + font (dùng `Dockerfile`),
   - khởi động server bằng Gunicorn.
5. Đợi ~3–5 phút đến khi trạng thái chuyển **Live**.
6. Bấm vào link dạng `https://video-text-web.onrender.com` → **xong, dùng được!**

> Không dùng Blueprint được thì: **New + → Web Service** → chọn repo →
> **Runtime: Docker** → để trống các lệnh build/start (Render tự đọc `Dockerfile`) →
> thêm biến môi trường `PORT=10000` → Create Web Service.

### Bước 3 — Dùng web

1. Mở link Render trên **điện thoại hoặc máy tính** đều được.
2. Chạm **"Chạm để chọn video"** → chọn video trong máy.
3. Gõ chữ, ví dụ: `Chào Các Bạn`.
4. Chọn kiểu chữ động (mặc định **Nảy vào**), chỉnh cỡ chữ / màu / vị trí nếu muốn.
5. Bấm **▶ Xem thử hoạt ảnh** để xem trước ngay trên video.
6. Bấm **🎬 Tạo video** → đợi thanh tiến độ chạy tới 100% → **⬇ Tải video về máy**.

---

## ⚠️ Lưu ý quan trọng (gói miễn phí của Render)

| Vấn đề | Cách xử lý |
|---|---|
| **Server "ngủ" sau 15 phút** không ai dùng | Lần mở đầu tiên phải chờ ~30–60 giây cho server thức dậy. Lỗi/thời gian chờ là bình thường, cứ F5 lại. |
| **RAM chỉ 512 MB** | Video nên **dưới 2–3 phút**. Video dài/quá nặng server sẽ báo lỗi → hãy cắt ngắn video trước. |
| **Giới hạn tải lên 250 MB** | Sửa biến `MAX_UPLOAD_MB` trong Render nếu cần (đổi cả trong `app.py`). |
| **Link tải chỉ sống 3 tiếng** | Server tự dọn file. Tải về ngay sau khi render xong! |
| **750 giờ chạy/tháng** | Đủ cho 1 web cá nhân dùng cả tháng. |

---

## 🔧 Khắc phục lỗi thường gặp

| Hiện tượng | Nguyên nhân & cách sửa |
|---|---|
| Web báo *"Không tạo được file kết quả"* | Video định dạng lạ. Thử lưu lại thành **MP4** rồi tải lên lại. |
| Chữ bị méo/thiếu dấu | Bạn đang dùng font cũ — kéo lại thư mục `static/fonts` lên GitHub cho đủ 3 file `.ttf`. |
| Bấm "Tạo video" mà mãi không xong | Server đang ngủ → chờ 1 phút, F5 trang và thử lại. |
| Deploy Render bị lỗi build | Kiểm tra bạn đã upload **cả thư mục `static/fonts`** (3 file .ttf) và file `requirements.txt`. |
| Muốn đổi cỡ chữ mặc định | Sửa `value` của ô `size` trong `templates/index.html` và `DEFAULT` trong `renderer/presets.py`. |

---

## 🛠 Chạy thử trên máy mình (không bắt buộc)

```bash
pip install -r requirements.txt
python3 app.py
# mở http://localhost:5000
```

Nếu máy chưa có FFmpeg thì cài tại https://ffmpeg.org (hoặc `winget install ffmpeg`).

---

## 📄 Giấy phép font

Be Vietnam Pro, Baloo 2, Montserrat đều là font mã nguồn mở (SIL Open Font License 1.1),
được phép dùng cho mục đích cá nhân lẫn thương mại.
