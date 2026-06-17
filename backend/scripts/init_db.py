"""初始化数据库。

用法 (在 backend/ 目录下):
    python scripts/init_db.py

会在 DB_PATH 建出库 (CREATE TABLE IF NOT EXISTS)。重复运行安全。
"""

import sys
from pathlib import Path

# 让脚本能 import app.*
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings  # noqa: E402
from app.storage.db import init_db  # noqa: E402
from app.storage.files import ensure_dirs  # noqa: E402


def main() -> None:
    ensure_dirs()
    init_db()
    print(f"[ok] 数据库已初始化: {settings.db_path}")
    print(f"[ok] 文件目录: {settings.file_base}")


if __name__ == "__main__":
    main()
