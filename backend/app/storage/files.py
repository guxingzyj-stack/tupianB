"""文件存取 (Zeabur Volume / 本地 data 目录)。

布局 (架构 §3.5):
  {FILE_BASE}/inputs/{device_id}/{job_id}.jpg      原图
  {FILE_BASE}/outputs/{device_id}/{job_id}/        该任务输出
        ├── base.jpg        基础修复版
        ├── option_1.jpg    三选项
        ├── option_2.jpg
        └── option_3.jpg
  {FILE_BASE}/videos/{device_id}/{job_id}.mp4       视频

对外 URL: {PUBLIC_BASE_URL}/files/<相对 FILE_BASE 的路径>
"""

import base64
import binascii
import re
from pathlib import Path

from app.config import settings

# device_id / job_id 来自客户端, 用作路径, 必须清洗防目录穿越。
_SAFE_RE = re.compile(r"[^A-Za-z0-9_\-]")


def sanitize_id(raw: str) -> str:
    """只保留字母数字下划线连字符; 限长。空串兜底为 'unknown'。"""
    cleaned = _SAFE_RE.sub("", (raw or "").strip())[:64]
    return cleaned or "unknown"


def base_dir() -> Path:
    return Path(settings.file_base)


def ensure_dirs() -> None:
    """建好顶层数据目录 + 数据库父目录。启动时调用 (幂等)。"""
    for sub in ("inputs", "outputs", "videos"):
        (base_dir() / sub).mkdir(parents=True, exist_ok=True)
    Path(settings.db_path).parent.mkdir(parents=True, exist_ok=True)


def input_path(device_id: str, job_id: str) -> Path:
    p = base_dir() / "inputs" / device_id
    p.mkdir(parents=True, exist_ok=True)
    return p / f"{job_id}.jpg"


def output_dir(device_id: str, job_id: str) -> Path:
    p = base_dir() / "outputs" / device_id / job_id
    p.mkdir(parents=True, exist_ok=True)
    return p


def video_path(device_id: str, job_id: str) -> Path:
    p = base_dir() / "videos" / device_id
    p.mkdir(parents=True, exist_ok=True)
    return p / f"{job_id}.mp4"


def to_url(path: Path | str) -> str:
    """把 FILE_BASE 下的文件路径转成对外可访问的 URL。"""
    rel = Path(path).resolve().relative_to(base_dir().resolve())
    return f"{settings.public_base_url.rstrip('/')}/files/{rel.as_posix()}"


def decode_image_b64(data: str) -> bytes:
    """解码 base64 图片。容忍 data:image/...;base64, 前缀。

    解码失败抛 ValueError (上层转成人话 400)。
    """
    if not data:
        raise ValueError("空图片数据")
    if data.startswith("data:"):
        # data:image/jpeg;base64,xxxx
        _, _, payload = data.partition(",")
        data = payload
    data = data.strip()
    try:
        return base64.b64decode(data, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("base64 解码失败") from exc
