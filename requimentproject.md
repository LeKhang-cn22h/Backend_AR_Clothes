Tôi đang xây dựng một FastAPI service cho Virtual Try-On sử dụng CatVTON model (ICLR 2025).

## Cấu trúc project
Backend_AR_Clothes/
├── .env
├── download_models.py
├── app/
│   ├── init.py
│   ├── main.py
│   ├── config.py
│   ├── dependencies.py
│   ├── routers/
│   │   ├── init.py
│   │   └── tryon.py
│   └── services/
│       ├── init.py
│       └── catvton.py
├── CatVTON/          ← đã clone từ https://github.com/Zheng-Chong/CatVTON
├── detectron2/       ← đã clone và build từ source
└── model_cache/      ← chứa model weights download từ HuggingFace

## Môi trường
- Windows 11, Python 3.11, venv
- GPU: NVIDIA RTX 4060 Laptop (CUDA 12.9, dùng torch cu121)
- PyTorch 2.1.0+cu121 đã cài
- Detectron2 0.6 đã build từ source
- DensePose đã cài

## Yêu cầu từng file

### `.env`
HOST=0.0.0.0
PORT=8000
MIXED_PRECISION=fp16
ALLOW_TF32=true
DEFAULT_STEPS=50
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]

### `download_models.py`
Script dùng huggingface_hub.snapshot_download để tải 2 model về model_cache/:
- runwayml/stable-diffusion-inpainting → model_cache/sd-inpainting
- zhengchong/CatVTON → model_cache/CatVTON
Có check nếu folder đã tồn tại và có file thì skip, không download lại.

### `app/config.py`
- Dùng pydantic_settings.BaseSettings, đọc từ .env
- Các field: BASE_DIR, CATVTON_DIR, MODEL_CACHE (tự resolve từ __file__)
- SD_INPAINTING_PATH, CATVTON_CKPT_PATH (mặc định rỗng, tự resolve sau khi init)
- MIXED_PRECISION="fp16", ALLOW_TF32=True
- DEFAULT_STEPS=50, DEFAULT_GUIDANCE=2.5, DEFAULT_SEED=42
- IMAGE_WIDTH=768, IMAGE_HEIGHT=1024
- HOST, PORT, CORS_ORIGINS
- Sau khi tạo settings instance, tự resolve SD_INPAINTING_PATH và CATVTON_CKPT_PATH nếu rỗng

### `app/dependencies.py`
- Quản lý singleton CatVTONService
- Hàm get_catvton_service() dùng làm FastAPI Depends
- Hàm init_service() gọi khi startup

### `app/services/catvton.py`
- Thêm CatVTON/ vào sys.path
- Import từ CatVTON repo: CatVTONPipeline, AutoMasker, resize_and_crop
- Class CatVTONService dùng Singleton pattern (__new__)
- Method load(): 
  + Load CatVTONPipeline với base_ckpt=SD_INPAINTING_PATH, attn_ckpt=CATVTON_CKPT_PATH, attn_ckpt_version="mix"
  + enable_attention_slicing() và enable_vae_slicing() nếu có GPU
  + Load AutoMasker với densepose_ckpt và schp_ckpt từ CATVTON_CKPT_PATH
  + Load VaeImageProcessor
- Method run(person_image, cloth_image, cloth_type, num_steps, guidance, seed) -> PIL.Image:
  + resize_and_crop cả 2 ảnh về (IMAGE_WIDTH, IMAGE_HEIGHT)
  + Gọi automasker để lấy mask
  + Preprocess mask qua mask_processor
  + Chạy pipeline với generator từ seed
  + Trả về PIL Image kết quả
- Dùng @torch.inference_mode()

### `app/routers/tryon.py`
- APIRouter prefix="/tryon"
- Endpoint POST "" nhận: person (UploadFile), cloth (UploadFile), cloth_type (Form, default "upper"), num_steps (Form, default 50), guidance (Form, default 2.5), seed (Form, default 42)
- Validate: content_type phải là image/jpeg, image/png, image/webp; cloth_type phải là upper/lower/overall
- Chạy service.run() trong run_in_executor để không block event loop
- Trả về StreamingResponse image/jpeg
- Xử lý lỗi: out of memory → 503, lỗi khác → 500

### `app/main.py`
- Dùng lifespan context manager để load model khi startup (chạy init_service trong run_in_executor)
- CORSMiddleware với origins từ settings
- Include router tryon
- Endpoint GET /health trả về status, gpu availability, gpu_name

## Lưu ý quan trọng
- Tất cả string thông báo giữ tiếng Việt không dấu (tránh encoding issue trên Windows)
- File encoding UTF-8
- Chỉ dùng 1 worker khi chạy uvicorn vì model trên GPU
- Model chỉ load 1 lần duy nhất khi server start, không load lại mỗi requestzzzzzzSonnet 4.6