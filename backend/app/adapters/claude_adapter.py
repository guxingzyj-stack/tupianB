"""Claude adapter (主用看图模型, 经 relay 调用)。

模型默认 claude-sonnet-4-6 (PRD §5.4, 已验证 7/8 通过率)。
"""

from app.adapters.base import OpenAICompatVisionAdapter
from app.config import settings


class ClaudeAdapter(OpenAICompatVisionAdapter):
    pass


def make_claude_adapter() -> ClaudeAdapter:
    return ClaudeAdapter(
        endpoint=settings.chat_completions_url,
        api_key=settings.relay_api_key,
        model=settings.relay_model,
        timeout=settings.claude_timeout,
    )
