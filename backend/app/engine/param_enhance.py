"""参数化修图引擎 (PRD §6.1/§6.2)。

只用 Pillow + NumPy, 不调用任何 AI 模型, 不依赖 OpenCV。
保真、快、便宜、不会"生成"不存在的内容。

核心约束: 绝不覆盖原图 —— 每次都写到调用方给的新 output_path。
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

from app.engine.intent_mapper import Operation

_LUMA = np.array([0.299, 0.587, 0.114], dtype=np.float32)


# --------------------------------------------------------------------------- #
# 图片 <-> float 数组
# --------------------------------------------------------------------------- #
def _load_rgb(path: str | Path) -> np.ndarray:
    img = Image.open(path)
    img = ImageOps.exif_transpose(img)  # 尊重拍摄方向
    img = img.convert("RGB")
    return np.asarray(img, dtype=np.float32) / 255.0


def _to_pil(arr: np.ndarray) -> Image.Image:
    a = np.clip(arr, 0.0, 1.0)
    return Image.fromarray((a * 255.0 + 0.5).astype(np.uint8), "RGB")


def _luma_of(arr: np.ndarray) -> np.ndarray:
    return arr @ _LUMA  # HxW


# --------------------------------------------------------------------------- #
# 像素级操作 (NumPy)
# --------------------------------------------------------------------------- #
def _op_brightness(arr: np.ndarray, v: float) -> np.ndarray:
    # 提亮暗部、保护高光: out = in + v*(1-in), 高光处 (1-in)→0 几乎不动
    return np.clip(arr + v * (1.0 - arr), 0.0, 1.0)


def _op_saturation(arr: np.ndarray, v: float) -> np.ndarray:
    lu = _luma_of(arr)[..., None]
    return np.clip(lu + (arr - lu) * (1.0 + v), 0.0, 1.0)


def _op_vibrance(arr: np.ndarray, v: float) -> np.ndarray:
    # 对已经很鲜艳的像素少加, 对灰暗像素多加
    lu = _luma_of(arr)[..., None]
    sat = np.abs(arr - lu).max(axis=2, keepdims=True)
    factor = 1.0 + v * (1.0 - sat)
    return np.clip(lu + (arr - lu) * factor, 0.0, 1.0)


def _op_contrast(arr: np.ndarray, v: float) -> np.ndarray:
    return np.clip((arr - 0.5) * (1.0 + v) + 0.5, 0.0, 1.0)


def _op_warmth(arr: np.ndarray, v: float) -> np.ndarray:
    out = arr.copy()
    out[..., 0] = arr[..., 0] * (1.0 + 0.5 * v)  # R 上
    out[..., 2] = arr[..., 2] * (1.0 - 0.5 * v)  # B 下
    return np.clip(out, 0.0, 1.0)


def _op_sky_blue(arr: np.ndarray, v: float) -> np.ndarray:
    R, G, B = arr[..., 0], arr[..., 1], arr[..., 2]
    luma = _luma_of(arr)
    blue_dom = np.clip(B - np.maximum(R, G), 0.0, 1.0)  # 蓝主导
    bright = np.clip((luma - 0.35) / 0.65, 0.0, 1.0)  # 偏亮 (天空通常亮)
    mask = np.clip(blue_dom * 4.0, 0.0, 1.0) * bright  # HxW
    m = mask[..., None]
    lu = luma[..., None]
    saturated = lu + (arr - lu) * (1.0 + v)  # 局部加饱和
    out = arr * (1.0 - m) + saturated * m
    out[..., 2] = out[..., 2] + v * 0.10 * mask * (1.0 - out[..., 2])  # 蓝再深一点
    return np.clip(out, 0.0, 1.0)


def _op_subject_boost(arr: np.ndarray, v: float) -> np.ndarray:
    # 简化版"主体增强": 暗部 (常是逆光主体) 局部提亮
    luma = _luma_of(arr)
    shadow = np.clip((0.55 - luma) / 0.55, 0.0, 1.0)  # 黑处=1, 中灰以上=0
    m = shadow[..., None]
    return np.clip(arr + v * m * (1.0 - arr), 0.0, 1.0)


_NUMPY_OPS = {
    "brightness": _op_brightness,
    "saturation": _op_saturation,
    "vibrance": _op_vibrance,
    "contrast": _op_contrast,
    "warmth": _op_warmth,
    "sky_blue": _op_sky_blue,
    "subject_boost": _op_subject_boost,
}


# --------------------------------------------------------------------------- #
# 滤镜级操作 (PIL)
# --------------------------------------------------------------------------- #
def _apply_filter_op(img: Image.Image, op: Operation) -> Image.Image:
    if op.type == "clarity":
        percent = int(max(0.0, op.value) * 120)
        return img.filter(ImageFilter.UnsharpMask(radius=3, percent=percent, threshold=2))
    if op.type == "soft":
        v = op.value
        img = ImageEnhance.Contrast(img).enhance(1.0 - 0.30 * v)  # 降对比
        blurred = img.filter(ImageFilter.GaussianBlur(radius=2.0))
        img = Image.blend(img, blurred, min(0.30, 0.25 * v + 0.08))  # 轻磨皮
        return img
    return img


_FILTER_OP_TYPES = {"clarity", "soft"}


# --------------------------------------------------------------------------- #
# 对外接口
# --------------------------------------------------------------------------- #
def apply_operations(
    input_path: str | Path,
    operations: Iterable[Operation],
    output_path: str | Path,
) -> Path:
    """按操作序列修图, 写到 output_path (新文件)。返回 output_path。"""
    operations = list(operations)
    arr = _load_rgb(input_path)

    filter_ops: list[Operation] = []
    for op in operations:
        fn = _NUMPY_OPS.get(op.type)
        if fn is not None:
            arr = fn(arr, op.value)
        elif op.type in _FILTER_OP_TYPES:
            filter_ops.append(op)
        # 未知操作类型: 忽略 (前向兼容)

    img = _to_pil(arr)
    for op in filter_ops:
        img = _apply_filter_op(img, op)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, "JPEG", quality=92)
    return output_path


def make_base_repair(input_path: str | Path, output_path: str | Path) -> Path:
    """一进结果页就显示的"基础修复版": 轻度提亮 + 对比 + 饱和 (PRD §3.3/§6.4)。"""
    arr = _load_rgb(input_path)
    arr = _op_brightness(arr, 0.10)
    arr = _op_contrast(arr, 0.06)
    arr = _op_saturation(arr, 0.12)
    img = _to_pil(arr)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, "JPEG", quality=92)
    return output_path


def image_stats(path: str | Path) -> dict:
    """平均亮度 / 平均饱和度, 供测试与调试用。"""
    arr = _load_rgb(path)
    luma = _luma_of(arr)
    lu = luma[..., None]
    sat = float(np.abs(arr - lu).mean())
    return {"mean_luma": float(luma.mean()), "mean_sat": sat}
