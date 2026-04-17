# Thư mục `app/` — FastAPI Application

Đây là **core của backend service** — chứa toàn bộ code FastAPI để expose API ra ngoài cho frontend gọi vào.

## Cấu trúc

```
app/
├── __init__.py         ← đánh dấu đây là Python package
├── main.py             ← entry point — khởi động server
├── config.py           ← tất cả cấu hình tập trung một chỗ
├── dependencies.py     ← quản lý singleton model (load 1 lần dùng mãi)
├── routers/            ← các nhóm API endpoint
│   ├── __init__.py
│   └── tryon.py        ← endpoint POST /tryon
└── services/           ← business logic thực sự
    ├── __init__.py
    └── catvton.py      ← wrapper chạy CatVTON inference
```

## Luồng xử lý một request

```
Frontend gửi POST /tryon
        ↓
   app/main.py          (nhận request, route đến router)
        ↓
   app/routers/tryon.py (validate input, gọi service)
        ↓
   app/services/catvton.py (chạy AI model, trả về ảnh)
        ↓
   Frontend nhận ảnh JPEG
```

## Tại sao tách thành routers/ và services/?

- **routers/** chỉ lo HTTP: validate input, trả về response, xử lý lỗi HTTP
- **services/** chỉ lo business logic: không biết gì về HTTP, chỉ nhận PIL Image, trả về PIL Image
- Dễ test từng phần riêng lẻ
- Nếu sau này muốn thêm endpoint mới (ví dụ `/tryon/batch`), chỉ cần thêm router, không đụng vào service

## Mô tả từng file

### `main.py`
Entry point duy nhất. Làm 3 việc:
1. Tạo FastAPI app
2. Mount CORS middleware (cho phép frontend call API)
3. Đăng ký routers
4. Load model khi server khởi động (lifespan)

### `config.py`
Tập trung **tất cả** cấu hình vào một chỗ, đọc từ file `.env`.
Không hardcode path hay số magic rải rác trong code.

### `dependencies.py`
Quản lý **singleton** — đảm bảo CatVTON model chỉ được load vào GPU **một lần duy nhất** dù có nhiều request đến cùng lúc.
Load model rất tốn thời gian (~30-60 giây), không thể load lại mỗi request.

### `routers/tryon.py`
Định nghĩa endpoint `POST /tryon`. Làm 4 việc:
1. Nhận file upload từ multipart form
2. Validate (đúng định dạng ảnh, đúng cloth_type...)
3. Gọi `CatVTONService.run()`
4. Stream ảnh kết quả về client

### `services/catvton.py`
**Wrapper** cho CatVTON model. Làm 3 việc:
1. Load pipeline SD1.5 + CatVTON weights
2. Load AutoMasker (SCHP + DensePose)
3. Expose method `run(person_image, cloth_image, ...)` → trả về ảnh kết quả