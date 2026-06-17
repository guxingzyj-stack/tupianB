"""测试公共夹具。

关键: 在 import 任何 app.* 之前, 先把 DB_PATH / FILE_BASE 指到临时目录,
APP_TOKEN 置空 (默认关闭鉴权), 避免污染真实数据。
"""

import base64
import io
import os
import sys
import tempfile
from pathlib import Path

# --- 必须在导入 app 之前设置环境变量 ---
_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_DIR))

_TMP = Path(tempfile.mkdtemp(prefix="laozhao_test_"))
os.environ.setdefault("DB_PATH", str(_TMP / "app.db"))
os.environ.setdefault("FILE_BASE", str(_TMP / "files"))
os.environ.setdefault("APP_TOKEN", "")  # 默认关闭鉴权
os.environ.setdefault("PUBLIC_BASE_URL", "http://test.local")
os.environ.setdefault("RELAY_API_KEY", "test-key")
os.environ.setdefault("RELAY_BACKUP_MODEL", "")  # 不启用备用

import numpy as np  # noqa: E402
import pytest  # noqa: E402
from PIL import Image  # noqa: E402


@pytest.fixture(autouse=True, scope="session")
def _init_storage():
    from app.storage.db import init_db
    from app.storage.files import ensure_dirs

    ensure_dirs()
    init_db()
    yield


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """每个测试前清空频次计数, 避免跨测试累计触发 429。"""
    from app.middleware.rate_limit import limiter

    limiter.reset()
    yield


def make_test_image_bytes(w: int = 96, h: int = 96) -> bytes:
    """造一张有渐变和颜色的小图 (JPEG bytes)。"""
    arr = np.zeros((h, w, 3), dtype=np.uint8)
    xs = np.linspace(0, 255, w).astype(np.uint8)
    ys = np.linspace(20, 200, h).astype(np.uint8)
    arr[:, :, 0] = xs[None, :]
    arr[:, :, 1] = 110
    arr[:, :, 2] = ys[:, None]
    buf = io.BytesIO()
    Image.fromarray(arr, "RGB").save(buf, "JPEG", quality=90)
    return buf.getvalue()


def make_test_image_b64(w: int = 96, h: int = 96) -> str:
    return base64.b64encode(make_test_image_bytes(w, h)).decode("ascii")


@pytest.fixture
def test_image_b64() -> str:
    return make_test_image_b64()


@pytest.fixture
def test_image_path(tmp_path) -> Path:
    p = tmp_path / "src.jpg"
    p.write_bytes(make_test_image_bytes(128, 128))
    return p


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c
