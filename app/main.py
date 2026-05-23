import sys
import os
import asyncio

print("__file__:", __file__)
print("dirname:", os.path.dirname(os.path.abspath(__file__)))
print("sys.path before:", sys.path[:3])

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("sys.path after:", sys.path[:5])

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from config import settings
from dependencies import init_service
from core.database import init_db

from routers.tryon import router as tryon_router
from routers.images import router as images_router
from routers.store import router as store_router
from routers.garments import router as garments_router
from routers.garment_categories import router as garment_categories_router
from routers.users import router as users_router
from routers.addresses import router as addresses_router
from routers.reviews import router as reviews_router
from routers.chatbot import router as chatbot_router
from routers.payment import router as payment_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    os.makedirs(settings.GLB_STATIC_DIR, exist_ok=True)
    yield


app = FastAPI(title="Virtual Try-On API", lifespan=lifespan)


class NgrokHeaderMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["ngrok-skip-browser-warning"] = "true"
        return response


app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.add_middleware(NgrokHeaderMiddleware)
app.mount("/static/models", StaticFiles(directory=settings.GLB_STATIC_DIR, check_dir=False), name="glb_models")

app.include_router(tryon_router)
app.include_router(images_router)
app.include_router(store_router)
app.include_router(garments_router)
app.include_router(garment_categories_router)
app.include_router(users_router)
app.include_router(addresses_router)
app.include_router(reviews_router)
app.include_router(chatbot_router)
app.include_router(payment_router)


@app.get("/health")
def health():
    from services import fitdit_service
    return {
        "status": "ok",
        "fitdit_available": fitdit_service.is_available(),
        "fitdit_url": fitdit_service._get_base_url(),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
