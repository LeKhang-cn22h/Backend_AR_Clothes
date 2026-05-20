# -*- coding: utf-8 -*-
import sys
import os
import uuid
import math
import tempfile
import torch
import numpy as np
from PIL import Image

from config import settings

# Thêm FitDiT vào path nhưng KHÔNG import gradio_sd3
sys.path.insert(0, settings.FITDIT_DIR)

from preprocess.humanparsing.run_parsing import Parsing
from preprocess.dwpose import DWposeDetector
from transformers import CLIPVisionModelWithProjection, CLIPImageProcessor
from src.pose_guider import PoseGuider
from src.utils_mask import get_mask_location
from src.pipeline_stable_diffusion_3_tryon import StableDiffusion3TryOnPipeline
from src.transformer_sd3_garm import SD3Transformer2DModel as SD3Transformer2DModel_Garm
from src.transformer_sd3_vton import SD3Transformer2DModel as SD3Transformer2DModel_Vton


def pad_and_resize(im, new_width=768, new_height=1024, pad_color=(255, 255, 255), mode=Image.LANCZOS):
    old_width, old_height = im.size
    ratio_w = new_width / old_width
    ratio_h = new_height / old_height
    if ratio_w < ratio_h:
        new_size = (new_width, round(old_height * ratio_w))
    else:
        new_size = (round(old_width * ratio_h), new_height)
    im_resized = im.resize(new_size, mode)
    pad_w = math.ceil((new_width - im_resized.width) / 2)
    pad_h = math.ceil((new_height - im_resized.height) / 2)
    new_im = Image.new('RGB', (new_width, new_height), pad_color)
    new_im.paste(im_resized, (pad_w, pad_h))
    return new_im, pad_w, pad_h


def unpad_and_resize(padded_im, pad_w, pad_h, original_width, original_height):
    width, height = padded_im.size
    cropped_im = padded_im.crop((pad_w, pad_h, width - pad_w, height - pad_h))
    return cropped_im.resize((original_width, original_height), Image.LANCZOS)


def resize_image(img, target_size=768):
    width, height = img.size
    scale = target_size / width if width < height else target_size / height
    new_width = int(round(width * scale))
    new_height = int(round(height * scale))
    return img.resize((new_width, new_height), Image.LANCZOS)


class FitDiTService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._loaded = False
        return cls._instance

    def load(self):
        if self._loaded:
            return

        use_cuda = torch.cuda.is_available()
        device = "cuda:0" if use_cuda else "cpu"
        print(f"[FitDiT] CUDA available: {use_cuda}, Device: {device}")

        weight_dtype = torch.float16 if settings.MIXED_PRECISION == "fp16" else torch.bfloat16

        transformer_garm = SD3Transformer2DModel_Garm.from_pretrained(
            os.path.join(settings.FITDIT_CKPT_PATH, "transformer_garm"),
            torch_dtype=weight_dtype
        )
        transformer_vton = SD3Transformer2DModel_Vton.from_pretrained(
            os.path.join(settings.FITDIT_CKPT_PATH, "transformer_vton"),
            torch_dtype=weight_dtype
        )
        pose_guider = PoseGuider(
            conditioning_embedding_channels=1536,
            conditioning_channels=3,
            block_out_channels=(32, 64, 256, 512)
        )
        pose_guider.load_state_dict(torch.load(
            os.path.join(settings.FITDIT_CKPT_PATH, "pose_guider", "diffusion_pytorch_model.bin")
        ))

        image_encoder_large = CLIPVisionModelWithProjection.from_pretrained(
            "openai/clip-vit-large-patch14", torch_dtype=weight_dtype
        )
        image_encoder_bigG = CLIPVisionModelWithProjection.from_pretrained(
            "laion/CLIP-ViT-bigG-14-laion2B-39B-b160k", torch_dtype=weight_dtype
        )

        pose_guider.to(device=device, dtype=weight_dtype)
        image_encoder_large.to(device=device)
        image_encoder_bigG.to(device=device)

        self.pipeline = StableDiffusion3TryOnPipeline.from_pretrained(
            settings.FITDIT_CKPT_PATH,
            torch_dtype=weight_dtype,
            transformer_garm=transformer_garm,
            transformer_vton=transformer_vton,
            pose_guider=pose_guider,
            image_encoder_large=image_encoder_large,
            image_encoder_bigG=image_encoder_bigG,
        )
        self.pipeline.to(device)

        self.dwprocessor = DWposeDetector(model_root=settings.FITDIT_CKPT_PATH, device=device)
        self.parsing_model = Parsing(model_root=settings.FITDIT_CKPT_PATH, device=device)

        self._device = device
        self._weight_dtype = weight_dtype
        self._loaded = True
        print("[FitDiT] Model loaded successfully!")

    @torch.inference_mode()
    def run(
        self,
        person_image: Image.Image,
        cloth_image: Image.Image,
        cloth_type: str = "upper",
        num_steps: int = 30,
        guidance: float = 2.0,
        seed: int = 42,
        resolution: str = "768x1024",
    ) -> Image.Image:
        person_image = person_image.convert("RGB")
        cloth_image = cloth_image.convert("RGB")

        category_map = {
            "upper":   "Upper-body",
            "lower":   "Lower-body",
            "overall": "Dresses",
        }
        category = category_map.get(cloth_type, "Upper-body")
        new_width, new_height = [int(x) for x in resolution.split("x")]

        print(f"[FitDiT] category={category}, steps={num_steps}, guidance={guidance}, seed={seed}")

        # Bước 1: Generate mask
        vton_img_det = resize_image(person_image)
        pose_image_np, keypoints, _, candidate = self.dwprocessor(np.array(vton_img_det)[:, :, ::-1])
        candidate[candidate < 0] = 0
        candidate = candidate[0]
        candidate[:, 0] *= vton_img_det.width
        candidate[:, 1] *= vton_img_det.height

        model_parse, _ = self.parsing_model(vton_img_det)
        mask, mask_gray = get_mask_location(
            category, model_parse, candidate,
            model_parse.width, model_parse.height,
            0, 0, 0, 0
        )
        mask = mask.resize(person_image.size).convert("L")
        mask_gray = mask_gray.resize(person_image.size).convert("L")

        pose_image = Image.fromarray(pose_image_np[:, :, ::-1])

        # Bước 2: Pad và resize
        model_image_size = person_image.size
        garm_img_padded, _, _ = pad_and_resize(cloth_image, new_width=new_width, new_height=new_height)
        vton_img_padded, pad_w, pad_h = pad_and_resize(person_image, new_width=new_width, new_height=new_height)
        mask_padded, _, _ = pad_and_resize(mask.convert("RGB"), new_width=new_width, new_height=new_height, pad_color=(0, 0, 0))
        mask_padded = mask_padded.convert("L")
        pose_padded, _, _ = pad_and_resize(pose_image, new_width=new_width, new_height=new_height, pad_color=(0, 0, 0))

        # Bước 3: Run pipeline
        results = self.pipeline(
            height=new_height,
            width=new_width,
            guidance_scale=guidance,
            num_inference_steps=num_steps,
            generator=torch.Generator("cpu").manual_seed(seed),
            cloth_image=garm_img_padded,
            model_image=vton_img_padded,
            mask=mask_padded,
            pose_image=pose_padded,
            num_images_per_prompt=1,
        ).images

        result = unpad_and_resize(results[0], pad_w, pad_h, model_image_size[0], model_image_size[1])
        print(f"[FitDiT] Result size: {result.size}")
        return result