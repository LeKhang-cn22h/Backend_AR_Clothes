from typing import Optional

from pydantic import BaseModel


class FitAssessmentRequest(BaseModel):
    body_profile_id: int
    garment_id: int
    size_label: Optional[str] = None


class RegionFit(BaseModel):
    diff_cm: Optional[float] = None
    status: str


class FitAssessmentResult(BaseModel):
    overall_fit: str
    chest_fit: RegionFit
    waist_fit: RegionFit
    hip_fit: RegionFit
    recommendation: str
    size_suggestion: Optional[str] = None
    body_measurements: Optional[dict] = None
    garment_size: Optional[dict] = None
    selected_size: Optional[str] = None


class FaceReconstructResponse(BaseModel):
    face_glb_url: str
    face_params: dict


class MergeFaceRequest(BaseModel):
    face_glb_url: str


class MergeFaceResponse(BaseModel):
    merged_glb_url: str
    status: str


class LandmarksResponse(BaseModel):
    landmarks: dict
    measurements: dict
