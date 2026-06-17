"""模板合成 (任务 5.4): 在视频上叠加字幕 (+ 可选背景音乐), 用 ffmpeg。

字幕: 白字 + 黑描边, 底部居中 (PRD §9.3)。CJK 用系统简黑。
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

# Windows 简黑; 其他平台可换 Noto Sans CJK
_DEFAULT_FONT = r"C:\Windows\Fonts\simhei.ttf"


def _esc_font(p: str) -> str:
    # ffmpeg drawtext 的 fontfile 需要正斜杠 + 转义冒号: C\:/Windows/...
    return str(p).replace("\\", "/").replace(":", "\\:")


def _esc_text(t: str) -> str:
    return (
        t.replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "’")  # 单引号换成印刷体, 避开滤镜引号地狱
        .replace("%", "\\%")
    )


def has_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None


def compose(
    video_in: str | Path,
    text: str,
    out_path: str | Path,
    music_path: str | Path | None = None,
    font_path: str = _DEFAULT_FONT,
) -> Path:
    """给视频叠字幕 (+音乐), 输出新 mp4。失败抛 CalledProcessError。"""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = ["ffmpeg", "-y", "-i", str(video_in)]
    if music_path:
        cmd += ["-i", str(music_path)]

    if text.strip():
        vf = (
            f"drawtext=fontfile='{_esc_font(font_path)}':text='{_esc_text(text)}':"
            f"fontcolor=white:fontsize=h/16:borderw=4:bordercolor=black@0.9:"
            f"x=(w-text_w)/2:y=h-(h/7)"
        )
        cmd += ["-vf", vf]

    cmd += ["-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p"]
    if music_path:
        cmd += ["-map", "0:v:0", "-map", "1:a:0", "-shortest", "-c:a", "aac"]
    cmd += [str(out_path)]

    subprocess.run(cmd, check=True, capture_output=True)
    return out_path
