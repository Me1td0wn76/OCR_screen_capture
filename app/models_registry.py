"""Registry of downloadable OCR recognition models, keyed by language.

Models come from the RapidOCR model collection on Hugging Face. Each model
embeds its character dictionary in the ONNX metadata, so only the .onnx file
is needed. ``img_height`` is the recognizer input height the model expects
(v2/mobile CRNN models use 32, PP-OCRv3/v4 use 48).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

import requests

log = logging.getLogger(__name__)

_BASE = "https://huggingface.co/spaces/RapidAI/RapidOCR/resolve/main/models/text_rec"


@dataclass(frozen=True)
class ModelInfo:
    code: str          # internal key, e.g. "japan"
    label: str         # human label, e.g. "日本語 (Japanese)"
    filename: str      # onnx file name (also the file stored on disk)
    img_height: int    # recognizer input height
    source_url: str | None = None  # full download URL; None -> _BASE/filename

    @property
    def url(self) -> str:
        return self.source_url or f"{_BASE}/{self.filename}"


# Newer multilingual models that the RapidOCR HF Space doesn't carry live on
# ModelScope (the home of the current RapidOCR model zoo). These embed their
# character dictionary in the ONNX metadata, same as the HF ones.
_MODELSCOPE = (
    "https://www.modelscope.cn/models/RapidAI/RapidOCR/resolve/master/onnx"
)

# Default rec model per supported language.
MODELS: dict[str, ModelInfo] = {
    # PP-OCRv4 (input height 48) is markedly more accurate on mixed
    # kanji/kana/English/symbols than the old v2 CRNN model (height 32).
    "japan": ModelInfo(
        "japan", "日本語 (Japanese)", "japan_PP-OCRv4_rec_mobile.onnx", 48,
        f"{_MODELSCOPE}/PP-OCRv4/rec/japan_PP-OCRv4_rec_mobile.onnx",
    ),
    "en": ModelInfo("en", "英語 (English)", "en_PP-OCRv3_rec_infer.onnx", 48),
    "ch": ModelInfo("ch", "中国語 (Chinese)", "ch_PP-OCRv4_rec_infer.onnx", 48),
    "korean": ModelInfo("korean", "韓国語 (Korean)", "korean_mobile_v2.0_rec_infer.onnx", 32),
}

DEFAULT_LANGUAGE = "japan"


def get_model(language: str) -> ModelInfo:
    return MODELS.get(language, MODELS[DEFAULT_LANGUAGE])


def model_path(models_dir: Path, language: str) -> Path:
    return Path(models_dir) / get_model(language).filename


def is_downloaded(models_dir: Path, language: str) -> bool:
    p = model_path(models_dir, language)
    return p.exists() and p.stat().st_size > 0


ProgressFn = Callable[[int, int], None]  # (downloaded_bytes, total_bytes)


def download_model(
    models_dir: Path,
    language: str,
    progress: Optional[ProgressFn] = None,
    timeout: int = 60,
) -> Path:
    """Download the model for ``language`` into ``models_dir``.

    Streams to a temp file then renames, so a partial download never looks
    complete. Returns the final path. Raises on network/HTTP errors.
    """
    info = get_model(language)
    dest = Path(models_dir) / info.filename
    if dest.exists() and dest.stat().st_size > 0:
        return dest

    Path(models_dir).mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    log.info("downloading %s model from %s", language, info.url)

    with requests.get(info.url, stream=True, timeout=timeout) as r:
        r.raise_for_status()
        total = int(r.headers.get("Content-Length", 0))
        done = 0
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(chunk_size=64 * 1024):
                if not chunk:
                    continue
                f.write(chunk)
                done += len(chunk)
                if progress:
                    progress(done, total)
    tmp.replace(dest)
    log.info("saved %s (%d bytes)", dest, dest.stat().st_size)
    return dest
