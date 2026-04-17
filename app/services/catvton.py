# -*- coding: utf-8 -*-
import sys
import os
import torch
from diffusers.image_processor import VaeImageProcessor
from PIL import Image

from config import settings

sys.path.insert(0, settings.CATVTON_DIR)

from model.pipeline import CatVTONPipeline
from model.cloth_masker import AutoMasker
from utils import init_weight_dtype, resize_and_crop, resize_and_padding


class CatVTONService:
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
        device = "cuda" if use_cuda else "cpu"
        print(f"[DEBUG] CUDA available: {use_cuda}")
        print(f"[DEBUG] Device: {device}")

        weight_dtype = init_weight_dtype(settings.MIXED_PRECISION)

        if settings.ALLOW_TF32 and use_cuda:
            torch.backends.cuda.matmul.allow_tf32 = True

        self.pipeline = CatVTONPipeline(
            base_ckpt=settings.SD_INPAINTING_PATH,
            attn_ckpt=settings.CATVTON_CKPT_PATH,
            attn_ckpt_version="mix",
            weight_dtype=weight_dtype,
            use_tf32=settings.ALLOW_TF32,
            device=device,
            skip_safety_check=True,
        )
        # try:
        #     self.pipeline.unet.enable_xformers_memory_efficient_attention()
        #     print("[CatVTON] xFormers enabled!")
        # except Exception as e:
        #     print(f"[CatVTON] xFormers not available: {e}")

        densepose_ckpt = os.path.join(settings.CATVTON_CKPT_PATH, "DensePose")
        schp_ckpt = os.path.join(settings.CATVTON_CKPT_PATH, "SCHP")

        self.automasker = AutoMasker(
            densepose_ckpt=densepose_ckpt,
            schp_ckpt=schp_ckpt,
            device=device,
        )

        self.mask_processor = VaeImageProcessor(
            vae_scale_factor=8,
            do_normalize=False,
            do_binarize=True,
            do_convert_grayscale=True,
        )

        self._device = device
        self._loaded = True

    @torch.inference_mode()
    def run(
        self,
        person_image: Image.Image,
        cloth_image: Image.Image,
        cloth_type: str = "upper",
        num_steps: int = 50,
        guidance: float = 2.5,
        seed: int = 42,
    ) -> Image.Image:
        size = (settings.IMAGE_WIDTH, settings.IMAGE_HEIGHT)

        person_image = person_image.convert("RGB").resize((768, 1024), Image.LANCZOS)
        cloth_image  = cloth_image.convert("RGB").resize((768, 1024), Image.LANCZOS)

        mask = self.automasker(person_image, cloth_type)["mask"]

        print(f"[DEBUG] person size: {person_image.size}")
        print(f"[DEBUG] mask type: {type(mask)}")
        print(f"[DEBUG] mask size: {mask.size if hasattr(mask, 'size') else mask.shape}")

        mask = self.mask_processor.blur(mask, blur_factor=9)

        print(f"[DEBUG] mask after blur type: {type(mask)}")
        print(f"[DEBUG] mask after blur shape: {mask.shape if hasattr(mask, 'shape') else mask.size}")
        generator = torch.Generator(device=self._device).manual_seed(seed)
        print(f"[DEBUG] Running on: {self._device}")
        print(f"[DEBUG] Pipeline device: {next(self.pipeline.unet.parameters()).device}")
        result = self.pipeline(
            image=person_image,
            condition_image=cloth_image,
            mask=mask,
            num_inference_steps=num_steps,
            guidance_scale=guidance,
            generator=generator,
            height=1024,    
            width=768,
        )[0]

        return result
