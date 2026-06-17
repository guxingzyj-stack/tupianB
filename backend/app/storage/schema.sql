-- 老照 数据库 schema (SQLite)
-- 严格按 02_ARCHITECTURE.md §3.4: 只有 2 张表。
-- 建表用 IF NOT EXISTS, 应用启动时自动执行, 不做迁移工具。

-- 任务表 (异步视频生成 + 历史记录)
CREATE TABLE IF NOT EXISTS jobs (
    id            TEXT PRIMARY KEY,
    device_id     TEXT NOT NULL,       -- 设备标识 (从 App 传)
    type          TEXT NOT NULL,       -- 'analyze' / 'enhance' / 'restore' / 'video'
    status        TEXT NOT NULL,       -- 'pending' / 'running' / 'success' / 'failed'
    input_path    TEXT,
    output_path   TEXT,
    metadata_json TEXT,                -- 任意 JSON: 三选项、用户选择、模型名等
    created_at    INTEGER NOT NULL,
    updated_at    INTEGER NOT NULL,
    error_msg     TEXT
);

CREATE INDEX IF NOT EXISTS idx_jobs_device ON jobs(device_id, created_at DESC);

-- 设备配置表 (子女配置)
CREATE TABLE IF NOT EXISTS devices (
    device_id          TEXT PRIMARY KEY,
    nickname           TEXT,                  -- 老人备注 (王奶奶/李爷爷)
    daily_budget_cny   REAL    DEFAULT 10.0,
    daily_video_limit  INTEGER DEFAULT 10,
    preferred_style    TEXT,                  -- 上次用的样式
    enable_video       INTEGER DEFAULT 1,
    enable_animate_old INTEGER DEFAULT 0,     -- 老照片动起来, 默认关
    config_json        TEXT,                  -- 其他配置
    created_at         INTEGER NOT NULL
);
