# AR Clothes — BE Context
**Path**: `D:\Backend_AR_Clothes\app`
**Framework**: FastAPI, SQLAlchemy async (asyncpg), Pydantic v2
**Port**: 8000
**DB chính**: Neon PostgreSQL (pgvector)
**DB phụ**: Firebase Firestore (chỉ dùng cho `orders` + sync `products` → embeddings)

---

## Kiến trúc bắt buộc
```
router (thin)
  → service (business logic)
    → repository (DB queries)
```

### Rules
- Router: chỉ validate input + gọi service + raise HTTPException
- Service: business logic, orchestration
- Repository: DB queries only (SQLAlchemy / raw SQL)
- **KHÔNG** để business logic trong router
- **KHÔNG** gọi DB trực tiếp trong service (dùng repository)
- Tuân thủ SOLID

### Ngoại lệ hiện có (cần biết khi sửa)
- `services/garment_service.py` viết theo **kiểu module-level functions**, không phải class — và **gọi `db.execute` trực tiếp**, không qua `GarmentRepository`.
- `routers/tryon.py` chứa business logic + in-memory job store `_jobs` (không có `TryonService`); gọi thẳng `fitdit_service` + `cloudinary_service`.
- `routers/payment.py` gọi `stripe` SDK trực tiếp ở 2 endpoint list/detail (không qua service).
- `routers/users.py`, `routers/reviews.py` thi thoảng instantiate repository thẳng trong handler.

---

## Entry point (`app/main.py`)
```python
# Lifespan: init_db()
# Middleware: CORSMiddleware, NgrokHeaderMiddleware (thêm ngrok-skip-browser-warning)
# KHÔNG mount /static (đã xóa GLB)
# GET /health  → { status, fitdit_available, fitdit_url }
```

### Các router được include
```
tryon_router        → /tryon
images_router       → /images
store_router        → /stores
garments_router     → /garments
garment_categories_router → /garment-categories
users_router        → /users
addresses_router    → /users/{user_id}/addresses
reviews_router      → /reviews
chatbot_router      → /api/chatbot
payment_router      → /payment
fit_router          → /fit
```

---

## 1. ROUTERS — Tất cả endpoints

### `users.py` — prefix `/users`
| Method | Path | Handler | Note |
|--------|------|---------|------|
| POST   | `/users`                          | `create_or_upsert` | upsert theo firebase_uid, 409 nếu email trùng |
| GET    | `/users`                          | `get_all`          | query: `skip`, `limit` (1..100) |
| GET    | `/users/by-uid/{firebase_uid}`    | `get_by_uid`       | trả full UserResponse |
| GET    | `/users/by-firebase-uid/{firebase_uid}` | `get_by_firebase_uid` | chỉ trả `{id}` |
| GET    | `/users/{id}`                     | `get_one`          | |
| PATCH  | `/users/{id}`                     | `update`           | |
| DELETE | `/users/{id}`                     | `delete`           | soft delete |

### `addresses.py` — prefix `/users/{user_id}/addresses`
| Method | Path | Handler |
|--------|------|---------|
| POST   | `""`                              | `create` |
| GET    | `""`                              | `get_all` (theo user) |
| GET    | `/{id}`                           | `get_one` |
| PUT    | `/{id}`                           | `update` |
| DELETE | `/{id}`                           | `delete` (soft) |
| PATCH  | `/{id}/set-default`               | `set_default` |

### `garments.py` — prefix `/garments`
| Method | Path | Handler | Note |
|--------|------|---------|------|
| POST   | `/`                               | `create` | multipart form, optional `cloth_image` upload Cloudinary |
| GET    | `/`                               | `get_all` |
| GET    | `/by-product/{firestore_product_id}` | `get_by_firestore_product` | trả list (mỗi màu = 1 garment) |
| GET    | `/{garment_id}`                   | `get_one` |
| PUT    | `/{garment_id}`                   | `update` | multipart form |
| DELETE | `/{garment_id}`                   | `delete` | soft + xóa ảnh Cloudinary |
| GET    | `/{garment_id}/lens-link`         | `lens_link` | trả Snap Lens URL |

### `garment_categories.py` — prefix `/garment-categories`
| Method | Path | Handler |
|--------|------|---------|
| POST   | `""`             | `create` |
| GET    | `""`             | `get_all` |
| GET    | `/{id}`          | `get_one` |
| PUT    | `/{id}`          | `update` |
| DELETE | `/{id}`          | `delete` |

### `reviews.py` — prefix `/reviews`
| Method | Path | Handler | Note |
|--------|------|---------|------|
| POST   | `""`                                | `create` | tự update nếu user đã review product |
| GET    | `""`                                | `get_all` | filter: `firestore_product_id`, `user_id`, `rating` |
| GET    | `/{id}`                             | `get_one` |
| PUT    | `/{id}`                             | `update` |
| DELETE | `/{id}`                             | `delete` (soft) |
| GET    | `/product/{firestore_product_id}`        | `get_by_product` | paging: `page`, `limit` |
| GET    | `/product/{firestore_product_id}/stats`  | `get_product_stats` |
| GET    | `/check-purchase/{firestore_product_id}` | `check_purchase` | trả `{hasPurchased, hasReviewed}` |
| GET    | `/my-review/{firestore_product_id}` | `get_my_review` |

### `store.py` — prefix `/stores`
| Method | Path | Handler |
|--------|------|---------|
| POST   | `""`             | `create_store` |
| GET    | `""`             | `list_stores` (filter `is_active`) |
| GET    | `/{id}`          | `get_store` (UUID) |
| PATCH  | `/{id}`          | `update_store` |
| DELETE | `/{id}`          | `delete_store` (soft) |

### `fit_router.py` — prefix `/fit`
| Method | Path | Handler | Note |
|--------|------|---------|------|
| POST   | `/suggest`                       | `suggest_size` | body: `garment_id` + (`user_id` hoặc `measurements`) |
| GET    | `/garment/{garment_id}/sizes`    | `get_garment_sizes` | trả size chart |
| PUT    | `/garment/{garment_id}/sizes`    | `upsert_garment_sizes` | admin: bulk upsert |

### `tryon.py` — prefix `/tryon`
| Method | Path | Handler | Note |
|--------|------|---------|------|
| POST   | `""`                       | `tryon`             | multipart: `person`, `cloth` + form params → trả `job_id` ngay |
| POST   | `/catalog`                 | `tryon_catalog`     | cloth lấy từ `garment_id` |
| GET    | `/status/{job_id}`         | `get_tryon_status`  | poll: queued / processing / done / failed |
| GET    | `/history`                 | `get_tryon_history` | query: `user_id`, `limit`, `offset` |

Job được giữ trong `_jobs: dict` in-memory, TTL 3600s.

### `images.py` — prefix `/images`
| Method | Path | Handler | Note |
|--------|------|---------|------|
| GET    | `""`                       | `list_images`        | folder mặc định `tryon_results` |
| GET    | `/{public_id:path}`        | `get_image`          |
| DELETE | `""`                       | `delete_all_images`  |
| DELETE | `/{public_id:path}`        | `delete_image`       |

### `chatbot.py` — prefix `/api/chatbot`
| Method | Path | Handler |
|--------|------|---------|
| POST   | `/sessions`                                  | `create_session` |
| GET    | `/sessions`                                  | `get_sessions` (query `user_id`) |
| GET    | `/sessions/{session_id}`                     | `get_session` |
| PATCH  | `/sessions/{session_id}/title`               | `update_title` |
| DELETE | `/sessions/{session_id}`                     | `delete_session` |
| DELETE | `/messages/{message_id}`                     | `delete_message` |
| POST   | `/chat`                                      | `chat` |
| POST   | `/search/image-url`                          | `search_by_image_url` |
| POST   | `/search/image-upload`                       | `search_by_image_upload` (UploadFile) |
| POST   | `/admin/sync-products`                       | `sync_products` (Firestore → embeddings) |
| GET    | `/admin/embeddings/stats`                    | `get_embedding_stats` |
| GET    | `/admin/embeddings`                          | `get_embeddings` (search, skip, limit) |
| DELETE | `/admin/embeddings/{firestore_product_id}`   | `delete_embedding` |

### `payment.py` — prefix `/payment`
| Method | Path | Handler | Note |
|--------|------|---------|------|
| POST   | `/stripe/create`                  | `create_stripe_payment` | tạo Stripe Checkout Session |
| GET    | `/stripe/success`                 | `stripe_success` | redirect về FE |
| GET    | `/stripe/payments`                | `get_stripe_payments` | list từ Stripe API |
| GET    | `/stripe/payments/{payment_intent_id}` | `get_stripe_payment_detail` |

---

## 2. MODELS — Bảng + cột

### `users` (`User`)
```
id              SERIAL PK
firebase_uid    VARCHAR(128) UNIQUE NOT NULL, indexed
email           VARCHAR(255) UNIQUE NOT NULL
display_name    VARCHAR(200) NULL
phone           VARCHAR(20)  NULL
avatar_url      VARCHAR(500) NULL
created_at      TIMESTAMPTZ default now()
updated_at      TIMESTAMPTZ default now(), onupdate now()
is_deleted      BOOLEAN default false
```
Relationships: `stores`, `addresses`, `reviews`, `body_profiles`, `tryon_history`

### `stores` (`Store`)
```
id              UUID PK (default uuid4)
name            VARCHAR(255) NOT NULL
description     TEXT NULL
address         VARCHAR(500) NULL
phone           VARCHAR(20)  NULL
email           VARCHAR(255) UNIQUE NULL
website         VARCHAR(500) NULL
logo_url        VARCHAR(500) NULL
banner_url      VARCHAR(500) NULL
manager_name    VARCHAR(255) NULL
address_detail  VARCHAR(500) NULL
latitude        FLOAT NULL
longitude       FLOAT NULL
is_active       BOOLEAN default true
user_id         INT FK → users.id NOT NULL
created_at      TIMESTAMPTZ
updated_at      TIMESTAMPTZ
is_deleted      BOOLEAN default false
```
Relationships: `user`, `garments`

### `garment_categories` (`GarmentCategory`)
```
id              SERIAL PK
name            VARCHAR(100) NOT NULL
description     TEXT NULL
created_at      TIMESTAMPTZ
is_deleted      BOOLEAN
```
Relationships: `garments`

### `garments` (`Garment`)
```
id                    SERIAL PK
name                  VARCHAR(255) NOT NULL
description           VARCHAR(1000) NULL
item_index            INT NULL                  -- Snap Camera Kit index
color                 VARCHAR(100) NULL
firestore_product_id  VARCHAR(500) NULL, indexed
category_id           INT FK → garment_categories.id NULL
store_id              UUID FK → stores.id NULL
cloth_image_url       STRING NULL
cloth_image_public_id STRING NULL
created_at            TIMESTAMPTZ
updated_at            TIMESTAMPTZ
is_deleted            BOOLEAN
-- KHÔNG có model_url
```
Relationships: `category`, `store`, `size_specs` (cascade delete, selectin), `tryon_history`

### `addresses` (`Address`)
```
id              SERIAL PK
user_id         INT FK → users.id NOT NULL
full_name       VARCHAR(200) NOT NULL
phone           VARCHAR(20)  NOT NULL
address         TEXT NOT NULL
address_type    VARCHAR(50)  default "Nhà riêng"
city            VARCHAR(100) NULL
district        VARCHAR(100) NULL
ward            VARCHAR(100) NULL
latitude        FLOAT NULL
longitude       FLOAT NULL
is_default      BOOLEAN default false
created_at      TIMESTAMPTZ
updated_at      TIMESTAMPTZ
is_deleted      BOOLEAN
```
Relationships: `user`

### `reviews` (`Review`)
```
id                    SERIAL PK
user_id               INT FK → users.id NOT NULL
firestore_product_id  VARCHAR(100) NOT NULL, indexed
rating                INT NOT NULL  (CHECK 1..5)
comment               TEXT NULL
media_urls            TEXT NULL    -- JSON string
created_at            TIMESTAMPTZ
updated_at            TIMESTAMPTZ
is_deleted            BOOLEAN
UNIQUE(user_id, firestore_product_id)
```
Relationships: `user`

### `body_profiles` (`BodyProfile`)
```
id          SERIAL PK
user_id     INT FK → users.id NOT NULL, indexed
height      NUMERIC(5,1) NULL   -- cm
weight      NUMERIC(5,1) NULL   -- kg
chest       NUMERIC(5,1) NULL
waist       NUMERIC(5,1) NULL
hip         NUMERIC(5,1) NULL
shoulder    NUMERIC(5,1) NULL
arm_length  NUMERIC(5,1) NULL
inseam      NUMERIC(5,1) NULL
gender      VARCHAR(10) default "neutral"
created_at  TIMESTAMPTZ
updated_at  TIMESTAMPTZ
is_deleted  BOOLEAN
```
> Lưu ý: model có sẵn `beta_hash` / `beta_cache` trong **service & repo** (compute_beta_hash, update_beta_cache) nhưng **column không tồn tại trong model** — đoạn code này sẽ lỗi nếu được dùng (ghi chú để biết).

Relationships: `user`

### `garment_size_specs` (`GarmentSizeSpec`)
```
id              SERIAL PK
garment_id      INT FK → garments.id ON DELETE CASCADE, indexed
size_label      VARCHAR(20)  NOT NULL   -- XS/S/M/L/XL/XXL/XXXL
-- Số đo quần áo (DETAIL mode)
chest_cm        NUMERIC(5,1) NULL
waist_cm        NUMERIC(5,1) NULL
hip_cm          NUMERIC(5,1) NULL
shoulder_cm     NUMERIC(5,1) NULL
length_cm       NUMERIC(5,1) NULL
sleeve_cm       NUMERIC(5,1) NULL
inseam_cm       NUMERIC(5,1) NULL
-- Khuyến nghị cơ thể của shop (BASIC mode)
height_min_cm   NUMERIC(5,1) NULL
height_max_cm   NUMERIC(5,1) NULL
weight_min_kg   NUMERIC(5,1) NULL
weight_max_kg   NUMERIC(5,1) NULL
is_deleted      BOOLEAN default false
created_at      TIMESTAMPTZ
updated_at      TIMESTAMPTZ
UNIQUE(garment_id, size_label)
```
Helper: `to_dict()` chuyển sang dict (cast Decimal → float, None giữ nguyên).
Relationships: `garment`

### `tryon_history` (`TryonHistory`)
```
id               SERIAL PK
user_id          INT FK → users.id ON DELETE SET NULL NULL, indexed  -- nullable cho guest
garment_id       INT FK → garments.id ON DELETE SET NULL NULL, indexed
result_image_url STRING NOT NULL
public_id        STRING NULL          -- Cloudinary public_id
width            INT NULL
height           INT NULL
cloth_type       VARCHAR(20) NOT NULL default "upper"  -- upper | lower | overall
seed             INT NULL
num_steps        INT NULL
guidance         FLOAT NULL
resolution       VARCHAR(20) NULL     -- 768x1024 | 1152x1536 | 1536x2048
is_deleted       BOOLEAN default false
created_at       TIMESTAMPTZ
```
Relationships: `user`, `garment`

### `chat_sessions` (`ChatSession`)
```
id          SERIAL PK
user_id     INT FK → users.id NOT NULL, indexed
title       VARCHAR(255) NOT NULL default "Cuộc trò chuyện mới"
created_at  TIMESTAMPTZ
updated_at  TIMESTAMPTZ
```
Relationships: `messages` (cascade delete, selectin)

### `chat_messages` (`ChatMessage`)
```
id                  SERIAL PK
session_id          INT FK → chat_sessions.id ON DELETE CASCADE NOT NULL, indexed
role                VARCHAR(20) NOT NULL    -- user | assistant
content             TEXT NOT NULL
suggested_products  TEXT NULL               -- JSON string
image_url           VARCHAR(500) NULL
created_at          TIMESTAMPTZ
```
Relationships: `session`

### `product_embeddings` (`ProductEmbedding`) — pgvector
```
id                    SERIAL PK
firestore_product_id  VARCHAR(100) UNIQUE, indexed
name                  VARCHAR(500) NOT NULL
brand                 VARCHAR(100) NULL
price                 INT NULL
images_json           VARCHAR(2000) NULL    -- JSON array
text_embedding        Vector(768)            -- nomic-embed-text
image_embedding       Vector(768)            -- nomic-embed-vision
synced_at             TIMESTAMPTZ
```
Index: HNSW cosine ops cho cả `text_embedding` + `image_embedding` (m=16, ef_construction=64).

> `EMBED_DIM = 768`

---

## 3. SERVICES — Class & methods

### `user_service.py — UserService(repo)`
- `upsert(data: UserCreate) -> User`
- `get_by_id(id) -> User`
- `get_by_firebase_uid(firebase_uid) -> User`
- `get_all(skip=0, limit=20) -> list[User]`
- `update(id, data: UserUpdate) -> User`
- `delete(id) -> None`

### `address_service.py — AddressService(repo, user_repo)`
- `create(user_id, data)`
- `get_by_id(user_id, id)`
- `get_all_by_user(user_id)`
- `update(user_id, id, data)`
- `delete(user_id, id)`
- `set_default(user_id, id)`

### `garment_service.py` — **module-level functions** (không class)
- `_upload_cloth_image(file)` — internal
- `create_garment(db, data, cloth_image=None)`
- `get_garments_by_firestore_id(db, firestore_product_id)`
- `get_all_garments(db)`
- `get_garment_by_id(db, garment_id)`
- `update_garment(db, garment_id, data, cloth_image=None)`
- `delete_garment(db, garment_id)` — soft + xóa Cloudinary
- `get_lens_link(db, garment_id)`
- Constants: `LENS_ID`, `CLOTH_IMAGE_FOLDER`, `ALLOWED_IMAGE_TYPES`

### `garment_category_service.py — GarmentCategoryService(repo)`
- `create`, `get_by_id`, `get_all`, `update`, `delete`

### `store_service.py — StoreService(repo)`
- `create`, `get_by_id`, `get_all(skip, limit, is_active)`, `update`, `delete`

### `review_service.py — ReviewService(repo)`
- `create(data)` — auto-update nếu user đã có review cho product
- `get_user_review(user_id, firestore_product_id)`
- `get_by_id(id)`
- `get_all(firestore_product_id, user_id, rating, skip, limit)`
- `update(id, data)`
- `delete(id)`
- `get_product_stats(firestore_product_id)`

### `body_profile_service.py — BodyProfileService(repo, user_repo)`
- `compute_beta_hash(data)` classmethod — sha256(payload), 16 char
- `create_or_update_profile(user_id, data: BodyProfileCreate)`
- > **Service chưa được sử dụng** — không có router nào gọi (chỉ `fit_assessment` đọc body_profile qua repo).

### `fit_assessment_service.py`
Constants: `SIZE_ORDER = ["XS","S","M","L","XL","XXL","XXXL"]`, `FIT_EASE`, `RECOMMENDATIONS`.

Module-level helpers:
- `_sorted_sizes`, `_classify_ease`, `_aggregate_overall`
- `_suggest_size_from_specs(body, specs)` — chọn size có nhiều region "good" nhất
- `_basic_size_lookup(height_cm, weight_kg, specs)` — exact match → fallback closest weight

Public stateless functions:
- `assess_fit_detail(body, specs, selected_size=None) -> dict` (mode="detail")
- `assess_fit_basic(height_cm, weight_kg, specs) -> dict` (mode="basic")

Class `FitAssessmentService(body_profile_repo, size_spec_repo)`:
- `_profile_to_body_dict(profile)` static
- `_has_detail_measurements(body)` static — ≥2 trong (chest/waist/hip)
- `suggest(garment_id, user_id=None, guest_measurements=None, selected_size=None)`

### `fitdit_service.py` — module functions (httpx.Client + AsyncClient)
- `is_available() -> bool` — GET `/health`
- `get_status() -> dict`
- `try_on(person_path, garment_path, ...)` — sync wrapper
- `try_on_from_pil(person_img, garment_img, category, num_steps, guidance_scale, seed, request_id)` — sync POST `/try-on`
- `try_on_async(...)`
- `try_on_from_pil_async(...)` — POST `/submit` → poll `/status/{job_id}` mỗi 5s, timeout `FITDIT_TIMEOUT` (default 3600s)
- Internal: `_pil_to_base64`, `_base64_to_pil`, `_load_image`, `_get_base_url`, `_make_client`

### `cloudinary_service.py` — module functions
- `upload_image(pil_image, folder="tryon_results", public_id=None)`
- `get_image(public_id)`
- `list_images(folder, max_results=50)`
- `delete_image(public_id)`
- `delete_all_images(folder)`

### `embedding_service.py` — module functions
- `_get_firestore()` — internal, init firebase_admin nếu chưa
- `embed_text(text) -> list[float]` (`nomic-embed-text` qua Ollama)
- `build_text_input(data)` — `[category] [gender] name | brand | short_desc`
- `embed_image_from_url(url) -> list[float] | None`
- `embed_image_from_bytes(bytes) -> list[float]`
- `sync_all_products(repo)` — Firestore `products` → embed → upsert

### `chatbot_service.py`
Module helpers:
- `_keyword_filter(rows, query)` — dùng `EXCLUDE_MAP`
- `_build_query_text(message)` — prefix category + gender
- `warmup_model()`
- `_format_context(products)`, `_to_product_out(row)`, `_call_ollama(msgs)`
- Constants: `MODEL = "qwen2.5:7b"`, `SYSTEM_PROMPT`, `EXCLUDE_MAP`

Class `ChatbotService(chat_repo, embed_repo)`:
- `create_session(user_id, title)`
- `get_session(session_id)`
- `get_sessions(user_id, skip, limit)`
- `update_session_title(session_id, title)`
- `delete_session(session_id)`
- `delete_message(message_id)`
- `chat(session_id, user_id, message)` — embed + search top-3 → filter → top-2 → ollama
- `search_by_image_url(url, top_k=5)`
- `search_by_image_bytes(bytes, top_k=5)`
- `get_embeddings(skip, limit, search="")`
- `get_embedding_stats()`
- `delete_embedding(firestore_product_id)`

### `payment_service.py — PaymentService(repo)`
- `create_stripe_session(req: StripeCreateRequest)` — VND → USD cents (≥50¢), tạo Stripe Checkout
- `handle_success(session_id, order_id)` — verify + ghi Firestore

---

## 4. REPOSITORIES — Class & methods

### `UserRepository(db)`
- `create(data)`, `get_by_id(id)`, `get_by_firebase_uid`, `get_by_email`
- `get_all(skip, limit)`, `update(id, data)`, `delete(id)` (soft), `count()`

### `StoreRepository(db)`
- `create`, `get_by_id`, `get_by_email`, `get_all(skip, limit, is_active=None)`
- `update`, `delete` (soft), `count(is_active=None)`

### `AddressRepository(db)`
- `create(user_id, data)`, `get_by_id`, `get_all_by_user(user_id)`, `get_all(skip, limit)`
- `update`, `delete` (soft), `clear_default_for_user(user_id)`, `count()`

### `GarmentRepository(db)` — **tối thiểu**
- `get_by_id(id)`
> Các operation create/update/delete/list cho garment nằm trong `garment_service.py` (module functions).

### `GarmentCategoryRepository(db)`
- `create`, `get_by_id`, `get_all(skip, limit)`, `update`, `delete` (soft), `count()`

### `BodyProfileRepository(db)`
- `create(user_id, data: dict)`, `get_by_id`, `get_by_user_id(user_id)`
- `get_by_beta_hash(beta_hash)` ⚠️ **column không tồn tại**
- `update(profile_id, **kwargs)`
- `update_beta_cache(profile_id, beta_cache, beta_hash)` ⚠️ **column không tồn tại**
- `soft_delete(profile_id)`

### `GarmentSizeSpecRepository(db)`
- `get_by_garment_id(garment_id)`
- `get_by_garment_and_size(garment_id, size_label)`
- `upsert(garment_id, size_label, data)` — yêu cầu `weight_min_kg` + `weight_max_kg`
- `bulk_upsert(garment_id, sizes: list[dict])`
- `soft_delete_by_garment(garment_id)`

### `TryonHistoryRepository(db)`
- `create(data: dict)`
- `get_by_user_id(user_id, limit=20, offset=0)`
- `get_by_id(record_id)`
- `soft_delete(record_id)` ⚠️ chưa có endpoint expose

### `ReviewRepository(db)`
- `create(data)` — serialize media_urls list → JSON string
- `get_by_id`, `get_by_user_and_product(user_id, firestore_product_id)`
- `get_all(firestore_product_id, user_id, rating, skip, limit)` — join User để lấy `display_name` + `avatar_url`
- `update`, `delete` (soft)
- `count(firestore_product_id=None)`
- `get_stats(firestore_product_id)` — `{avg_rating, total_reviews, distribution}`

### `ChatRepository(db)`
Sessions:
- `create_session(user_id, title)`, `get_session(session_id)`
- `get_sessions_by_user(user_id, skip, limit)`
- `update_session_title(session_id, title)`, `delete_session(session_id)`

Messages:
- `add_message(session_id, role, content, suggested_products=None, image_url=None)`
- `get_messages(session_id)`, `delete_message(message_id)`

### `EmbeddingRepository(db)`
- `upsert(data: dict)`
- `search_by_text(vector, top_k=5)` — hard-coded `LIMIT 2`, threshold 0.72
- `search_by_image(vector, top_k=5)` — threshold 0.6
- `count(search="")` — có 2 định nghĩa `count`, bản sau (có `search`) override bản trước
- `get_all(skip, limit, search="")`
- `get_stats()` → `{total, has_text, has_image, has_both}`
- `delete(firestore_product_id)`

### `PaymentRepository()` — **Firestore, không phải Neon**
- `db` lazy property → init firebase_admin
- `update_payment_status(order_id, payment_status, transaction_no=None, vnpay_response_code=None)` — ghi `orders/{order_id}`
- `save_stripe_session(order_id, session_id)`

---

## 5. SCHEMAS — Pydantic v2

### `user.py`
- `UserCreate(firebase_uid, email, display_name?, phone?, avatar_url?)`
- `UserUpdate` — tất cả optional
- `UserResponse` — `from_attributes=True`, full fields

### `store.py`
- `StoreBase` — name + tất cả optional fields, `is_active=True`
- `StoreCreate(StoreBase)` — thêm `user_id: int`
- `StoreUpdate` — tất cả optional
- `StoreResponse(StoreBase)` — `id: UUID`, `user_id`, timestamps

### `address.py`
- `addressType = Literal["Nhà riêng", "Cơ quan", "Khác"]`
- `ADDRESS_TYPES = ["Nhà riêng", "Cơ quan", "Khác"]`
- `AddressCreate` — `full_name, phone, address_type, address, city?, district?, ward?, lat?, long?, is_default=False` + validate phone 10-11 số
- `AddressUpdate` — optional all
- `AddressResponse` — `from_attributes=True`

### `garment.py`
- `GarmentCreate(name, description?, item_index?, category_id?, store_id?, firestore_product_id?, color?)`
- `GarmentUpdate` — optional
- `GarmentResponse` — `from_attributes=True`, gồm `cloth_image_url`, `cloth_image_public_id`
- `LensLinkResponse(lens_url, product_id)`

### `garment_category.py`
- `GarmentCategoryCreate(name, description?)`
- `GarmentCategoryUpdate` — optional
- `GarmentCategoryResponse` — `from_attributes=True`

### `review.py`
- `ReviewCreate(user_id, firestore_product_id, rating, comment?, media_urls?)` — validate rating 1..5
- `ReviewUpdate(rating?, comment?)`
- `ReviewResponse` — kèm `display_name`, `avatar_url` (join từ User)
- `ReviewStatsResponse(avg_rating, total_reviews, distribution: dict[str, int])`

### `body_profile.py`
- `BodyProfileCreate(height?, weight?, chest?, waist?, hip?, shoulder?, arm_length?, inseam?, gender="neutral")`
- `BodyProfileResponse` — `from_attributes=True`

### `payment.py`
- `StripeCreateRequest(order_id, amount, order_desc="Thanh toan don hang GlowUp")`
- `StripeCreateResponse(payment_url)`

### `chatbot.py`
- `ProductOut(id, name, price, images, brand, score?)`
- `MessageIn(role, content)`
- `MessageOut(id, role, content, suggested_products?, image_url?, created_at)` — `from_attributes`
- `SessionCreate(user_id, title?)`
- `SessionOut(id, user_id, title, created_at, updated_at, messages: list[MessageOut])`
- `SessionSummary(id, title, created_at, updated_at)`
- `ChatRequest(session_id, user_id, message, image_url?)`
- `ChatResponse(success, data: ChatResponseData)`
- `ChatResponseData(message, suggested_products: list[ProductOut], session_id)`
- `ImageSearchRequest(image_url, top_k=5)`
- `ImageSearchResponse(success, products: list[ProductOut])`

### `schemas/__init__.py` — re-exports
`UserCreate/Update/Response`, `StoreBase/Create/Update/Response`,
`GarmentCategoryCreate/Update/Response`, `GarmentCreate/Update/Response`, `LensLinkResponse`,
`AddressCreate/Update/Response`, `ReviewCreate/Update/Response/StatsResponse`.

### Schemas khai báo inline trong router
- `fit_router.py`: `GuestMeasurements`, `SuggestRequest`, `SizeSpecIn`

---

## 6. Fit Assessment Logic

### BASIC mode (height + weight)
Tra spec có range khớp; nếu không match, fallback closest weight.

### DETAIL mode (chest/waist/hip ≥ 2 trường)
`ease = garment_cm - body_cm`. Phân vùng theo region:

| Region | very_tight | tight | good | loose | very_loose |
|--------|-----------|-------|------|-------|-----------|
| chest  | < -2 | -2..2 | 2..8  | 8..12 | > 12 |
| waist  | < -2 | -2..2 | 2..6  | 6..12 | > 12 |
| hip    | < -2 | -2..2 | 2..8  | 8..12 | > 12 |

Service tự chọn DETAIL nếu `_has_detail_measurements(body)` (≥2 trong chest/waist/hip) — fallback BASIC nếu chỉ có height + weight.

---

## 7. FitDiT Integration
```
ENV: FITDIT_COLAB_URL (ngrok URL)
ENV: FITDIT_TIMEOUT (giây, default 3600)

POST {base}/submit  → { job_id }
GET  {base}/status/{job_id} → { status, result_image, error?, ... }
GET  {base}/health  → { status, model_loaded, vram_used_gb, uptime_s }

Async flow: poll 5s, timeout FITDIT_TIMEOUT.
Sync flow (try_on/try_on_from_pil): POST /try-on trực tiếp, retry MAX_RETRIES=2.
```

---

## 8. Cloudinary
```
Folder garment cloth: ar_garments_cloth
Folder tryon result:  tryon_results
Allowed types: image/jpeg, image/png, image/webp
(KHÔNG upload GLB)
```

---

## 9. Chatbot AI Stack
```
Text embedding:  nomic-embed-text  (768 dim) — qua Ollama
Image embedding: nomic-embed-vision (768 dim) — qua Ollama
LLM:             qwen2.5:7b — qua Ollama
Vector search:   pgvector cosine, HNSW index
Threshold text:  0.72
Threshold image: 0.60
Search flow:     top-3 → keyword filter (EXCLUDE_MAP) → top-2 final
```

---

## 10. Settings (`config.py` + `.env`)
```
BASE_DIR
DEFAULT_STEPS=20, DEFAULT_GUIDANCE=2.0, DEFAULT_SEED=42
IMAGE_WIDTH=768, IMAGE_HEIGHT=1024
HOST=0.0.0.0, PORT=8000
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]
CLOUDINARY_CLOUD_NAME / API_KEY / API_SECRET / UPLOAD_PRESET / API_URL
DATABASE_URL                # Neon (auto strip sslmode, channel_binding)
BASE_URL=http://localhost:8000
STRIPE_SECRET_KEY
FE_BASE_URL=http://localhost:3000
FITDIT_COLAB_URL            # ngrok URL
# Ngoài Settings:
FITDIT_TIMEOUT (os.getenv)
```

---

## 11. Database init (`core/database.py`)
- Async engine, `ssl: require`, pool_pre_ping.
- `init_db()` import toàn bộ model + `CREATE EXTENSION IF NOT EXISTS vector` + `Base.metadata.create_all`.

---

## 12. Checklist — gap so với code thực

### ❓ Có code nhưng chưa expose endpoint
- `BodyProfileService.create_or_update_profile` — chưa có router (FE chưa lấy/lưu body profile).
- `TryonHistoryRepository.soft_delete` — chưa có `DELETE /tryon/history/{id}`.
- `GarmentSizeSpecRepository.soft_delete_by_garment` — chưa expose.
- `EmbeddingRepository.count` định nghĩa **2 lần** (bản trên không có tham số bị bản dưới override).

### ⚠️ Code có bug tiềm tàng
- `body_profile_repository.update_beta_cache` + `get_by_beta_hash` đọc/ghi `beta_hash`/`beta_cache` **không tồn tại trong `BodyProfile` model** — sẽ raise nếu được gọi.
- `chatbot_service.py` còn import `from sympy import limit` thừa.
- `EmbeddingRepository.search_by_text` hard-coded `LIMIT 2` (bỏ qua tham số `top_k`).

### ❌ Còn thiếu (theo FE)
- `GET /body-profiles?user_id=` — FE cần khi vào profile page.
- `POST/PUT /body-profiles` — FE cần để tạo/cập nhật.
- `DELETE /tryon/history/{id}` — FE đang xóa local state.
- Admin endpoint xem toàn bộ tryon history (cross-user).

### Đã hoàn thành
- CRUD: users, addresses, garments, garment_categories, garment_size_specs
- CRUD: reviews, stores
- Try-on: submit/catalog/status/history (in-memory job store)
- Fit assessment: BASIC + DETAIL
- Chatbot: sessions, messages, chat, image search, admin sync/list/delete embeddings
- Payment: Stripe Checkout + success redirect + list/detail

### Đã loại bỏ
- Feature `product_view` (model/repo/service/router/schema) — toàn bộ đã xóa.
- 3D/GLB pipeline, `/static/models` mount, `model_url` column trên garment.
