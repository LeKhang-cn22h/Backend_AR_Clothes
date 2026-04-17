# Backend AR Clothes — CatVTON Service

Service API cho tính năng **Virtual Try-On** (thử đồ ảo) sử dụng model CatVTON (ICLR 2025).

## Tổng quan

Người dùng upload 2 ảnh (ảnh người + ảnh quần áo), service trả về ảnh người đang mặc quần áo đó — được tạo ra bởi AI diffusion model.

```
[Ảnh người] + [Ảnh quần áo]
          ↓
    CatVTON Model
    (Stable Diffusion 1.5 Inpainting
     + CatVTON attention weights
     + SCHP segmentation
     + DensePose)
          ↓
    [Ảnh kết quả]
```

## Cấu trúc project

```
Backend_AR_Clothes/
├── README.md               ← file này
├── .env                    ← biến môi trường (không commit)
├── .gitignore
│
├── download_models.py      ← script tải model weights về máy
│
├── app/                    ← FastAPI application
│   ├── main.py             ← entry point, khởi động server
│   ├── config.py           ← cấu hình toàn project
│   ├── dependencies.py     ← quản lý singleton model
│   ├── routers/            ← định nghĩa các API endpoint
│   └── services/           ← business logic, inference
│
├── CatVTON/                ← source code model (git clone)
├── detectron2/             ← thư viện segmentation (git clone)
└── model_cache/            ← model weights download về (không commit)
```

## Yêu cầu hệ thống

- Python 3.9+
- NVIDIA GPU >= 6GB VRAM
- CUDA Toolkit 12.x
- Visual Studio Build Tools (với C++ workload)

## Cài đặt

Xem file `SETUP.md` để biết hướng dẫn cài đặt từng bước.

## Chạy server

```powershell
# Activate venv
.\venv\Scripts\Activate.ps1

# Download models (chỉ chạy lần đầu, ~5GB)
python download_models.py

# Start server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## API Endpoints

| Method | URL | Mô tả |
|--------|-----|--------|
| GET | `/health` | Kiểm tra server + GPU |
| POST | `/tryon` | Thực hiện virtual try-on |
| GET | `/docs` | Swagger UI tự động |

## Công nghệ sử dụng

| Thư viện | Vai trò |
|----------|---------|
| FastAPI | Web framework |
| CatVTON | Model AI thử đồ ảo |
| Stable Diffusion 1.5 | Base diffusion model |
| SCHP | Phân vùng quần áo trên người |
| DensePose | Nhận diện pose cơ thể |
| Detectron2 | Framework cho SCHP + DensePose |
| Diffusers | Pipeline chạy SD model |
| PyTorch | Deep learning framework |