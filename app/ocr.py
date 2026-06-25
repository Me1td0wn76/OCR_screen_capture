"""RapidOCR wrapper (CPU, ONNX). Lazily initialized so the tray starts fast."""
from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from . import models_registry as registry
from .config import resolve_model_dir
from .paths import bundled_models_dir

log = logging.getLogger(__name__)


class OCREngine:
    """Thin wrapper around RapidOCR with a language-selectable rec model.

    RapidOCR ships a Chinese+English model. We point the recognizer at the
    model for the language selected in config (downloaded into the model dir),
    falling back to a copy bundled with the build, then to RapidOCR's default.
    Detection + angle classification always use the bundled models.
    """

    def __init__(self, cfg: dict[str, Any]):
        self._cfg = cfg
        self._engine = None
        self._lock = threading.Lock()

    def _resolve_rec_model(self) -> tuple[Path, int] | None:
        """Return (model_path, img_height) for the configured language, or None."""
        language = self._cfg.get("language", registry.DEFAULT_LANGUAGE)
        info = registry.get_model(language)
        for base in (resolve_model_dir(self._cfg), bundled_models_dir()):
            candidate = Path(base) / info.filename
            if candidate.exists() and candidate.stat().st_size > 0:
                return candidate, info.img_height
        return None

    def _det_kwargs(self) -> dict[str, Any]:
        """Detection overrides from config, or {} to keep RapidOCR's defaults.

        RapidOCR only applies det_* kwargs when a det model path is also given,
        so we point it at the bundled detection model when any knob is set.
        """
        det = self._cfg.get("ocr", {}).get("det", {}) or {}
        mapping = {
            "unclip_ratio": "det_unclip_ratio",
            "box_thresh": "det_box_thresh",
            "thresh": "det_thresh",
        }
        overrides = {arg: det[key] for key, arg in mapping.items() if det.get(key) is not None}
        if not overrides:
            return {}
        import rapidocr_onnxruntime as _r  # det model ships inside this package

        det_model = Path(_r.__file__).parent / "models" / "ch_PP-OCRv3_det_infer.onnx"
        overrides["det_model_path"] = str(det_model)
        return overrides

    def _build(self):
        from rapidocr_onnxruntime import RapidOCR  # heavy import; defer it

        kwargs: dict[str, Any] = {}
        resolved = self._resolve_rec_model()
        if resolved:
            rec_path, height = resolved
            kwargs["rec_model_path"] = str(rec_path)
            kwargs["rec_img_shape"] = [3, height, 320]
            log.info("Using rec model: %s (h=%d)", rec_path, height)
        else:
            log.warning(
                "No language rec model found; falling back to bundled "
                "Chinese+English model (weak on Japanese kana)."
            )
        kwargs.update(self._det_kwargs())
        return RapidOCR(**kwargs)

    def _ensure(self):
        if self._engine is None:
            with self._lock:
                if self._engine is None:
                    self._engine = self._build()
        return self._engine

    def reload(self) -> None:
        """Drop the engine so the next call rebuilds it (e.g. after a language change)."""
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
        text_score = float(self._cfg.get("ocr", {}).get("text_score", 0.5))
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
