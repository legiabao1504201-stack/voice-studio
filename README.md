# Voice Studio — Tạo giọng nói offline (giống ElevenLabs)

Phần mềm Windows tạo giọng nói **chạy hoàn toàn trên máy bạn** (không cần internet sau khi tải model, không tốn phí, không gửi dữ liệu đi đâu). Giao diện thanh trượt mô phỏng ElevenLabs.

- **Engine:** viXTTS (bản fine-tune của XTTS-v2, hỗ trợ **tiếng Việt** + 16 ngôn ngữ)
- **Tính năng:** clone giọng từ 1 file mẫu 6–30 giây
- **Yêu cầu:** Windows 10/11, GPU NVIDIA (máy bạn có RTX 3060 12GB ✅)

---

## ⚠️ Nói thẳng về kỳ vọng

Đây **không phải** ElevenLabs và **không cho ra chất lượng y hệt** ElevenLabs — chất lượng đó đến từ mô hình khổng lồ + dữ liệu khổng lồ của họ. viXTTS là mô hình mã nguồn mở tốt nhất chạy offline được, chất lượng **khá tốt nhưng thấp hơn ElevenLabs một bậc**. Bù lại: miễn phí, offline, riêng tư.

Các thanh trượt ánh xạ sang engine như sau:

| Thanh trượt | Ánh xạ | Độ chính xác |
|---|---|---|
| Speed | `speed` (0.70–1.20) | ✅ Trùng khớp |
| Language Override | `language` | ✅ Trùng khớp |
| Output Format | xuất WAV → MP3 (cần ffmpeg) | ✅ Trùng khớp |
| Stability | `temperature` ↓ + `repetition_penalty` ↑ | 🟡 Gần đúng |
| Style Exaggeration | `temperature` ↑ + `top_p` ↑ | 🟡 Gần đúng |
| Similarity | giọng mẫu + `gpt_cond_len` (6–30s) | 🟡 Tùy file mẫu |

Chi tiết ánh xạ nằm trong hàm `map_sliders_to_params` ở [engine.py](engine.py) — bạn chỉnh được.

---

## Cài đặt (chỉ 1 lần)

1. **Cài Python 3.11** (nếu chưa có): https://www.python.org/downloads/release/python-3119/
   - Tải *Windows installer (64-bit)*
   - ⚠️ Khi cài **nhớ tích "Add python.exe to PATH"**
2. Nháy đúp **`install.bat`** → chờ tải PyTorch + thư viện (~vài GB, vài phút).
3. (Tùy chọn, để xuất MP3) cài ffmpeg: mở PowerShell gõ `winget install Gyan.FFmpeg`

## Sử dụng

1. Nháy đúp **`run.bat`** → app mở lên.
2. Nhập **nội dung cần đọc**.
3. Chọn **file giọng mẫu** (.wav 6–30 giây, giọng rõ, ít ồn) — đây là giọng app sẽ bắt chước.
4. Kéo các thanh trượt **hoặc gõ thẳng số** vào ô bên phải mỗi dòng (Speed: 0.70–1.20; các dòng khác: 0–100%). Số nhập ngoài giới hạn sẽ tự kẹp lại.
5. Chọn **Ngôn ngữ đọc** — mặc định Tiếng Việt, có **English** + 15 ngôn ngữ khác.
6. Bấm **🎙 Tạo giọng nói**.
   - **Lần đầu** sẽ tải model viXTTS (~1.8GB) — chỉ 1 lần.
   - Các lần sau chạy nhanh (vài giây với RTX 3060).
6. File kết quả nằm trong thư mục `output/`.

---

## Chế độ Server (Web + REST API)

Ngoài app desktop, dự án còn có **server** để dùng qua trình duyệt và để **app khác gọi vào bằng API key** (giống ElevenLabs/OpenAI).

### Chạy server
1. Nháy đúp **`serve.bat`** → server chạy tại `http://localhost:8000`
   - Mở trình duyệt vào địa chỉ đó để dùng **giao diện web**.
   - Lần đầu chạy, server tự tạo 1 API key và in ra cửa sổ console — lưu lại.
2. (Đưa ra internet) nháy đúp **`tunnel.bat`** → nhận 1 địa chỉ công khai `https://...trycloudflare.com` để app khác trên internet gọi vào.

### Quản lý API key
```
python manage_keys.py create [tên]   # tạo key mới (hiện 1 lần)
python manage_keys.py list           # liệt kê
python manage_keys.py revoke <id>    # thu hồi
```

### Các endpoint
| Method | Endpoint | Mô tả |
|---|---|---|
| GET | `/v1/languages` | Danh sách ngôn ngữ (không cần key) |
| POST | `/v1/voices` | Tải lên giọng mẫu (multipart: `name`, `file`) → `voice_id` |
| GET | `/v1/voices` | Liệt kê giọng |
| DELETE | `/v1/voices/{id}` | Xoá giọng |
| POST | `/v1/tts` | Sinh giọng → trả về audio |
| GET | `/health` | Trạng thái |

Xác thực: header `Authorization: Bearer <api_key>` (hoặc `X-API-Key: <api_key>`).

### Ví dụ gọi API (curl)
```bash
# 1) Tải giọng mẫu
curl -X POST http://localhost:8000/v1/voices \
  -H "Authorization: Bearer vs_XXX" \
  -F "name=Giong cua toi" -F "file=@mau.wav"
# -> {"voice_id":"vc_....","name":"Giong cua toi"}

# 2) Sinh giọng
curl -X POST http://localhost:8000/v1/tts \
  -H "Authorization: Bearer vs_XXX" -H "Content-Type: application/json" \
  -d '{"text":"Xin chào","voice_id":"vc_....","language":"vi","speed":1.0,"stability":50,"similarity":85,"style":0,"format":"mp3_44100_128"}' \
  --output giong.mp3
```

### Ví dụ Python
```python
import requests
B, KEY = "http://localhost:8000", "vs_XXX"
h = {"Authorization": f"Bearer {KEY}"}
vid = requests.post(f"{B}/v1/voices", headers=h,
        data={"name":"toi"}, files={"file":open("mau.wav","rb")}).json()["voice_id"]
r = requests.post(f"{B}/v1/tts", headers=h, json={
        "text":"Xin chào","voice_id":vid,"language":"vi",
        "speed":1.0,"stability":50,"similarity":85,"style":0,"format":"mp3_44100_128"})
open("giong.mp3","wb").write(r.content)
```

> ⚠️ **Bảo mật:** khi mở `tunnel.bat`, server của bạn ra internet — **API key là thứ duy nhất bảo vệ nó**. Đừng để lộ key, và thu hồi ngay nếu nghi bị lộ. Không commit `api_keys.json` lên GitHub (đã có trong `.gitignore`).

### Deploy lên GPU cloud (tùy chọn)
Có sẵn [Dockerfile](Dockerfile): `docker build -t voice-studio .` rồi `docker run --gpus all -p 8000:8000 voice-studio`.

---

## Cấu trúc

| File | Vai trò |
|---|---|
| [app.py](app.py) | App desktop (thanh trượt giống ElevenLabs) |
| [server.py](server.py) | Server FastAPI (web UI + REST API) |
| [engine.py](engine.py) | Nạp model viXTTS + ánh xạ thanh trượt → tham số |
| [apikeys.py](apikeys.py) / [manage_keys.py](manage_keys.py) | Hệ thống API key |
| [web/index.html](web/index.html) | Giao diện web |
| `serve.bat` / `tunnel.bat` | Chạy server / mở đường hầm internet |
| `install.bat` / `run.bat` | Cài đặt / chạy app desktop |
| `Dockerfile` | Deploy GPU cloud |
| `models/` `output/` `voices/` | Dữ liệu (tự tạo, không commit) |

## Mẹo chất lượng

- File giọng mẫu càng sạch (không nhạc nền, không ồn) → giọng clone càng giống.
- Tiếng Việt nên có **dấu đầy đủ** thì đọc mới đúng.
- Stability cao + Style thấp → giọng đều, ổn định (đọc tin tức).
- Style cao → biểu cảm hơn nhưng dễ "bay" hơn.
