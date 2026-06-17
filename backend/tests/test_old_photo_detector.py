"""老照片判别测试 (任务 4.1)。用合成图验证信号逻辑。"""

import numpy as np
from PIL import Image, ImageFilter

from app.engine.old_photo_detector import (
    analyze_oldness,
    is_old_photo,
    old_photo_options,
)


def _save_modern(path):
    # 随机彩色 + 高频 -> 高饱和、锐利 -> 不该判老照片
    arr = np.random.default_rng(2).integers(0, 256, (600, 800, 3), dtype=np.uint8)
    Image.fromarray(arr, "RGB").save(path, "JPEG", quality=95)


def _save_old(path):
    # 低饱和棕褐渐变 + 高斯模糊 -> 低饱和 + 黄褐色调 + 锐度低
    xs = np.linspace(70, 195, 800)
    g = np.tile(xs, (600, 1))
    arr = np.stack([g, g * 0.90, g * 0.78], axis=-1)  # 通道接近 -> 低饱和
    arr = np.clip(arr, 0, 255).astype("uint8")
    img = Image.fromarray(arr, "RGB").filter(ImageFilter.GaussianBlur(4))
    img.save(path, "JPEG", quality=80)


def test_modern_not_old(tmp_path):
    p = tmp_path / "modern.jpg"
    _save_modern(p)
    is_old, signals = is_old_photo(p)
    assert is_old is False, f"现代照片被误判, 命中: {signals}"


def test_synthetic_old_detected(tmp_path):
    p = tmp_path / "old.jpg"
    _save_old(p)
    r = analyze_oldness(p)
    assert r["is_old"] is True, f"老照片没判出来, metrics={r}"
    assert len(r["signals"]) >= 2


def test_claude_keyword_is_a_signal(tmp_path):
    p = tmp_path / "modern2.jpg"
    _save_modern(p)
    # 现代图 + Claude 说是黑白老照片: 关键词应成为一个信号
    r = analyze_oldness(p, claude_scene="一张黑白老照片翻拍")
    assert "AI判断旧照" in r["signals"]


def test_old_photo_options_bw_vs_color():
    bw = old_photo_options(is_bw=True)
    assert [o["name"] for o in bw] == ["修旧如新", "变成彩色", "脸更清楚"]
    color = old_photo_options(is_bw=False)
    assert color[1]["name"] == "颜色还原"
