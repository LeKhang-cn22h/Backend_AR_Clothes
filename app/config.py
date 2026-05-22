import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    BASE_DIR:           str   = os.path.dirname(os.path.dirname(__file__))

    DEFAULT_STEPS:      int   = 20
    DEFAULT_GUIDANCE:   float = 2.0
    DEFAULT_SEED:       int   = 42
    IMAGE_WIDTH:        int   = 768
    IMAGE_HEIGHT:       int   = 1024

    HOST:               str   = "0.0.0.0"
    PORT:               int   = 8000
    CORS_ORIGINS:       list  = ["http://localhost:5173", "http://localhost:3000"]

    CLOUDINARY_CLOUD_NAME:    str = ""
    CLOUDINARY_API_KEY:       str = ""
    CLOUDINARY_API_SECRET:    str = ""
    CLOUDINARY_UPLOAD_PRESET: str = ""
    CLOUDINARY_API_URL:       str = ""

    DATABASE_URL:       str = ""
    GLB_STATIC_DIR:     str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "models")
    BASE_URL:           str = "http://localhost:8000"

    STRIPE_SECRET_KEY:  str = ""
    FE_BASE_URL:        str = "http://localhost:3000"
    FITDIT_COLAB_URL:   str = ""

    class Config:
        env_file = ".env"

settings = Settings()
