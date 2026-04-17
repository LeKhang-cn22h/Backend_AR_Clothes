# -*- coding: utf-8 -*-
import os
from huggingface_hub import snapshot_download

BASE_DIR = os.path.dirname(__file__)
MODEL_CACHE = os.path.join(BASE_DIR, "model_cache")

MODELS = [
    ("runwayml/stable-diffusion-inpainting", "sd-inpainting"),
    ("zhengchong/CatVTON", "CatVTON"),
]


def has_files(path):
    if not os.path.exists(path):
        return False
    for _, _, files in os.walk(path):
        if files:
            return True
    return False


def download_all():
    os.makedirs(MODEL_CACHE, exist_ok=True)
    for repo_id, folder_name in MODELS:
        dest = os.path.join(MODEL_CACHE, folder_name)
        if has_files(dest):
            print(f"[SKIP] {repo_id} da ton tai tai {dest}")
            continue
        print(f"[DOWN] Dang tai {repo_id} ve {dest} ...")
        for attempt in range(1, 6):
            try:
                snapshot_download(
                    repo_id=repo_id,
                    local_dir=dest,
                    local_dir_use_symlinks=False,
                    resume_download=True,
                    max_workers=1,
                )
                print(f"[DONE] {repo_id} -> {dest}")
                break
            except Exception as e:
                print(f"[RETRY {attempt}/5] loi: {e}")
                if attempt == 5:
                    print(f"[FAIL] {repo_id} - het so lan thu")


if __name__ == "__main__":
    download_all()