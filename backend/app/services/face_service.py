from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Sequence

import cv2
import face_recognition
import numpy as np
from PIL import Image


@dataclass
class FaceMatch:
    bbox: tuple[int, int, int, int]
    embedding: list[float]
    person_name: str | None
    confidence: float


class FaceService:
    @staticmethod
    def _load_rgb(image_bytes: bytes) -> np.ndarray:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        return np.array(image)

    def detect_and_encode(self, image_bytes: bytes) -> tuple[list[tuple[int, int, int, int]], list[list[float]]]:
        rgb = self._load_rgb(image_bytes)
        locations = face_recognition.face_locations(rgb, model="hog")
        encodings = face_recognition.face_encodings(rgb, locations)
        return locations, [encoding.tolist() for encoding in encodings]

    @staticmethod
    def _to_float_vector(value: Sequence[float] | str) -> list[float]:
        if isinstance(value, str):
            cleaned = value.strip()
            if cleaned.startswith("[") and cleaned.endswith("]"):
                cleaned = cleaned[1:-1]
            if not cleaned:
                return []
            return [float(part.strip()) for part in cleaned.split(",") if part.strip()]
        return [float(x) for x in value]

    @classmethod
    def cosine_similarity(cls, a: Sequence[float] | str, b: Sequence[float] | str) -> float:
        va = np.array(cls._to_float_vector(a), dtype=np.float32)
        vb = np.array(cls._to_float_vector(b), dtype=np.float32)
        if va.size == 0 or vb.size == 0 or va.size != vb.size:
            return 0.0
        denom = float(np.linalg.norm(va) * np.linalg.norm(vb))
        if denom == 0.0:
            return 0.0
        return float(np.dot(va, vb) / denom)

    def annotate_image(self, image_bytes: bytes, matches: list[FaceMatch]) -> bytes:
        np_img = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(np_img, cv2.IMREAD_COLOR)
        if img is None:
            return image_bytes

        for match in matches:
            top, right, bottom, left = match.bbox
            name = match.person_name or "unknown"
            label = f"{name} ({match.confidence:.2f})"

            cv2.rectangle(img, (left, top), (right, bottom), (60, 180, 75), 2)
            cv2.rectangle(img, (left, max(0, top - 24)), (right, top), (60, 180, 75), -1)
            cv2.putText(img, label, (left + 4, max(12, top - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)

        success, encoded = cv2.imencode(".jpg", img)
        if not success:
            return image_bytes
        return encoded.tobytes()


face_service = FaceService()
