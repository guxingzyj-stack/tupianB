# 老照 · 后端 (photo-rescue backend)

给老年人用的 AI 照片补救 App「老照」的后端服务。FastAPI + SQLite，部署在 Zeabur。

> 配套文档：`01_PRD.md` / `02_ARCHITECTURE.md` / `03_MVP_TASKS.md`

## 能力 (v0.1 后端骨架)

- `GET  /api/health` — 探活
- `POST /api/analyze` — 看图给三选项（Claude via relay）+ 即时基础修复版
- `POST /api/enhance` — 按所选方向做参数化修图
- `X-App-Token` 鉴权 + IP 频次限制中间件

## 本地运行

需要 Python 3.11+（开发机更高版本亦可）。

```powershell
# 1. 建虚拟环境
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # Windows PowerShell
# source .venv/bin/activate            # macOS / Linux

# 2. 装依赖
#   完整依赖 (含 opencv, 老照片功能用):
pip install -r requirements.txt
#   若所在 Python 版本暂无 opencv wheel, 第 1 周可只装:
#   pip install fastapi "uvicorn[standard]" pydantic pydantic-settings httpx pillow numpy python-multipart pytest pytest-asyncio

# 3. 配环境变量
copy .env.example .env                 # 然后填入 RELAY_API_KEY 等

# 4. 初始化数据库 (应用启动也会自动建表, 这步可选)
python scripts/init_db.py

# 5. 启动
uvicorn app.main:app --reload
```

打开 http://localhost:8000/docs 看接口文档；http://localhost:8000/api/health 应返回 `{"status":"ok","version":"0.1.0"}`。

## 测试

```powershell
pytest -q
```

## 端到端冒烟测试

把一张测试图放到 `test_images/cheetah.jpg`，然后：

```bash
bash scripts/smoke_test.sh           # 需要 bash + curl + jq
```

## 环境变量

见 `.env.example`。关键项：

| 变量 | 说明 |
|------|------|
| `RELAY_BASE_URL` | relay 地址，填到 `/v1` 为止 |
| `RELAY_API_KEY` | relay 密钥 |
| `RELAY_MODEL` | 看图主模型，默认 `claude-sonnet-4-6` |
| `APP_TOKEN` | App 内置 token；线上必须设置，留空=关闭鉴权 |
| `PUBLIC_BASE_URL` | 后端对外根地址，用于拼接图片 URL |
| `DB_PATH` / `FILE_BASE` | 数据库与文件存储路径 |

## 部署到 Zeabur

1. 把本仓库推到 GitHub。
2. Zeabur 新建 Project → Service，选 GitHub 仓库（根目录 = `backend/`，或把 backend 作为仓库根）。
3. 构建方式选 Dockerfile（已提供）。
4. 加一个 Volume，挂载到 `/app/data`（持久化数据库和文件）。
5. 在 Service → Variables 里配 `.env.example` 中的环境变量。
6. Region 选新加坡。
7. push 到 `main` → 自动构建部署；访问 `https://xxx.zeabur.app/api/health` 验证。

## 目录结构

```
backend/
├── app/
│   ├── main.py            # FastAPI 入口 + 中间件 + 静态文件
│   ├── config.py          # pydantic-settings 读环境变量
│   ├── api/               # 路由: health / analyze / enhance
│   ├── adapters/          # AI 调用层: claude / gpt(备)
│   ├── engine/            # 参数化修图引擎 + intent 映射
│   ├── storage/           # SQLite + 文件存取
│   ├── middleware/        # token 鉴权 + 频次限制
│   └── prompts/           # 锁定版分析 prompt
├── scripts/               # init_db.py / smoke_test.sh
├── tests/
├── requirements.txt
├── Dockerfile
└── .env.example
```
