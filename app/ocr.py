"""OCR engine wrapper around the `rapidocr` package (PP-OCRv6, ONNX, CPU).

`rapidocr` ships a multilingual PP-OCRv6 model set bundled inside the package
(det + rec + cls, ~30 MB), so there is no model download step: Japanese,
English and Chinese are recognized out of the box with far higher accuracy
than the old single-language CRNN models. The engine is lazily built so the
tray starts fast.
"""
from __future__ import annotations

import logging
import threading
from typing import Any

import numpy as np
from PIL import Image

log = logging.getLogger(__name__)


class OCREngine:
    """Thin wrapper around rapidocr.RapidOCR with a stable, simple interface."""

    def __init__(self, cfg: dict[str, Any]):
        self._cfg = cfg
        self._engine = None
        self._lock = threading.Lock()

    def _params(self) -> dict[str, Any]:
        """Map our config onto rapidocr's dotted parameter keys."""
        ocr_cfg = self._cfg.get("ocr", {}) or {}
        params: dict[str, Any] = {
            "Global.text_score": float(ocr_cfg.get("text_score", 0.5)),
            "Global.log_level": "warning",
        }
        # Detection knobs (optional). rapidocr applies these directly.
        det = ocr_cfg.get("det", {}) or {}
        det_map = {
            "unclip_ratio": "Det.unclip_ratio",
            "box_thresh": "Det.box_thresh",
            "thresh": "Det.thresh",
        }
        for key, pkey in det_map.items():
            if det.get(key) is not None:
                params[pkey] = det[key]
        # Optional: pin a recognizer language/version for advanced users. The
        # default (unset) uses the bundled multilingual PP-OCRv6 model, which
        # already handles Japanese/English/Chinese well.
        lang_type = ocr_cfg.get("lang_type")
        if lang_type:
            params["Rec.lang_type"] = lang_type
        ocr_version = ocr_cfg.get("ocr_version")
        if ocr_version:
            params["Rec.ocr_version"] = ocr_version
            params["Det.ocr_version"] = ocr_version
        return params

    def _build(self):
        from rapidocr import RapidOCR  # heavy import; defer it

        engine = RapidOCR(params=self._params())
        log.info("OCR engine ready (rapidocr / PP-OCRv6 bundled models)")
        return engine

    def _ensure(self):
        if self._engine is None:
            with self._lock:
                if self._engine is None:
                    self._engine = self._build()
        return self._engine

    def reload(self) -> None:
        """Drop the engine so the next call rebuilds it (e.g. after a settings change)."""
        with self._lock:
            self._engine = None

    def _preprocess(self, image: Image.Image | np.ndarray) -> np.ndarray:
        """Upscale small captures so text is large enough for the recognizer.

        Screen text is frequently 12-16px tall; the recognizer normalizes each
        line crop to ~48px, so small text gets blurrily stretched. Enlarging the
        whole image first gives those crops real pixels to work with. Cheap (a
        single LANCZOS resize) and only kicks in when the image is actually small.
        """
        img = image if isinstance(image, Image.Image) else Image.fromarray(image)
        pp = self._cfg.get("ocr", {}).get("preprocess", {}) or {}
        if pp.get("enabled", True):
            min_side = int(pp.get("min_side", 300))
            max_scale = float(pp.get("max_scale", 3.0))
            max_pixels = int(pp.get("max_pixels", 12_000_000))
            w, h = img.size
            short = min(w, h)
            if short > 0 and short < min_side:
                scale = min(max_scale, min_side / short)
                if scale > 1.05 and (w * h) * (scale ** 2) <= max_pixels:
                    img = img.resize((round(w * scale), round(h * scale)), Image.LANCZOS)
        return np.array(img)

    def recognize(self, image: Image.Image | np.ndarray) -> str:
        """Run OCR and return recognized text joined line by line."""
        engine = self._ensure()
        arr = self._preprocess(image)
        result = engine(arr)
        if result is None or not getattr(result, "txts", None):
            return ""
        lines = [str(t).strip() for t in result.txts]
        return "\n".join(line for line in lines if line)

    def warm_up(self) -> None:
        """Build the engine ahead of first use (called from a background thread)."""
        try:
            self._ensure()
        except Exception:  # pragma: no cover - best effort warm-up
            log.exception("OCR warm-up failed")
