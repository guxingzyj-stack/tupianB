"""AI 调用层基类。

每个 adapter 封装一个 provider, 对外暴露统一接口。
失败统一抛 AdapterFailure, 由上层 (analyze.py) 决定切备用还是退兜底。

自用版不做 ProviderRouter (架构 §3.7): 主用一家 relay, 极少切换。
"""

from __future__ import annotations

import json
import re
from typing import Protocol

import httpx


class AdapterFailure(Exception):
    """AI 调用失败 (网络错误 / HTTP 非 200 / 返回无法解析等)。"""


class BaseAdapter(Protocol):
    async def analyze(self, image_b64: str, mime: str = "image/jpeg") -> dict: ...


_FENCE_RE = re.compile(r"^```[a-zA-Z]*\s*\n?(.*?)\n?```$", re.DOTALL)


def parse_json_loose(text: str) -> dict:
    """从模型文本输出里尽量稳健地抠出 JSON 对象。

    处理: markdown ``` 代码块包裹、前后多余文字。
    失败抛 AdapterFailure。
    """
    if not text or not text.strip():
        raise AdapterFailure("模型返回为空")
    s = text.strip()

    fence = _FENCE_RE.match(s)
    if fence:
        s = fence.group(1).strip()

    start = s.find("{")
    end = s.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise AdapterFailure("模型返回里找不到 JSON 对象")

    snippet = s[start : end + 1]
    try:
        result = json.loads(snippet)
    except json.JSONDecodeError as exc:
        raise AdapterFailure(f"JSON 解析失败: {exc}") from exc
    if not isinstance(result, dict):
        raise AdapterFailure("模型返回的不是 JSON 对象")
    return result


class OpenAICompatVisionAdapter:
    """OpenAI 兼容的多模态 chat/completions adapter。

    Claude / GPT 经由 relay 都走这套接口, 只是 model 名不同。
    """

    def __init__(self, endpoint: str, api_key: str, model: str, timeout: float = 30.0):
        self.endpoint = endpoint
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def _build_payload(self, image_b64: str, mime: str) -> dict:
        # 延迟 import 避免循环依赖
        from app.prompts.analyze_prompt import SYSTEM_PROMPT, USER_PROMPT

        return {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": USER_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime};base64,{image_b64}"},
                        },
                    ],
                },
            ],
            "temperature": 0.3,
            "max_tokens": 700,
        }

    async def analyze(self, image_b64: str, mime: str = "image/jpeg") -> dict:
        payload = self._build_payload(image_b64, mime)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(self.endpoint, json=payload, headers=headers)
        except httpx.HTTPError as exc:
            raise AdapterFailure(f"relay 网络错误: {exc}") from exc

        if resp.status_code != 200:
            raise AdapterFailure(
                f"relay 返回 HTTP {resp.status_code}: {resp.text[:200]}"
            )

        try:
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise AdapterFailure(f"relay 返回结构异常: {exc}") from exc

        return parse_json_loose(content)
