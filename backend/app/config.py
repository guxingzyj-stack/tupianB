"""应用配置。全部来自环境变量 (或 .env 文件), 不硬编码任何 URL / Key。

用 pydantic-settings 读取。字段名小写, 环境变量名大写, 自动对应:
  RELAY_BASE_URL -> relay_base_url
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- relay (OpenAI 兼容) ---
    relay_base_url: str = "https://your-relay.example.com/v1"
    relay_api_key: str = ""
    relay_model: str = "claude-sonnet-4-6"
    relay_backup_model: str = ""  # 留空 = 不启用备用模型
    # 老照片生成式修复 (指令式图像编辑, 经 relay /images/edits)
    # doubao-seedream-4-5 实测可用~17-33s、质量好; gpt-image-2 更忠实但~65s。
    # (qwen-image-edit / gpt-image-1 / flux 当前分组 429。)
    image_edit_model: str = "doubao-seedream-4-5-251128"
    image_edit_timeout: float = 180.0
    # 图生视频 (Week 4): kling 原生代理 /kling/v1/videos/image2video,
    # model_name 用 kling 版本号 (kling-v1 实测可用, ~3-4 分钟出 5s 视频)。
    video_model: str = "kling-v1"
    video_mode: str = "std"  # std / pro
    video_duration: str = "5"  # 5 / 10 秒

    # --- 存储 ---
    db_path: str = "./data/app.db"
    file_base: str = "./data/files"

    # --- 鉴权 ---
    # 留空 = 关闭鉴权 (仅本地开发); 线上必须设置一个长随机串。
    app_token: str = ""

    # --- 对外根地址, 用于拼接返回给客户端的资源 URL ---
    public_base_url: str = "http://localhost:8000"

    # --- 调优 ---
    claude_timeout: float = 30.0
    rate_limit_per_min: int = 60
    worker_count: int = 2

    @property
    def chat_completions_url(self) -> str:
        """relay 的 chat/completions 端点。

        约定 RELAY_BASE_URL 填到 /v1; 这里补上 /chat/completions。
        若用户没填 /v1 也尽量兜住。
        """
        base = self.relay_base_url.rstrip("/")
        if not base.endswith("/v1"):
            base = base + "/v1"
        return base + "/chat/completions"

    @property
    def image_edits_url(self) -> str:
        base = self.relay_base_url.rstrip("/")
        if not base.endswith("/v1"):
            base = base + "/v1"
        return base + "/images/edits"


settings = Settings()
