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

# UI language code (cfg["language"]) -> rapidocr recognizer language. Our codes
# already match rapidocr's LangRec values.
_REC_LANG = {"japan": "japan", "en": "en", "ch": "ch", "korean": "korean"}
# The bundled default model is PP-OCRv6 (model_type "small"), whose multilingual
# model covers Japanese/English/Chinese (and many European langs) but NOT Korean.
# Languages listed here need a different version/model_type (downloaded on first
# use): value is (ocr_version, model_type).
_LANG_REC_OVERRIDE = {"korean": ("PP-OCRv5", "mobile")}


def _as_float(value: Any, default: float | None) -> float | None:
    """Coerce config values (which may arrive as JSON strings) to float."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


class OCREngine:
    """Thin wrapper around rapidocr.RapidOCR with a stable, simple interface."""

    def __init__(self, cfg: dict[str, Any]):
        self._cfg = cfg
        self._engine = None
        self._lock = threading.Lock()

    def _params(self) -> dict[str, Any]:
        """Map our config onto rapidocr's dotted parameter keys.

        Language is driven by the top-level ``cfg["language"]`` set by the
        setup/settings UI (japan/en/ch/korean), mapped to rapidocr's
        ``Rec.lang_type``. Korean isn't in the bundled PP-OCRv6 model, so it
        switches the recognizer to PP-OCRv5 (downloaded on first use).
        """
        ocr_cfg = self._cfg.get("ocr", {}) or {}
        params: dict[str, Any] = {
            "Global.text_score": _as_float(ocr_cfg.get("text_score"), 0.5),
            "Global.log_level": "warning",
        }
        # Detection knobs (optional). Coerce to float in case they arrive as
        # strings from JSON config.
        det = ocr_cfg.get("det", {}) or {}
        det_map = {
            "unclip_ratio": "Det.unclip_ratio",
            "box_thresh": "Det.box_thresh",
            "thresh": "Det.thresh",
        }
        for key, pkey in det_map.items():
            val = _as_float(det.get(key), None)
            if val is not None:
                params[pkey] = val

        # Recognizer language from the UI's top-level "language" setting.
        lang = str(self._cfg.get("language", "japan")).strip().lower()
        rec_lang = _REC_LANG.get(lang)
        if rec_lang:
            params["Rec.lang_type"] = rec_lang
            override = _LANG_REC_OVERRIDE.get(lang)
            if override:
                # ocr_version / model_type must be passed as enums, not strings.
                from rapidocr.utils.typings import ModelType, OCRVersion

                version, model_type = override
                params["Rec.ocr_version"] = OCRVersion(version)
                params["Rec.model_type"] = ModelType(model_type)
        return params

    def _build(self):
        from rapidocr import RapidOCR  # heavy import; defer it

        params = self._params()
        try:
            engine = RapidOCR(params=params)
        except Exception as e:
            # An unsupported language/version combo (or a failed first-time
            # model download) shouldn't break OCR; fall back to the bundled
            # multilingual default model.
            log.warning(
                "OCR engine build failed for %s (%s); falling back to the "
                "bundled default model.", params, e
            )
            engine = RapidOCR(params={
                "Global.text_score": _as_float(
                    self._cfg.get("ocr", {}).get("text_score"), 0.5),
                "Global.log_level": "warning",
            })
        log.info("OCR engine ready (rapidocr, language=%s)", self._cfg.get("language"))
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
