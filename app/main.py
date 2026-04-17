# -*- coding: utf-8 -*-
from asyncio import get_event_loop
from contextlib import asynccontextmanager
import sys
import os

import torch
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from dependencies import init_service
from routers.tryon import router as tryon_router

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))  # Backend_AR_Clothes/
sys.path = [p for p in sys.path if "CatVTON" not in p]

@asynccontextmanager
async def lifespan(app: FastAPI):
    loop = get_event_loop()
    await loop.run_in_executor(None, init_service)
    yield


app = FastAPI(title="Virtual Try-On API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tryon_router)


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