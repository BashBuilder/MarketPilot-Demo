"""Benchmark compatibility import for the shared Hugging Face image adapter."""

from app.tools.image_providers.huggingface import (
    HF_INFERENCE_URL,
    PROVIDER_NAME,
    HuggingFaceImageGenerator,
)

HuggingFaceInferenceGenerator = HuggingFaceImageGenerator

__all__ = [
    "HF_INFERENCE_URL",
    "PROVIDER_NAME",
    "HuggingFaceImageGenerator",
    "HuggingFaceInferenceGenerator",
]
