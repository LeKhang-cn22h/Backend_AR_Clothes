import os
import requests
import torch
import lpips
import pandas as pd

from PIL import Image
from torchvision import transforms
from skimage.metrics import structural_similarity as ssim
from skimage.metrics import peak_signal_noise_ratio as psnr
import cv2
import numpy as np

# =========================
# CONFIG
# =========================

images = {
    "20_steps": "https://res.cloudinary.com/dziuocdnw/image/upload/v1780042457/tryon_results/tryon_results/1780042448_42_54f97135.jpg",
    "25_steps": "https://res.cloudinary.com/dziuocdnw/image/upload/v1780042916/tryon_results/tryon_results/1780042908_42_84102ed8.jpg",
    "10_steps_1": "https://res.cloudinary.com/dziuocdnw/image/upload/v1780060617/tryon_results/tryon_results/1780060608_42_4a307eb4.jpg",
    "10_steps_2": "https://res.cloudinary.com/dziuocdnw/image/upload/v1780060653/tryon_results/tryon_results/1780060645_42_cd24cb15.jpg",
    "10_steps_3": "https://res.cloudinary.com/dziuocdnw/image/upload/v1780061378/tryon_results/tryon_results/1780061369_42_945521ea.jpg",
    "10_steps_4": "https://res.cloudinary.com/dziuocdnw/image/upload/v1780061440/tryon_results/tryon_results/1780061432_42_dc494e09.jpg",
}

BASELINE = "20_steps"

DOWNLOAD_DIR = "benchmark_images"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# =========================
# DOWNLOAD IMAGES
# =========================

def download_image(url, path):
    response = requests.get(url)
    response.raise_for_status()

    with open(path, "wb") as f:
        f.write(response.content)

    return path


local_paths = {}

print("Downloading images...")

for name, url in images.items():
    save_path = os.path.join(DOWNLOAD_DIR, f"{name}.jpg")
    download_image(url, save_path)
    local_paths[name] = save_path

print("Done downloading.\n")

# =========================
# LOAD IMAGE
# =========================

def load_image_cv(path):
    img = cv2.imread(path)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    return img

def resize_same(img1, img2):
    h = min(img1.shape[0], img2.shape[0])
    w = min(img1.shape[1], img2.shape[1])

    img1 = cv2.resize(img1, (w, h))
    img2 = cv2.resize(img2, (w, h))

    return img1, img2

# =========================
# LPIPS SETUP
# =========================

loss_fn = lpips.LPIPS(net='alex')

transform = transforms.Compose([
    transforms.Resize((256, 256)),
    transforms.ToTensor(),
])

def load_lpips_image(path):
    image = Image.open(path).convert("RGB")
    tensor = transform(image)
    tensor = tensor * 2 - 1
    return tensor.unsqueeze(0)

# =========================
# BASELINE
# =========================

baseline_cv = load_image_cv(local_paths[BASELINE])
baseline_lpips = load_lpips_image(local_paths[BASELINE])

# =========================
# BENCHMARK
# =========================

results = []

for name, path in local_paths.items():

    if name == BASELINE:
        continue

    current_cv = load_image_cv(path)

    # Resize same size
    img1, img2 = resize_same(baseline_cv, current_cv)

    # Convert grayscale for SSIM
    gray1 = cv2.cvtColor(img1, cv2.COLOR_RGB2GRAY)
    gray2 = cv2.cvtColor(img2, cv2.COLOR_RGB2GRAY)

    # SSIM
    ssim_score = ssim(gray1, gray2)

    # PSNR
    psnr_score = psnr(img1, img2)

    # LPIPS
    current_lpips = load_lpips_image(path)

    with torch.no_grad():
        lpips_score = loss_fn(
            baseline_lpips,
            current_lpips
        ).item()

    results.append({
        "compare_to": BASELINE,
        "target": name,
        "SSIM": round(ssim_score, 4),
        "PSNR": round(psnr_score, 4),
        "LPIPS": round(lpips_score, 4),
    })

# =========================
# RESULT TABLE
# =========================

df = pd.DataFrame(results)

print("\n===== BENCHMARK RESULT =====\n")
print(df)

# Save CSV
csv_path = "benchmark_result.csv"
df.to_csv(csv_path, index=False)

print(f"\nSaved CSV => {csv_path}")
