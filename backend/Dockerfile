# 老照 后端 — Zeabur 部署用 (Linux/amd64)
FROM python:3.11-slim

# OpenCV / Pillow 运行所需的系统库
RUN apt-get update && apt-get install -y --no-install-recommends \
        libglib2.0-0 libgl1 libsm6 libxext6 libxrender1 \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 先装依赖, 利用构建缓存
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# 再拷贝代码
COPY . .

# 数据目录 (Zeabur Volume 会挂到 /app/data)
ENV DB_PATH=/app/data/app.db \
    FILE_BASE=/app/data/files

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
