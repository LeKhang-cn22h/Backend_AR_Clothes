Tôi đang xây dựng một FastAPI service. Hãy dựng cho tôi một CRUD service hoàn chỉnh cho "Thông tin cửa hàng" (Store) kết nối với PostgreSQL trên Neon.

## Cấu trúc project hiện tại
Backend_AR_Clothes/
├── .env
├── app/
│   ├── main.py
│   ├── config.py
│   ├── dependencies.py
│   ├── routers/
│   │   └── tryon.py
│   └── services/
│       └── catvton.py

## Yêu cầu tạo thêm các folder và file sau
app/
├── core/
│   ├── init.py
│   └── database.py          ← SQLAlchemy async engine kết nối Neon PostgreSQL
│
├── models/
│   ├── init.py
│   └── store.py             ← SQLAlchemy ORM model
│
├── schemas/
│   ├── init.py
│   └── store.py             ← Pydantic schemas (request/response)
│
├── repositories/
│   ├── init.py
│   └── store_repository.py  ← tầng truy vấn database
│
├── routers/
│   └── store.py             ← API endpoints
│
└── services/
└── store_service.py     ← business logic

## Trường dữ liệu Store
id            UUID        primary key, auto generate
name          String      tên cửa hàng, required, max 255
description   Text        mô tả, optional
address       String      địa chỉ, required, max 500
phone         String      số điện thoại, required, max 20
email         String      email liên hệ, optional, unique
website       String      website, optional
logo_url      String      URL logo từ Cloudinary, optional
banner_url    String      URL banner từ Cloudinary, optional
is_active     Boolean     trạng thái hoạt động, default True
created_at    DateTime    tự động set khi tạo
updated_at    DateTime    tự động cập nhật khi sửa

## Yêu cầu từng file

### `app/core/database.py`
- Dùng SQLAlchemy async với asyncpg driver
- Kết nối Neon PostgreSQL qua DATABASE_URL trong .env
- Tạo async engine, AsyncSession, Base
- Hàm get_db() làm FastAPI dependency
- Hàm init_db() tạo tables khi startup

### `app/models/store.py`
- SQLAlchemy ORM model tên bảng "stores"
- Đầy đủ các trường như trên
- id dùng UUID type
- created_at và updated_at dùng server_default và onupdate

### `app/schemas/store.py`
- StoreBase: các trường chung
- StoreCreate: kế thừa StoreBase, dùng khi tạo mới
- StoreUpdate: tất cả trường Optional, dùng khi cập nhật
- StoreResponse: kế thừa StoreBase, thêm id/created_at/updated_at, dùng khi trả về
- Dùng model_config = ConfigDict(from_attributes=True)

### `app/repositories/store_repository.py`
- Class StoreRepository nhận AsyncSession
- Các method:
  - create(store_create) → Store
  - get_by_id(id) → Store | None
  - get_by_email(email) → Store | None
  - get_all(skip, limit, is_active) → list[Store]
  - update(id, store_update) → Store | None
  - delete(id) → bool
  - count(is_active) → int

### `app/services/store_service.py`
- Class StoreService nhận StoreRepository
- Xử lý business logic:
  - Kiểm tra email trùng khi tạo/cập nhật
  - Raise HTTPException đúng status code
  - Không để business logic trong router

### `app/routers/store.py`
- APIRouter prefix="/stores"
- Đầy đủ 5 endpoints:
  - POST   /stores          → tạo mới (201)
  - GET    /stores          → lấy danh sách (200), query params: skip=0, limit=10, is_active=None
  - GET    /stores/{id}     → lấy 1 theo id (200)
  - PATCH  /stores/{id}     → cập nhật một phần (200)
  - DELETE /stores/{id}     → xóa (204)

### `.env` thêm
DATABASE_URL=postgresql+asyncpg://user:password@host/dbname

### `app/config.py` thêm
- DATABASE_URL field

### `app/main.py` sửa`
- Gọi init_db() trong lifespan startup
- Include router stores

## Yêu cầu chung
- Dùng async/await toàn bộ
- Python 3.11, FastAPI, SQLAlchemy 2.0 async
- Pydantic v2
- Tất cả string thông báo lỗi không dấu tiếng Việt
- Không hardcode connection string
- Xử lý đầy đủ các trường hợp: not found (404), conflict (409), bad request (400)
- Cài thêm: `pip install sqlalchemy asyncpg`