# Virtual Try-On System - Claude Code Context

## Mục tiêu hiện tại
Implement các tính năng BE sau (FastAPI + Python):
1. `face_swap_service.py` - Face swap service dùng InsightFace
2. Body templates cho face swap
3. `POST /tryon/smart` - Smart tryon endpoint (auto detect full body vs face only)
4. CRUD `photo_tryon_sessions`

---

## Stack công nghệ

### Backend (D:\Backend_AR_Clothes)
- FastAPI 0.136 + Uvicorn 0.47
- SQLAlchemy 2.0 async + asyncpg + Neon PostgreSQL
- Pydantic v2
- Cloudinary (image storage)
- Python 3.11, venv: `D:\Backend_AR_Clothes\venv`

### AI Models đã setup
- **FitDiT** (D:\FitDiT\ckpts) - Virtual Try-On
- **InsightFace** buffalo_l - Face detection/analysis
  - Models: `C:\Users\Acer\.insightface\models\buffalo_l\`
- **inswapper_128.onnx** - Face swap
  - Path: `C:\Users\Acer\.insightface\models\inswapper_128.onnx`
- **DWpose** (D:\FitDiT\preprocess\dwpose) - Body keypoint detection
- **Human Parsing** (D:\FitDiT\preprocess\humanparsing) - Clothing segmentation

---

## Cấu trúc project BE

```
D:\Backend_AR_Clothes\
├── app\
│   ├── main.py              # FastAPI app, routers registration
│   ├── config.py            # Settings (pydantic-settings)
│   ├── dependencies.py      # FitDiTService singleton
│   ├── core\
│   │   └── database.py      # SQLAlchemy async engine
│   ├── models\
│   │   ├── user.py
│   │   ├── garment.py       # has cloth_image_url, sizes (JSON)
│   │   ├── body_profile.py  # chest, waist, hip, height, weight, gender
│   │   ├── photo_tryon_session.py  # person_image_url, result_image_url, etc
│   │   └── ...
│   ├── routers\
│   │   ├── tryon.py         # POST /tryon (FitDiT direct)
│   │   └── ...
│   ├── services\
│   │   ├── fitdit.py        # FitDiTService singleton
│   │   ├── fit_assessment_service.py
│   │   ├── cloudinary_service.py
│   │   └── ...
│   ├── repositories\
│   │   ├── body_profile_repository.py
│   │   ├── garment_repository.py
│   │   └── photo_tryon_session_repository.py
│   └── schemas\
│       ├── body_profile.py
│       ├── photo_tryon_session.py
│       └── ...
└── assets\
    └── templates\           # Body template images (cần tạo folder này)
        ├── male_template.jpg
        └── female_template.jpg
```

---

## Database Schema (Neon PostgreSQL)

### `body_profiles`
```python
id, user_id (FK users),
height (Numeric 5,1), weight (Numeric 5,1),
chest (Numeric 5,1), waist (Numeric 5,1), hip (Numeric 5,1),
shoulder (Numeric 5,1), arm_length (Numeric 5,1), inseam (Numeric 5,1),
gender (String: "male"/"female"/"neutral"),
created_at, updated_at, is_deleted
```

### `garments`
```python
id, name, description,
model_url (GLB for Snap AR), public_id,
item_index (Snap AR),
cloth_image_url,   # ảnh áo flat-lay cho FitDiT
cloth_image_public_id,
sizes (JSON):      # size chart
{
  "S":  {"chest_cm": 88, "waist_cm": 72, "hip_cm": 92, "length_cm": 65},
  "M":  {"chest_cm": 92, "waist_cm": 76, "hip_cm": 96, "length_cm": 67},
  "L":  {"chest_cm": 96, "waist_cm": 80, "hip_cm": 100, "length_cm": 69},
  "XL": {"chest_cm": 100, "waist_cm": 84, "hip_cm": 104, "length_cm": 71}
},
category_id (FK), store_id (FK),
is_deleted, created_at, updated_at
```

### `photo_tryon_sessions`
```python
id,
user_id (FK users, nullable),
garment_id (FK garments),
person_image_url (String 1000),    # ảnh người input
result_image_url (String 1000),    # ảnh kết quả FitDiT
result_public_id (String 500),     # Cloudinary public_id để xóa
cloth_type (String 20, default="upper"),  # upper/lower/overall
selected_size (String 10, nullable),
suggested_size (String 10, nullable),
fit_warnings (JSON, nullable),
created_at, is_deleted
```

---

## Services hiện có

### FitDiTService (app/services/fitdit.py)
```python
# Singleton, load khi startup
service = FitDiTService()
result_image = service.run(
    person_image: PIL.Image,
    cloth_image: PIL.Image,
    cloth_type: str = "upper",   # upper/lower/overall
    num_steps: int = 30,
    guidance: float = 2.0,
    seed: int = 42,
    resolution: str = "768x1024"  # 768x1024/1152x1536/1536x2048
) -> PIL.Image

# Internal: DWpose detect keypoints → Human parsing mask → SD3 pipeline
```

### FitAssessmentService (app/services/fit_assessment_service.py)
```python
service = FitAssessmentService(body_profile_repo, garment_repo)
result = await service.assess(
    body_profile_id: int,
    garment_id: int,
    size_label: str = None
) -> dict
# Returns: {chest_fit, waist_fit, hip_fit, overall_fit, recommendation, size_suggestion, body_measurements, garment_size}
```

### CloudinaryService (app/services/cloudinary_service.py)
```python
upload_info = cloud.upload_image(pil_image, folder="tryon_results", public_id="xxx")
# Returns: {url, public_id, created_at}
```

---

## Tính năng cần implement

### 1. FaceSwapService (app/services/face_swap_service.py)

```python
# Dùng InsightFace + inswapper
# Models path:
INSIGHTFACE_MODELS = "C:/Users/Acer/.insightface/models"
BUFFALO_L_DIR = f"{INSIGHTFACE_MODELS}/buffalo_l"
INSWAPPER_PATH = f"{INSIGHTFACE_MODELS}/inswapper_128.onnx"

# Methods cần có:
class FaceSwapService:
    def load(self): ...
    
    def detect_faces(self, image: PIL.Image) -> list:
        # Trả về list faces detected
        
    def is_face_only(self, image: PIL.Image) -> bool:
        # True nếu chỉ có mặt, không có body
        # Dùng DWpose check keypoints: nếu < 5 keypoints → face only
        
    def get_body_template(self, gender: str = "neutral") -> PIL.Image:
        # Load ảnh template từ assets/templates/
        # male_template.jpg / female_template.jpg / neutral_template.jpg
        
    def swap_face(self, face_image: PIL.Image, target_image: PIL.Image) -> PIL.Image:
        # Detect face trong face_image
        # Detect face trong target_image (body template)
        # Swap face từ face_image vào target_image
        # Trả về ảnh đã ghép mặt
```

### 2. Body Templates
Tạo folder `D:\Backend_AR_Clothes\assets\templates\`
Cần 3 ảnh template full body người đứng thẳng:
- `male_template.jpg`
- `female_template.jpg`  
- `neutral_template.jpg`
Lưu ý: ảnh phải full body, đứng thẳng, nền trắng/đơn giản

### 3. Smart Tryon Endpoint (thêm vào app/routers/tryon.py)

```
POST /tryon/smart
Form-data:
  person: UploadFile          # ảnh người (full body HOẶC chỉ mặt)
  garment_id: int             # ID garment trong DB
  user_id: int (optional)     # để lấy body_profile và lưu session
  cloth_type: str = "upper"
  num_steps: int = 20
  guidance: float = 2.0
  seed: int = 42
  resolution: str = "768x1024"
  gender: str = "neutral"     # dùng khi face swap cần chọn template

Flow:
1. Validate input
2. Load garment từ DB → lấy cloth_image_url
3. Download cloth_image từ Cloudinary URL
4. Detect input type:
   - face_swap_service.is_face_only(person_image) 
   - True → swap_face(person_image, template) → person_for_tryon
   - False → person_for_tryon = person_image
5. Chạy fit assessment nếu có user_id và garment có sizes:
   - Lấy body_profile của user
   - assess() → suggested_size, fit_warnings
6. Chạy FitDiT:
   - fitdit_service.run(person_for_tryon, cloth_image, ...)
7. Upload result lên Cloudinary
8. Lưu vào photo_tryon_sessions
9. Return response

Response:
{
  "session_id": int,
  "result_image_url": str,
  "public_id": str,
  "width": int, "height": int,
  "input_type": "full_body" | "face_only",
  "suggested_size": str | null,
  "fit_warnings": list | null,
  "created_at": str
}
```

### 4. CRUD Photo Tryon Sessions

```
GET  /tryon/sessions?user_id=X&skip=0&limit=20
     → list sessions của user, newest first

GET  /tryon/sessions/{id}
     → chi tiết 1 session (bao gồm garment info)

DELETE /tryon/sessions/{id}?user_id=X
     → soft delete (is_deleted=True) + xóa ảnh Cloudinary
```

---

## Config cần thêm vào config.py

```python
FITDIT_DIR:          str = "D:/FitDiT"
FITDIT_CKPT_PATH:    str = "D:/FitDiT/ckpts"
INSIGHTFACE_HOME:    str = "C:/Users/Acer/.insightface"
BODY_TEMPLATES_DIR:  str = "D:/Backend_AR_Clothes/assets/templates"
MIXED_PRECISION:     str = "bf16"
```

---

## Existing Endpoints (đừng thay đổi)

```
POST /tryon                          # FitDiT direct (giữ nguyên)
GET  /images                         # list Cloudinary images
GET  /garments/                      # list garments
GET  /garments/{id}                  # garment detail
POST /photo-tryon/body-profile       # save body measurements
POST /photo-tryon/fit-assessment     # size recommendation
GET  /health                         # GPU status
```

---

## Notes quan trọng

1. **FitDiTService là singleton** - đã load trong `dependencies.py`, inject qua `Depends(get_fitdit_service)`
2. **FaceSwapService cũng dùng singleton pattern** như FitDiTService
3. **Thêm FaceSwapService vào dependencies.py** và init trong `main.py lifespan`
4. **Async pattern**: DB calls dùng await, AI inference dùng `loop.run_in_executor(None, ...)`
5. **Error handling**: OOM → 503, validation error → 422, not found → 404
6. **Soft delete**: dùng `is_deleted=True` không xóa thật
7. **Cloudinary upload**: dùng `cloud.upload_image()` trong `services/cloudinary_service.py`
8. **numpy<2** đã cài - InsightFace hoạt động trên CPU

---

## Lệnh chạy BE
```powershell
cd D:\Backend_AR_Clothes
.\start_dev.ps1
# API: http://localhost:8000
# Docs: http://localhost:8000/docs
```