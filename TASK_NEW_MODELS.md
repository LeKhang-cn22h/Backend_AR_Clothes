# Mở rộng Backend_AR_Clothes: Thêm 10 bảng mới

## Mục tiêu
Mở rộng project FastAPI hiện tại bằng cách thêm 9 bảng mới (garments đã có sẵn) với đầy đủ models, schemas, repositories, services, routers theo đúng cấu trúc clean architecture đã có.

## Cấu trúc project hiện tại
```
Backend_AR_Clothes/
├── .env
├── app/
│   ├── main.py
│   ├── config.py
│   ├── dependencies.py
│   ├── core/
│   │   ├── __init__.py
│   │   └── database.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── store.py
│   │   └── garment.py          ← đã có
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── store.py
│   │   └── garment.py          ← đã có
│   ├── repositories/
│   │   ├── __init__.py
│   │   └── store_repository.py
│   ├── services/
│   │   ├── store_service.py
│   │   ├── garment_service.py  ← đã có
│   │   └── catvton.py
│   └── routers/
│       ├── store.py
│       ├── garments.py         ← đã có
│       ├── tryon.py
│       └── images.py
```

## Yêu cầu thêm mới

### Các file cần tạo mới
```
app/
├── models/
│   ├── garment_category.py
│   ├── user.py
│   ├── address.py
│   ├── ar_session.py
│   ├── review.py
│   ├── wishlist.py
│   ├── product_view.py
│   └── conversion_event.py
├── schemas/
│   ├── garment_category.py
│   ├── user.py
│   ├── address.py
│   ├── ar_session.py
│   ├── review.py
│   ├── wishlist.py
│   ├── product_view.py
│   └── conversion_event.py
├── repositories/
│   ├── garment_category_repository.py
│   ├── user_repository.py
│   ├── address_repository.py
│   ├── ar_session_repository.py
│   ├── review_repository.py
│   ├── wishlist_repository.py
│   ├── product_view_repository.py
│   └── conversion_event_repository.py
├── services/
│   ├── garment_category_service.py
│   ├── user_service.py
│   ├── address_service.py
│   ├── ar_session_service.py
│   ├── review_service.py
│   ├── wishlist_service.py
│   ├── product_view_service.py
│   └── conversion_event_service.py
└── routers/
    ├── garment_categories.py
    ├── users.py
    ├── addresses.py
    ├── ar_sessions.py
    ├── reviews.py
    ├── wishlists.py
    ├── product_views.py
    └── conversion_events.py
```

---

## Chi tiết từng bảng

### 1. GarmentCategory (`garment_categories`)
**Trường dữ liệu:**
```
id            Integer     primary key, autoincrement
name          String(100) tên danh mục, required (vd: "Áo", "Quần", "Phụ kiện")
description   Text        mô tả, optional
created_at    DateTime    tự động set khi tạo
```

**Endpoints:**
```
POST   /garment-categories          → tạo mới (201)
GET    /garment-categories          → lấy tất cả (200)
GET    /garment-categories/{id}     → lấy 1 (200)
PUT    /garment-categories/{id}     → cập nhật (200)
DELETE /garment-categories/{id}     → xóa (204)
```

---

### 2. User (`users`)
**Trường dữ liệu:**
```
id            Integer     primary key, autoincrement
firebase_uid  String(128) unique, not null, index (UID từ Firebase Auth)
email         String(255) unique, not null
display_name  String(200) optional
phone         String(20)  optional
avatar_url    String(500) optional
created_at    DateTime    tự động set khi tạo
updated_at    DateTime    tự động cập nhật khi sửa
```

**Endpoints:**
```
POST   /users                       → tạo hoặc upsert theo firebase_uid (201)
GET    /users                       → lấy danh sách (200), query: skip=0, limit=20
GET    /users/{id}                  → lấy 1 theo id (200)
GET    /users/by-uid/{firebase_uid} → lấy theo firebase_uid (200)
PATCH  /users/{id}                  → cập nhật (200)
DELETE /users/{id}                  → xóa (204)
```

**Business logic:**
- Upsert theo `firebase_uid`: nếu đã tồn tại thì update, chưa có thì tạo mới
- Validate email format
- Kiểm tra email trùng khi update

---

### 3. Address (`addresses`)
**Trường dữ liệu:**
```
id            Integer     primary key, autoincrement
user_id       Integer     FK → users.id, not null
full_name     String(200) required
phone         String(20)  required
address       Text        required
city          String(100) optional
district      String(100) optional
ward          String(100) optional
is_default    Boolean     default False
created_at    DateTime    tự động set khi tạo
updated_at    DateTime    tự động cập nhật khi sửa
```

**Endpoints:**
```
POST   /users/{user_id}/addresses           → tạo mới (201)
GET    /users/{user_id}/addresses           → lấy tất cả của user (200)
GET    /users/{user_id}/addresses/{id}      → lấy 1 (200)
PUT    /users/{user_id}/addresses/{id}      → cập nhật (200)
DELETE /users/{user_id}/addresses/{id}      → xóa (204)
PATCH  /users/{user_id}/addresses/{id}/set-default → đặt làm mặc định (200)
```

**Business logic:**
- Khi set `is_default=True` cho 1 address → tự động set `is_default=False` cho tất cả address khác của user đó
- Validate user tồn tại trước khi tạo address

---

### 4. ARSession (`ar_sessions`)
**Trường dữ liệu:**
```
id                    Integer     primary key, autoincrement
user_id               Integer     FK → users.id, nullable (guest user)
garment_id            Integer     FK → garments.id, not null
firestore_product_id  String(100) optional (link sang Firestore)
duration_seconds      Integer     optional (thời gian try-on tính bằng giây)
converted             Boolean     default False (có mua sau khi try-on không)
created_at            DateTime    tự động set khi tạo
```

**Endpoints:**
```
POST   /ar-sessions                 → tạo mới khi user bắt đầu try-on (201)
GET    /ar-sessions                 → lấy danh sách (200), query: user_id, garment_id, converted, skip, limit
GET    /ar-sessions/{id}            → lấy 1 (200)
PATCH  /ar-sessions/{id}/converted  → đánh dấu đã converted (200)
DELETE /ar-sessions/{id}            → xóa (204)
GET    /ar-sessions/stats/summary   → thống kê tổng hợp (200)
```

**Business logic:**
- Validate garment tồn tại khi tạo session
- Endpoint stats trả về: tổng sessions, tổng converted, conversion rate, top garments được try-on

---

### 5. Review (`reviews`)
**Trường dữ liệu:**
```
id                    Integer     primary key, autoincrement
user_id               Integer     FK → users.id, not null
firestore_product_id  String(100) not null, index
rating                Integer     not null, check 1-5
comment               Text        optional
created_at            DateTime    tự động set khi tạo
updated_at            DateTime    tự động cập nhật khi sửa
```

**Endpoints:**
```
POST   /reviews                                     → tạo mới (201)
GET    /reviews                                     → lấy danh sách (200), query: firestore_product_id, user_id, rating, skip, limit
GET    /reviews/{id}                                → lấy 1 (200)
PUT    /reviews/{id}                                → cập nhật (200)
DELETE /reviews/{id}                                → xóa (204)
GET    /reviews/product/{firestore_product_id}/stats → rating trung bình + phân phối (200)
```

**Business logic:**
- Mỗi user chỉ được review 1 lần cho mỗi product (unique constraint user_id + firestore_product_id)
- Validate rating trong khoảng 1-5
- Endpoint stats trả về: avg_rating, total_reviews, distribution {1:x, 2:x, 3:x, 4:x, 5:x}

---

### 6. Wishlist (`wishlists`)
**Trường dữ liệu:**
```
id                    Integer     primary key, autoincrement
user_id               Integer     FK → users.id, not null
firestore_product_id  String(100) not null
garment_id            Integer     FK → garments.id, nullable
created_at            DateTime    tự động set khi tạo
```

**Constraints:**
- UniqueConstraint trên (user_id, firestore_product_id)

**Endpoints:**
```
POST   /wishlists                           → thêm vào wishlist (201)
GET    /wishlists                           → lấy danh sách (200), query: user_id, skip, limit
DELETE /wishlists/{id}                      → xóa khỏi wishlist (204)
DELETE /wishlists/product/{firestore_product_id}?user_id=  → xóa theo product (204)
GET    /wishlists/check?user_id=&firestore_product_id=     → kiểm tra đã wishlist chưa (200)
```

**Business logic:**
- Kiểm tra duplicate trước khi thêm, nếu đã có thì raise 409 Conflict
- Validate user tồn tại

---

### 7. ProductView (`product_views`)
**Trường dữ liệu:**
```
id                    Integer     primary key, autoincrement
user_id               Integer     FK → users.id, nullable (guest)
firestore_product_id  String(100) not null, index
session_id            String(100) optional (browser session ID)
source                String(50)  optional ("web", "snapchat", "qr", "direct")
created_at            DateTime    tự động set khi tạo
```

**Endpoints:**
```
POST   /product-views                                       → ghi nhận lượt xem (201)
GET    /product-views                                       → lấy danh sách (200), query: firestore_product_id, user_id, source, skip, limit
GET    /product-views/product/{firestore_product_id}/count  → đếm lượt xem (200)
GET    /product-views/stats/top-products                    → top sản phẩm được xem nhiều (200), query: limit=10
```

**Business logic:**
- Không cần validate duplicate (ghi nhận tất cả lượt xem)
- Endpoint top-products trả về list {firestore_product_id, view_count} sắp xếp DESC

---

### 8. ConversionEvent (`conversion_events`)
**Trường dữ liệu:**
```
id                    Integer     primary key, autoincrement
user_id               Integer     FK → users.id, nullable (guest)
firestore_product_id  String(100) not null, index
garment_id            Integer     FK → garments.id, nullable
event_type            Enum        not null ("view", "ar_try_on", "add_to_cart", "purchase")
session_id            String(100) optional
created_at            DateTime    tự động set khi tạo
```

**Enum ConversionEventType:**
```python
class ConversionEventType(str, enum.Enum):
    view        = "view"
    ar_try_on   = "ar_try_on"
    add_to_cart = "add_to_cart"
    purchase    = "purchase"
```

**Endpoints:**
```
POST   /conversion-events                                       → ghi nhận event (201)
GET    /conversion-events                                       → lấy danh sách (200), query: firestore_product_id, event_type, user_id, skip, limit
GET    /conversion-events/product/{firestore_product_id}/funnel → funnel analysis (200)
GET    /conversion-events/stats/overview                        → tổng quan (200)
```

**Business logic:**
- Endpoint funnel trả về: {view: x, ar_try_on: x, add_to_cart: x, purchase: x, ar_to_purchase_rate: x%}
- Endpoint overview trả về tổng số event theo từng type trong 30 ngày gần nhất

---

## Yêu cầu sửa file hiện tại

### `app/models/garment.py` — thêm field mới
```python
# Thêm vào model Garment hiện tại:
category_id          = Column(Integer, ForeignKey("garment_categories.id"), nullable=True)
firestore_product_id = Column(String(100), nullable=True)  # link sang Firestore product

# Thêm relationships:
category    = relationship("GarmentCategory", back_populates="garments")
ar_sessions = relationship("ARSession", back_populates="garment")
wishlists   = relationship("Wishlist", back_populates="garment")
```

### `app/schemas/garment.py` — thêm field mới
```python
# Thêm vào GarmentCreate và GarmentUpdate:
category_id: Optional[int] = None
firestore_product_id: Optional[str] = None

# Thêm vào GarmentResponse:
category_id: Optional[int]
firestore_product_id: Optional[str]
```

### `app/main.py` — include routers mới
```python
from routers.garment_categories import router as garment_categories_router
from routers.users import router as users_router
from routers.addresses import router as addresses_router
from routers.ar_sessions import router as ar_sessions_router
from routers.reviews import router as reviews_router
from routers.wishlists import router as wishlists_router
from routers.product_views import router as product_views_router
from routers.conversion_events import router as conversion_events_router

app.include_router(garment_categories_router)
app.include_router(users_router)
app.include_router(addresses_router)
app.include_router(ar_sessions_router)
app.include_router(reviews_router)
app.include_router(wishlists_router)
app.include_router(product_views_router)
app.include_router(conversion_events_router)
```

### `app/core/database.py` — thêm import models mới vào init_db()
```python
# Đảm bảo tất cả models được import trước khi create_all
from models.garment_category import GarmentCategory
from models.user import User
from models.address import Address
from models.ar_session import ARSession
from models.review import Review
from models.wishlist import Wishlist
from models.product_view import ProductView
from models.conversion_event import ConversionEvent
```

---

## Yêu cầu chung cho tất cả files

- Dùng async/await toàn bộ
- Python 3.11, FastAPI, SQLAlchemy 2.0 async, Pydantic v2
- Tất cả string thông báo lỗi bằng tiếng Việt không dấu
- Xử lý đầy đủ: 404 Not Found, 409 Conflict, 400 Bad Request
- Mỗi repository có đầy đủ: create, get_by_id, get_all, update, delete, count
- Mỗi service xử lý business logic, không để logic trong router
- Mỗi router chỉ gọi service, không gọi trực tiếp repository
- Tất cả response model dùng `model_config = ConfigDict(from_attributes=True)`
- Import pattern nhất quán với codebase hiện tại (absolute imports từ app root)

## Thứ tự thực hiện
1. Tạo models (tất cả trước để tránh circular import)
2. Tạo schemas
3. Tạo repositories
4. Tạo services
5. Tạo routers
6. Sửa garment.py (model + schema)
7. Sửa main.py (include routers)
8. Sửa database.py (import models)
9. Chạy server test: `.\start_dev.ps1`