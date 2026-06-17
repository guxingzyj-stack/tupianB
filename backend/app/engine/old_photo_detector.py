"""老照片自动判别 (PRD §7.2 / 任务 4.1)。

多信号融合, 任意 2 条命中即判为老照片:
  1. 平均饱和度低 (褪色/偏黄)
  2. 锐度低 (拉普拉斯方差小)
  3. 黄褐色调 (HSV 平均色相在黄褐范围)
  4. 明显折痕/划痕 (Canny + Hough 直线)
  5. 胶片噪点 (非数字噪点的纹理特征)
  6. Claude 的 scene 含 "老照片/旧照/翻拍/黑白" 等关键词

阈值是启发式的, 需用真实老照片继续调。
"""

from __future__ import annotations

from pathlib import Path

# cv2 (OpenCV) 常驻内存约 80MB; 不在模块顶层导入, 改为函数内懒加载,
# 让启动 / 健康检查 / 非老照片路径保持低内存 (部署节点内存吃紧, 避免 OOM 驱逐)。

_OLD_KEYWORDS = ["老照片", "旧照", "翻拍", "黑白", "泛黄", "年代久", "老相片", "怀旧", "复古"]


def _load_bgr(path: str | Path) -> "np.ndarray | None":
    """用 imdecode 读图, 避开 cv2.imread 在 Windows 非 ASCII 路径返回 None 的坑。"""
    import cv2
    import numpy as np

    try:
        data = np.fromfile(str(path), dtype=np.uint8)
        if data.size == 0:
            return None
        return cv2.imdecode(data, cv2.IMREAD_COLOR)
    except Exception:
        return None


def analyze_oldness(image_path: str | Path, claude_scene: str = "") -> dict:
    """返回 {is_old, signals, mean_sat, is_bw, metrics}。"""
    import cv2
    import numpy as np

    img = _load_bgr(image_path)
    if img is None:
        return {"is_old": False, "signals": [], "mean_sat": 0.0, "is_bw": False, "metrics": {}}

    # 缩放提速
    h, w = img.shape[:2]
    scale = 1024.0 / max(h, w)
    if scale < 1.0:
        img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    s_chan = hsv[..., 1]
    h_chan = hsv[..., 0]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    signals: list[str] = []
    mean_sat = float(s_chan.mean()) / 255.0

    # 1. 低饱和 (褪色)
    if mean_sat < 0.25:
        signals.append("低饱和")

    # 2. 锐度低 (拉普拉斯方差)
    lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    if lap_var < 120.0:
        signals.append("锐度低")

    # 3. 黄褐(泛黄)色调: 色相在黄褐(12-38)且整体已褪色(低饱和)。
    #    要求低饱和, 避免把"暖色但鲜艳"的现代照片(美食/霓虹夜景)误判。
    colored = s_chan > 30
    mean_hue = float(h_chan[colored].mean()) if colored.sum() > 0 else -1.0
    if 12 <= mean_hue <= 38 and mean_sat < 0.25:
        signals.append("黄褐色调")

    # 4. 胶片噪点: 与中值滤波之差适中, 且整体不锐 → 偏胶片噪点
    med = cv2.medianBlur(gray, 3)
    noise = float(np.abs(gray.astype(np.int16) - med.astype(np.int16)).mean())
    if 4.0 < noise < 13.0 and lap_var < 250.0:
        signals.append("胶片噪点")

    # 5. Claude 关键词
    if any(k in (claude_scene or "") for k in _OLD_KEYWORDS):
        signals.append("AI判断旧照")

    # 注: 原本用 Canny+Hough 检测折痕/划痕, 但实测对任何有纹理的现代照片都误触
    #     (建筑/草木几十上百条线), 信噪比太差, v0.1 先去掉。真要做需"平滑背景上
    #     的少数长直线"这种更严格的判据。

    is_bw = mean_sat < 0.08  # 极低饱和 ≈ 黑白
    is_old = len(signals) >= 2

    return {
        "is_old": is_old,
        "signals": signals,
        "mean_sat": round(mean_sat, 3),
        "is_bw": is_bw,
        "metrics": {
            "lap_var": round(lap_var, 1),
            "mean_hue": round(mean_hue, 1),
            "noise": round(noise, 2),
        },
    }


def is_old_photo(image_path: str | Path, claude_scene: str = "") -> tuple[bool, list[str]]:
    """便捷接口: 返回 (是否老照片, 命中信号)。"""
    r = analyze_oldness(image_path, claude_scene)
    return r["is_old"], r["signals"]


# 老照片选项 -> 给图像编辑模型的修复指令 (任务 4.2)
# 修复 prompt 平衡: 在"清晰度/细节"上**大力提升**(明显的质感飞跃), 同时严格锁住身份/构图/
# 物体本色不变 —— 实测把"清晰锐利、细节丰富"写足 + "保持构图背景本色不变"约束, 既惊艳又不失真。
_RESTORE_PROMPTS = {
    "修旧如新": "高质量修复这张老照片：大幅提升清晰度，让五官、皱纹、发丝、衣物纹理都"
    "清晰锐利、细节丰富，彻底去除模糊、噪点、划痕和褪色，画面通透干净、明暗层次分明。"
    "保持原有色调与人物身份、表情、姿势、构图不变，自然真实不夸张，不臆造内容。",
    "变成彩色": "为这张黑白老照片自然真实地上色，并大幅提升清晰度：五官、发丝、皮肤、"
    "衣物纹理清晰锐利、细节丰富，彻底去除模糊、噪点、划痕，画面通透干净；肤色与环境色"
    "自然真实、柔和不夸张。严格保持人物身份、表情、姿势、画面构图与背景不变，不臆造或替换内容。",
    "颜色还原": "还原并增强这张老照片的真实色彩、去除偏黄；大幅提升清晰度，五官、衣物与"
    "细节清晰锐利，彻底去除模糊、噪点、划痕，画面通透。色彩自然不夸张。严格保持人物身份、"
    "画面构图与各物体本来的颜色不变，不臆造内容。",
    "脸更清楚": "重点修复并增强人物面部、整体提升清晰度：五官清晰锐利、肤质细腻真实、"
    "眼睛明亮有神、神态自然；整体彻底去除模糊、噪点、划痕，大幅提升清晰度与质感。"
    "严格保持人物身份与五官特征不变，自然不失真，不臆造内容。",
}


def restore_prompt_for(option_name: str) -> str:
    """按选项名选修复提示词。

    claude 的选项命名并不固定 (如"变彩色"/"上色"/"还原色彩"/"脸更清楚"…), 精确匹配不到时
    必须按关键词兜底, 否则"上色"类选项会错用成"修旧如新"导致**只修复不上色 (出黑白)**。
    """
    name = option_name or ""
    if name in _RESTORE_PROMPTS:
        return _RESTORE_PROMPTS[name]
    if any(k in name for k in ("彩色", "上色", "变彩", "着色")):
        return _RESTORE_PROMPTS["变成彩色"]
    if any(k in name for k in ("还原", "颜色", "色彩")):
        return _RESTORE_PROMPTS["颜色还原"]
    if any(k in name for k in ("脸", "面", "人物")):
        return _RESTORE_PROMPTS["脸更清楚"]
    return _RESTORE_PROMPTS["修旧如新"]


# 修复类关键词 (名称/意图命中即走生成式 gpt-image-2)。不含"清/亮"等普通增强词, 防误判普通照片。
_RESTORE_HINTS = ("旧", "老", "彩色", "上色", "褪色", "还原", "划痕", "泛黄", "修复", "黑白", "翻新")


def is_restore_option(name: str, intent: str = "") -> bool:
    """该选项是否属于"老照片修复/上色"类 → 应走生成式编辑 (gpt-image-2)。

    判据: 名称命中预设修复选项, 或名称/意图含修复类关键词。把生成式修复与不稳定的
    cv2 老照片判别解耦: 只要用户选的是修复/上色类选项就修, 不依赖 is_old 标志。
    """
    if name in _RESTORE_PROMPTS:
        return True
    text = f"{name or ''} {intent or ''}"
    return any(k in text for k in _RESTORE_HINTS)


def old_photo_options(is_bw: bool) -> list[dict]:
    """老照片预设三选项 (PRD §7.3)。彩色老照片把"变成彩色"换成"颜色还原"。"""
    second = (
        {"name": "变成彩色", "intent": "去模糊 + 去划痕 + 黑白上色"}
        if is_bw
        else {"name": "颜色还原", "intent": "去模糊 + 去划痕 + 褪色颜色还原"}
    )
    return [
        {"name": "修旧如新", "intent": "去模糊 + 去划痕 + 褪色还原,保持原色调"},
        second,
        {"name": "脸更清楚", "intent": "GFPGAN 人脸专修 + 整体增强"},
    ]
