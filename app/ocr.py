"""RapidOCR wrapper (CPU, ONNX). Lazily initialized so the tray starts fast."""
from __future__ import annotations

import logging
import threading
from typing import Any

import numpy as np
from PIL import Image

from .paths import models_dir

log = logging.getLogger(__name__)


class OCREngine:
    """Thin wrapper around RapidOCR with a swappable Japanese rec model.

    RapidOCR ships a Chinese+English model. For Japanese we point the
    recognizer at a Japanese CRNN model (height 32) dropped into models/.
    Detection + angle classification keep the bundled models.
    """

    def __init__(self, cfg: dict[str, Any]):
        self._cfg = cfg.get("ocr", {})
        self._engine = None
        self._lock = threading.Lock()

    def _build(self):
        from rapidocr_onnxruntime import RapidOCR  # heavy import; defer it

        kwargs: dict[str, Any] = {}
        rec_file = self._cfg.get("rec_model_file")
        if rec_file:
            rec_path = models_dir() / rec_file
            if rec_path.exists():
                kwargs["rec_model_path"] = str(rec_path)
                height = int(self._cfg.get("rec_img_height", 32))
                kwargs["rec_img_shape"] = [3, height, 320]
                log.info("Using Japanese rec model: %s (h=%d)", rec_path, height)
            else:
                log.warning(
                    "Rec model %s not found; falling back to bundled model "
                    "(weak on Japanese kana).", rec_path,
                )
        return RapidOCR(**kwargs)

    def _ensure(self):
        if self._engine is None:
            with self._lock:
                if self._engine is None:
                    self._engine = self._build()
        return self._engine

    def recognize(self, image: Image.Image | np.ndarray) -> str:
        """Run OCR and return recognized text joined line by line."""
        engine = self._ensure()
        arr = np.array(image) if isinstance(image, Image.Image) else image
        text_score = float(self._cfg.get("text_score", 0.5))
        result, _ = engine(arr, text_score=text_score)
        if not result:
            return ""
        lines = [str(text).strip() for _box, text, _score in result]
        return "\n".join(line for line in lines if line)

    def warm_up(self) -> None:
        """Build the engine ahead of first use (called from a background thread)."""
        try:
            self._ensure()
        except Exception:  # pragma: no cover - best effort warm-up
            log.exception("OCR warm-up failed")
