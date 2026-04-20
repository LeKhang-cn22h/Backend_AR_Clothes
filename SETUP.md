#  Setup Backend AR Clothes
## Clone các repo cần thiết

Trước khi setup, clone các repo sau vào thư mục gốc của project:

### 1. CatVTON (Virtual Try-On model)
```bash
git clone https://github.com/Zheng-Chong/CatVTON.git
```

### 2. DensePose
```bash
git clone https://github.com/facebookresearch/detectron2.git densepose_
```
> Hoặc nếu dùng bản riêng:
```bash
git clone https://github.com/facebookresearch/DensePose.git densepose_
```

### 3. Detectron2
```bash
git clone https://github.com/facebookresearch/detectron2.git
cd detectron2
pip install -e .
cd ..
```

---

> **Lưu ý:** Sau khi clone xong, cấu trúc thư mục sẽ như sau:
> ```
> BACKEND_AR_CLOTHES/
> ├── app/
> ├── CatVTON/
> ├── densepose_/
> ├── detectron2/
> ├── model_cache/
> ├── .env
> ├── download_models.py
> ├── requirements.txt
> └── SETUP.md
> ```
## 1. Tạo virtual environment

```bash
python -m venv venv
```

## 2. Kích hoạt môi trường

### Windows:

```bash
venv\Scripts\activate
```

### MacOS / Linux:

```bash
source venv/bin/activate
```

---

## 3. Cài đặt thư viện

Nếu đã có file `requirements.txt`:

```bash
pip install -r requirements.txt
```

---

## 4. Tạo requirements.txt (nếu chưa có)

### Cách nhanh (full tất cả thư viện):

```bash
pip freeze > requirements.txt
```

### Cách chuẩn (khuyến nghị):

```bash
pip install pipreqs
pipreqs .
```

---

## 5. Chạy server

### Nếu dùng FastAPI:

```bash
uvicorn main:app --reload
```

### Nếu dùng Flask:

```bash
python app.py
```

---

## 6. Một số lỗi thường gặp

###  Lỗi thiếu thư viện

```bash
ModuleNotFoundError
```

Chạy lại:

```bash
pip install -r requirements.txt
```

---

###  Sai môi trường (global vs venv)

Đảm bảo có `(venv)` trước dòng lệnh

---

###  Lỗi CUDA / Torch

Kiểm tra version phù hợp GPU hoặc dùng bản CPU:

```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

---

## 7. Gợi ý tối ưu requirements.txt

Không nên để file quá nặng (~200 libs như hiện tại)

 Chỉ giữ các lib chính:

* fastapi / flask
* opencv-python
* mediapipe
* numpy
* torch
* transformers
* rembg

---

## Ghi chú

* Luôn activate venv trước khi chạy project
* Không commit thư mục `venv/` lên Git
* Nên commit `requirements.txt`

---

##  Hoàn tất

Sau khi setup xong, truy cập:

```
http://127.0.0.1:8000
```

hoặc endpoint API tương ứng
