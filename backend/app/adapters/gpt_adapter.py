"""GPT adapter (备用看图模型, 经 relay 调用)。

仅当 RELAY_BACKUP_MODEL 配置了 (如 gpt-4.1) 才启用。
主模型失败时由 analyze.py 决定是否尝试本备用 (PRD §5.4)。
"""

from app.adapters.base import OpenAICompatVisionAdapter
from app.config import settings


class GPTAdapter(OpenAICompatVisionAdapter):
    pass


def make_gpt_adapter() -> GPTAdapter | None:
    if not settings.relay_backup_model:
        return None
    return GPTAdapter(
        endpoint=settings.chat_completions_url,
        api_key=settings.relay_api_key,
        model=settings.relay_backup_model,
        timeout=settings.claude_timeout,
    )
