import sys
import os
import asyncio
# Debug
print("__file__:", __file__)
print("dirname:", os.path.dirname(os.path.abspath(__file__)))
print("sys.path before:", sys.path[:3])

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))      # thêm app/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # thêm Backend_AR_Clothes/
sys.path = [p for p in sys.path if "CatVTON" not in p]

print("sys.path after:", sys.path[:5])
import torch
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import settings
from dependencies import init_service
from routers.tryon import router as tryon_router
from routers.images import router as images_router
from routers.store import router as store_router
from core.database import init_db
from models.garment import Garment
from routers.garments import router as garments_router
from routers.garment_categories import router as garment_categories_router
from routers.users import router as users_router
from routers.addresses import router as addresses_router
from routers.ar_sessions import router as ar_sessions_router
from routers.reviews import router as reviews_router
from routers.wishlists import router as wishlists_router
from routers.product_views import router as product_views_router
from routers.conversion_events import router as conversion_events_router
from routers.photo_tryon import router as photo_tryon_router
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    os.makedirs(settings.GLB_STATIC_DIR, exist_ok=True)
    await asyncio.get_event_loop().run_in_executor(None, init_service)
    yield


app = FastAPI(title="Virtual Try-On API", lifespan=lifespan)


class NgrokHeaderMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["ngrok-skip-browser-warning"] = "true"
        return response
    

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(NgrokHeaderMiddleware)

app.mount(
    "/static/models",
    StaticFiles(directory=settings.GLB_STATIC_DIR,check_dir=False),
    name="glb_models"
)

app.include_router(tryon_router)
app.include_router(images_router)
app.include_router(store_router)
app.include_router(garments_router)
app.include_router(garment_categories_router)
app.include_router(users_router)
app.include_router(addresses_router)
app.include_router(ar_sessions_router)
app.include_router(reviews_router)
app.include_router(wishlists_router)
app.include_router(product_views_router)
app.include_router(conversion_events_router)
app.include_router(photo_tryon_router)

@app.get("/health")
def health():
    available = torch.cuda.is_available()
    gpu_name = torch.cuda.get_device_name(0) if available else None
    return {
        "status": "ok",
        "gpu_available": available,
        "gpu_name": gpu_name,
    }
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)