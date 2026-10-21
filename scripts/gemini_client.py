"""
Gemini Vision & Translation Client Module
Provides multimodal image analysis, text detection, and translation via Google Gemini API.
"""

import os
import json
import base64
import urllib.request
import urllib.error
from typing import Dict, Any, Optional, List

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def get_gemini_api_key() -> str:
    """Retrieves GEMINI_API_KEY from environment or .env file."""
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if api_key:
        return api_key

    env_path = os.path.join(WORKSPACE_ROOT, ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if line.startswith("GEMINI_API_KEY="):
                    return line.split("=", 1)[1].strip().strip("'\"")
    return ""

class GeminiVisionClient:
    """High-reliability client for Google Gemini Vision models with automatic failover."""

    MODELS = [
        "gemini-3.5-flash-lite",
        "gemini-3.5-flash",
        "gemini-3.8-flash",
        "gemini-3.1-flash-lite",
    ]

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or get_gemini_api_key()

    def analyze_image(self, image_path: str, prompt: str) -> Optional[str]:
        """Analyzes a local image file using Gemini Vision models with automatic fallback."""
        if not self.api_key:
            return None

        if not os.path.exists(image_path):
            return None

        with open(image_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode("utf-8")

        ext = os.path.splitext(image_path)[1].lower()
        mime_type = "image/png" if ext == ".png" else "image/jpeg"

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": img_b64
                            }
                        }
                    ]
                }
            ]
        }
        body = json.dumps(payload).encode("utf-8")

        for model in self.MODELS:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
            req = urllib.request.Request(
                url,
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            try:
                with urllib.request.urlopen(req, timeout=15) as resp:
                    res = json.loads(resp.read().decode("utf-8"))
                    candidates = res.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            return parts[0].get("text", "").strip()
            except Exception:
                continue

        return None
